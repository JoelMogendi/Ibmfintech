#!/usr/bin/env python3
"""Run the complete Cognifi synthetic-data and risk-scoring pipeline."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import joblib

MODULE_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(MODULE_ROOT))

from src.feature_engineering import build_feature_matrix  # noqa: E402
from src.generate_synthetic_data import SyntheticConfig, generate_tables, save_tables  # noqa: E402
from src.risk_model import train_and_score  # noqa: E402


def _json_records(frame):
    selected = frame[
        [
            "transaction_id", "account_id", "customer_id", "payment_date", "amount_paid", "channel",
            "risk_score_final", "risk_level", "anomaly_type", "risk_reasons", "recommended_action",
        ]
    ].rename(columns={"risk_score_final": "risk_score"})
    selected["payment_date"] = selected["payment_date"].dt.strftime("%Y-%m-%d")
    return selected.to_dict(orient="records")


def run(customers: int, accounts: int, seed: int, output_dir: Path) -> dict:
    config = SyntheticConfig(customers=customers, accounts=accounts, seed=seed)
    tables = generate_tables(config)
    save_tables(output_dir, tables)
    feature_matrix = build_feature_matrix(*tables)
    result = train_and_score(feature_matrix, seed=seed)

    output_dir.mkdir(parents=True, exist_ok=True)
    feature_matrix.to_csv(output_dir / "feature_matrix.csv", index=False)
    result.scored.to_csv(output_dir / "scored_transactions.csv", index=False)
    (output_dir / "scored_transactions.json").write_text(json.dumps(_json_records(result.scored), indent=2), encoding="utf-8")
    (output_dir / "model_metrics.json").write_text(json.dumps(result.metrics, indent=2), encoding="utf-8")
    joblib.dump(result.model, output_dir / "repayment_anomaly_detector.joblib")
    return result.metrics


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--customers", type=int, default=250)
    parser.add_argument("--accounts", type=int, default=400)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output-dir", type=Path, default=MODULE_ROOT / "data" / "generated")
    args = parser.parse_args()
    if args.customers < 10 or args.accounts < 10:
        parser.error("customers and accounts must each be at least 10")
    metrics = run(args.customers, args.accounts, args.seed, args.output_dir)
    print(json.dumps(metrics, indent=2))
    print(f"Outputs written to {args.output_dir.resolve()}")


if __name__ == "__main__":
    main()
