# Cognifi Fintech Risk Intelligence — Member 1

This module is the data-science contribution to the Cognifi fintech security and compliance portal. It turns the IBM fintech reference schemas into synthetic, privacy-safe data, engineers repayment-risk features, trains an anomaly detector, and exports explainable scores for the Next.js API and dashboard.

## Why this exists

Financial institutions need to identify abnormal loan repayments early without exposing real customer data during a demonstration. This pipeline creates a reproducible dataset aligned to:

- `customers`
- `loan_accounts`
- `repayment_transactions`

The pipeline then produces risk intelligence suitable for compliance analysts, credit-risk teams, and operational dashboards.

## Data flow

1. Generate deterministic synthetic customers, loans, and repayments.
2. Inject a small set of known anomaly patterns for evaluation.
3. Join the schema-aligned tables and calculate behavioral features.
4. Train an Isolation Forest without using the injected labels.
5. Combine model evidence with transparent business rules.
6. Export dashboard-ready JSON, model metrics, and a CSV audit trail.

## Risk patterns demonstrated

- `payment_exceeds_principal` — one payment is implausibly large relative to the loan.
- `rapid_successive_repayments` — multiple repayments occur within seven days.
- `high_risk_customer_payment` — a high-risk customer makes an unusually large repayment.
- `channel_switch` — the channel changes unexpectedly for an account.
- `early_large_settlement` — a large fraction of principal is repaid unusually early.

## Run locally

From the repository root:

```bash
python -m venv .venv
source .venv/bin/activate             # Windows: .venv\Scripts\activate
pip install -r data-science/requirements.txt
python data-science/run_pipeline.py
pytest data-science/tests -q
```

Useful options:

```bash
python data-science/run_pipeline.py --customers 300 --accounts 500 --seed 42
python data-science/run_pipeline.py --output-dir /tmp/cognifi-risk
```

## Outputs

Generated files are written to `data-science/data/generated/` and are intentionally ignored by Git because they can be recreated. A small committed example is available in `demo/scored_transactions.sample.json`.

| Output | Consumer |
| --- | --- |
| `customers.csv` | watsonx.data customer table |
| `loan_accounts.csv` | watsonx.data loan table |
| `repayment_transactions.csv` | watsonx.data transaction table |
| `feature_matrix.csv` | analysis and audit |
| `scored_transactions.csv` | analysts and validation |
| `scored_transactions.json` | Member 2 API / Member 3 dashboard |
| `model_metrics.json` | evaluation and presentation |

## Dashboard contract

Every scored transaction contains:

```json
{
  "transaction_id": "TX0000001",
  "account_id": "ACC00001",
  "customer_id": "CUS00001",
  "payment_date": "2026-05-12",
  "amount_paid": 450000.0,
  "channel": "mpesa",
  "risk_score": 91.3,
  "risk_level": "critical",
  "anomaly_type": "early_large_settlement",
  "risk_reasons": ["Large early repayment: 45.0% of principal"],
  "recommended_action": "hold_and_investigate"
}
```

The formal contract is `schemas/risk-score.schema.json`.

## watsonx.data integration

For the TechZone demonstration, upload the three generated CSV tables to IBM Cloud Object Storage and expose them through watsonx.data. The table names and join keys deliberately match the supplied SQL schemas. The local pipeline remains a reproducible fallback when TechZone credentials are unavailable; it never claims that a local run contacted IBM services.

Suggested demo query:

```sql
SELECT risk_level, anomaly_type, COUNT(*) AS alerts,
       ROUND(AVG(risk_score), 2) AS average_risk
FROM scored_transactions
WHERE risk_level IN ('high', 'critical')
GROUP BY risk_level, anomaly_type
ORDER BY average_risk DESC;
```

## Responsible use

- All records are synthetic; do not upload real customer data to TechZone.
- Scores are decision support, not automatic proof of fraud.
- High-risk decisions require human review.
- Explanations are exported with every alert to support auditability.

## Ownership

This directory is the Member 1 data-science workspace. It does not modify the Member 2 backend or Member 3 dashboard workspaces.
