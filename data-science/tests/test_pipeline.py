from pathlib import Path
import sys

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.feature_engineering import MODEL_FEATURES, build_feature_matrix
from src.generate_synthetic_data import SyntheticConfig, generate_tables
from src.risk_model import train_and_score


def _small_tables():
    return generate_tables(SyntheticConfig(customers=30, accounts=40, seed=7))


def test_schema_keys_and_relations_are_valid():
    customers, loans, repayments = _small_tables()
    assert customers.customer_id.is_unique
    assert loans.account_id.is_unique
    assert repayments.transaction_id.is_unique
    assert set(loans.customer_id).issubset(set(customers.customer_id))
    assert set(repayments.account_id).issubset(set(loans.account_id))


def test_generation_is_reproducible():
    first = _small_tables()
    second = _small_tables()
    for left, right in zip(first, second):
        pd.testing.assert_frame_equal(left, right)


def test_features_are_complete_and_finite():
    features = build_feature_matrix(*_small_tables())
    assert set(MODEL_FEATURES).issubset(features.columns)
    assert features[MODEL_FEATURES].notna().all().all()


def test_scoring_contract_and_range():
    result = train_and_score(build_feature_matrix(*_small_tables()), seed=7)
    required = {"risk_score_final", "risk_level", "anomaly_type", "risk_reasons", "recommended_action"}
    assert required.issubset(result.scored.columns)
    assert result.scored.risk_score_final.between(0, 100).all()
    assert set(result.scored.risk_level).issubset({"low", "medium", "high", "critical"})


def test_injected_cases_are_evaluable():
    result = train_and_score(build_feature_matrix(*_small_tables()), seed=7)
    assert result.metrics["injected_anomalies"] > 0
    assert 0 <= result.metrics["precision"] <= 1
    assert 0 <= result.metrics["recall"] <= 1
