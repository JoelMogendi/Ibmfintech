# Repayment Anomaly Detector — Model Card

## Intended use

Prioritize synthetic loan-repayment transactions for human review in the Cognifi fintech demonstration. It supports internal risk and compliance analytics; it must not make autonomous lending, customer-blocking, or fraud determinations.

## Method

- Robust scaling reduces sensitivity to extreme monetary values.
- Isolation Forest learns unusual multivariate behavior without anomaly labels.
- Transparent controls capture domain-specific patterns that a general anomaly model can miss.
- The final score is the stronger of the model evidence and control evidence.

## Features

Payment-to-principal ratio, prior customer risk, loan age, time to maturity, recent repayment frequency and value, days since the previous repayment, payment-channel change, weekend indicator, and within-account amount deviation.

## Evaluation

The generator injects known test scenarios after creating normal repayment histories. These labels are used only for evaluation. Run `python data-science/run_pipeline.py` to reproduce the current metrics using seed 42. The investigation threshold is 85; high-risk scores below it remain available for monitoring.

## Limitations

- Synthetic behavior is simpler than production financial activity.
- A suspicious pattern is not proof of fraud.
- The model has not been validated for adverse-impact or production drift.
- Prior customer-risk scores may contain historical bias and require governance.
- Production deployment requires access controls, encryption, monitoring, model approval, and periodic recalibration.

## Human oversight

Every alert includes reasons and a recommended action. A qualified analyst must review the source transaction, customer context, and applicable policy before taking action.
