# Razorpay Buildathon Checkpoint

Date: 4 September 2026

## Project

Payment-Safe Causal Revenue Recovery Governor

Core decision:

For a failed payment, determine whether intervention is worthwhile,
and if yes, which safe action produces the highest incremental
merchant value.

## Current Architecture

Financial Truth
→ Recovery Eligibility
→ ML / Causal Intelligence
→ Economics
→ Deterministic Governor
→ Execution
→ Outcome / Audit

## Current Actions

- NO_ACTION
- NUDGE
- SWITCH_METHOD
- APPROVED_OFFER
- WAIT_FOR_TRUTH is a deterministic safety/workflow state

## Current Main ML Model

Pooled S-Learner

Current champion benchmark:

- Probability MAE: 0.0826
- Uplift MAE: 0.0310
- Uplift correlation: 0.4607
- Best-action accuracy: 43.00%
- Policy recovery: 66.20%
- NO_ACTION recovery: 61.36%
- Oracle recovery: 68.01%
- Regret vs Oracle: 1.81 pp

## Causal Experiments

### IPW S-Learner

- Probability MAE: 0.0830
- Uplift MAE: 0.0320
- Uplift correlation: 0.4881
- Policy recovery: 66.20%
- Regret: 1.81 pp

Result:
Improved uplift correlation but not policy value.

### Doubly Robust Learner

- Probability MAE: 0.0833
- Uplift MAE: 0.0336
- Uplift correlation: 0.3419
- Best-action accuracy: 41.50%
- Policy recovery: 66.25%
- Regret: 1.76 pp

Result:
Tiny policy improvement but worse uplift estimation.
Not enough evidence to replace S-Learner.

## Current Decision

Keep Pooled S-Learner as the production champion.

Keep:
- T-Learner
- IPW S-Learner
- Doubly Robust learner

as experimental/evaluation models.

## DR Pipeline Built

20,000 historical decision rows
→ 3-fold customer-grouped cross-fitting
→ DR pseudo-outcomes
→ eligibility filtering
→ 111,467 valid second-stage rows
→ HistGradientBoostingRegressor
→ models/dr_learner.joblib

## Governor Result

Economic Governor currently improves merchant value compared with
simply maximizing recovery probability.

T0 Governor:

- Recovery: 66.48%
- Intervention rate: 75.6%
- Unnecessary interventions: 29.10%
- Incremental merchant value: ₹28.76 per failed payment
- Approximately ₹28,758 incremental value per 1,000 failures

Recovery-max S policy:

- Recovery: 66.57%
- Incremental merchant value: ₹25.88 per failed payment

## Important Known Issue

An older database test creates customer C101 during test collection,
causing a unique-constraint violation on repeated runs.

Do not weaken the database uniqueness constraint.
The test should later be converted to proper fixtures / temporary IDs.

## Next ML Direction

Investigate genuinely new observable customer payment-method history:

- prior UPI success count/rate
- prior credit-card success count/rate
- prior debit-card success count/rate
- prior netbanking success count/rate

Do not blindly add them.
First inspect the simulator/state-builder implementation and determine
how production-realistic values should be calculated.

## Important Project Rule

Do not tune the synthetic simulator merely so that the Governor wins.

The Oracle remains simulator-only and is an upper bound.