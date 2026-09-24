"""Generate deterministic, schema-aligned synthetic fintech records."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
import random

import pandas as pd


CHANNELS = ("mpesa", "bank", "ussd")
PRODUCTS = ("personal", "business", "asset")


@dataclass(frozen=True)
class SyntheticConfig:
    customers: int = 250
    accounts: int = 400
    seed: int = 42
    as_of_date: date = date(2026, 9, 1)


def _money(value: float) -> float:
    return round(max(value, 1.0), 2)


def generate_tables(config: SyntheticConfig) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Return customers, loans, and repayments matching the IBM reference keys."""
    rng = random.Random(config.seed)

    customers: list[dict] = []
    for index in range(1, config.customers + 1):
        risk = min(99, max(1, int(rng.gauss(35, 18))))
        customers.append(
            {
                "customer_id": f"CUS{index:05d}",
                "id_number": f"SYN-{config.seed}-{index:06d}",
                "kyc_tier": "enhanced" if risk >= 60 else "basic",
                "risk_score": risk,
                "created_at": (config.as_of_date - timedelta(days=rng.randint(300, 1800))).isoformat(),
            }
        )

    loans: list[dict] = []
    repayments: list[dict] = []
    transaction_index = 1

    for index in range(1, config.accounts + 1):
        customer = rng.choice(customers)
        product = rng.choices(PRODUCTS, weights=(0.55, 0.25, 0.20), k=1)[0]
        principal = _money(rng.lognormvariate(11.0, 0.65))
        disbursement = config.as_of_date - timedelta(days=rng.randint(60, 720))
        term_days = rng.choice((180, 365, 540, 730))
        maturity = disbursement + timedelta(days=term_days)
        status = "defaulted" if rng.random() < 0.07 else ("closed" if maturity < config.as_of_date else "active")
        account_id = f"ACC{index:05d}"
        interest_rate = round(rng.uniform(0.08, 0.24), 4)
        loans.append(
            {
                "account_id": account_id,
                "customer_id": customer["customer_id"],
                "product_type": product,
                "principal_amount": principal,
                "interest_rate": interest_rate,
                "disbursement_date": disbursement.isoformat(),
                "maturity_date": maturity.isoformat(),
                "status": status,
            }
        )

        scheduled_payment = principal * (1 + interest_rate) / max(6, term_days // 30)
        payment_count = rng.randint(4, min(22, max(5, (config.as_of_date - disbursement).days // 25)))
        dominant_channel = rng.choice(CHANNELS)
        dates = sorted(disbursement + timedelta(days=rng.randint(12, max(13, (config.as_of_date - disbursement).days))) for _ in range(payment_count))

        for payment_date in dates:
            repayments.append(
                {
                    "transaction_id": f"TX{transaction_index:07d}",
                    "account_id": account_id,
                    "amount_paid": _money(rng.gauss(scheduled_payment, scheduled_payment * 0.13)),
                    "payment_date": payment_date.isoformat(),
                    "channel": dominant_channel if rng.random() < 0.92 else rng.choice(CHANNELS),
                    "injected_anomaly": "normal",
                }
            )
            transaction_index += 1

    # Inject labelled patterns solely to evaluate the otherwise unsupervised detector.
    eligible = rng.sample(range(len(repayments)), k=max(25, len(repayments) // 35))
    labels = (
        "payment_exceeds_principal",
        "rapid_successive_repayments",
        "high_risk_customer_payment",
        "early_large_settlement",
    )
    loan_lookup = {row["account_id"]: row for row in loans}
    customer_lookup = {row["customer_id"]: row for row in customers}

    for position, row_index in enumerate(eligible):
        transaction = repayments[row_index]
        loan = loan_lookup[transaction["account_id"]]
        label = labels[position % len(labels)]
        transaction["injected_anomaly"] = label
        if label == "payment_exceeds_principal":
            transaction["amount_paid"] = _money(loan["principal_amount"] * rng.uniform(1.05, 1.35))
        elif label == "rapid_successive_repayments":
            if row_index > 0 and repayments[row_index - 1]["account_id"] == transaction["account_id"]:
                transaction["payment_date"] = repayments[row_index - 1]["payment_date"]
            transaction["amount_paid"] = _money(loan["principal_amount"] * rng.uniform(0.08, 0.18))
        elif label == "high_risk_customer_payment":
            customer_lookup[loan["customer_id"]]["risk_score"] = rng.randint(82, 99)
            customer_lookup[loan["customer_id"]]["kyc_tier"] = "enhanced"
            transaction["amount_paid"] = _money(loan["principal_amount"] * rng.uniform(0.25, 0.55))
        else:
            transaction["payment_date"] = (date.fromisoformat(loan["disbursement_date"]) + timedelta(days=rng.randint(2, 20))).isoformat()
            transaction["amount_paid"] = _money(loan["principal_amount"] * rng.uniform(0.40, 0.80))

    return pd.DataFrame(customers), pd.DataFrame(loans), pd.DataFrame(repayments)


def save_tables(output_dir: Path, tables: tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    for filename, frame in zip(("customers.csv", "loan_accounts.csv", "repayment_transactions.csv"), tables):
        frame.to_csv(output_dir / filename, index=False)
