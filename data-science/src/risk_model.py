"""Train an unsupervised detector and produce explainable risk decisions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.metrics import accuracy_score, confusion_matrix, f1_score, precision_score, recall_score, roc_auc_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import RobustScaler

from .feature_engineering import MODEL_FEATURES


@dataclass
class ModelResult:
    model: Pipeline
    scored: pd.DataFrame
    metrics: dict[str, Any]


def _rule_evidence(row: pd.Series) -> tuple[float, str, list[str]]:
    evidence: list[tuple[float, str, str]] = []
    ratio = float(row["amount_to_principal_ratio"])
    if ratio > 1:
        evidence.append((100, "payment_exceeds_principal", f"Payment is {ratio:.1%} of original principal"))
    if row["days_since_previous_payment"] <= 1 and ratio >= 0.08:
        evidence.append((84, "rapid_successive_repayments", "A material repayment followed another within 24 hours"))
    elif row["repayment_count_7d"] >= 4:
        evidence.append((82, "rapid_successive_repayments", f"{int(row['repayment_count_7d'])} repayments recorded within seven days"))
    if row["customer_risk_normalized"] >= 0.8 and ratio >= 0.20:
        evidence.append((78, "high_risk_customer_payment", "Large repayment by a customer with an elevated prior risk score"))
    if row["days_since_disbursement"] <= 30 and ratio >= 0.35:
        evidence.append((88, "early_large_settlement", f"Large early repayment: {ratio:.1%} of principal"))
    if row["channel_switch"] and abs(row["account_amount_zscore"]) >= 2.5:
        evidence.append((68, "channel_switch", "Payment channel changed during an unusual-value transaction"))
    if not evidence:
        return 0.0, "none", ["No material rule-based risk indicator"]
    evidence.sort(reverse=True)
    return evidence[0][0], evidence[0][1], [item[2] for item in evidence[:3]]


def _risk_level(score: float) -> str:
    if score >= 88:
        return "critical"
    if score >= 75:
        return "high"
    if score >= 45:
        return "medium"
    return "low"


def _action(level: str) -> str:
    return {
        "critical": "hold_and_investigate",
        "high": "enhanced_due_diligence",
        "medium": "monitor_and_verify",
        "low": "allow",
    }[level]


def train_and_score(features: pd.DataFrame, seed: int = 42) -> ModelResult:
    """Fit Isolation Forest, blend its score with controls, and evaluate injected cases."""
    model = Pipeline(
        [
            ("scale", RobustScaler()),
            ("detector", IsolationForest(n_estimators=250, contamination=0.035, random_state=seed, n_jobs=-1)),
        ]
    )
    matrix = features[MODEL_FEATURES].astype(float)
    model.fit(matrix)
    raw_anomaly = -model.decision_function(matrix)
    low, high = np.quantile(raw_anomaly, [0.02, 0.98])
    model_score = np.clip((raw_anomaly - low) / max(high - low, 1e-9) * 100, 0, 100)

    scored = features.copy()
    rule_results = scored.apply(_rule_evidence, axis=1)
    scored["rule_score"] = [result[0] for result in rule_results]
    scored["anomaly_type"] = [result[1] for result in rule_results]
    scored["risk_reasons"] = [result[2] for result in rule_results]
    scored["model_anomaly_score"] = np.round(model_score, 2)
    scored["risk_score_final"] = np.round(np.maximum(scored["rule_score"], model_score * 0.85), 2)
    scored["risk_level"] = scored["risk_score_final"].map(_risk_level)
    scored["recommended_action"] = scored["risk_level"].map(_action)

    truth = scored["injected_anomaly"].ne("normal").astype(int)
    # Scores at or above 85 enter the investigation queue; lower high-risk
    # scores remain visible for monitoring without being treated as positives.
    predicted = scored["risk_score_final"].ge(85).astype(int)
    metrics = {
        "records_scored": int(len(scored)),
        "injected_anomalies": int(truth.sum()),
        "investigation_threshold": 85,
        "precision": round(float(precision_score(truth, predicted, zero_division=0)), 4),
        "recall": round(float(recall_score(truth, predicted, zero_division=0)), 4),
        "f1_score": round(float(f1_score(truth, predicted, zero_division=0)), 4),
        "accuracy": round(float(accuracy_score(truth, predicted)), 4),
        "roc_auc": round(float(roc_auc_score(truth, scored["risk_score_final"])), 4),
        "confusion_matrix": confusion_matrix(truth, predicted).tolist(),
        "methodology": "Isolation Forest score blended with transparent fintech control rules",
        "evaluation_note": "Injected synthetic labels are used only for evaluation, not model fitting.",
    }
    return ModelResult(model=model, scored=scored, metrics=metrics)
