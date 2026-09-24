"""Create auditable features from schema-aligned fintech tables."""

from __future__ import annotations

import numpy as np
import pandas as pd


MODEL_FEATURES = [
    "amount_to_principal_ratio",
    "customer_risk_normalized",
    "days_since_disbursement",
    "days_to_maturity",
    "repayment_count_7d",
    "days_since_previous_payment",
    "repayment_sum_ratio_30d",
    "channel_switch",
    "weekend_payment",
    "account_amount_zscore",
]


def build_feature_matrix(customers: pd.DataFrame, loans: pd.DataFrame, repayments: pd.DataFrame) -> pd.DataFrame:
    """Join source tables and calculate point-in-time repayment features."""
    frame = repayments.merge(loans, on="account_id", validate="many_to_one")
    frame = frame.merge(customers[["customer_id", "kyc_tier", "risk_score"]], on="customer_id", validate="many_to_one")
    for column in ("payment_date", "disbursement_date", "maturity_date"):
        frame[column] = pd.to_datetime(frame[column], errors="raise")
    frame = frame.sort_values(["account_id", "payment_date", "transaction_id"]).reset_index(drop=True)

    frame["amount_to_principal_ratio"] = frame["amount_paid"] / frame["principal_amount"].clip(lower=1)
    frame["customer_risk_normalized"] = frame["risk_score"].clip(0, 100) / 100
    frame["days_since_disbursement"] = (frame["payment_date"] - frame["disbursement_date"]).dt.days.clip(lower=0)
    frame["days_to_maturity"] = (frame["maturity_date"] - frame["payment_date"]).dt.days
    frame["weekend_payment"] = frame["payment_date"].dt.dayofweek.ge(5).astype(int)
    frame["days_since_previous_payment"] = (
        frame.groupby("account_id")["payment_date"].diff().dt.days.fillna(999).clip(lower=0)
    )
    frame["channel_switch"] = (
        frame.groupby("account_id")["channel"].transform(lambda values: values.ne(values.shift()).astype(int)).where(frame.groupby("account_id").cumcount().gt(0), 0)
    )

    def rolling_features(group: pd.DataFrame) -> pd.DataFrame:
        dated = group.set_index("payment_date")
        group["repayment_count_7d"] = dated["amount_paid"].rolling("7D", closed="both").count().to_numpy()
        rolling_sum = dated["amount_paid"].rolling("30D", closed="both").sum().to_numpy()
        group["repayment_sum_ratio_30d"] = rolling_sum / group["principal_amount"].clip(lower=1).to_numpy()
        return group

    account_groups = [rolling_features(group.copy()) for _, group in frame.groupby("account_id", sort=False)]
    frame = pd.concat(account_groups, ignore_index=True)
    group_mean = frame.groupby("account_id")["amount_paid"].transform("mean")
    group_std = frame.groupby("account_id")["amount_paid"].transform("std").replace(0, np.nan)
    frame["account_amount_zscore"] = ((frame["amount_paid"] - group_mean) / group_std).fillna(0).clip(-10, 10)
    return frame.reset_index(drop=True)
