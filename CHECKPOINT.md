# Engineering Checkpoint

**Project:** Payment-Safe Causal Revenue Recovery Governor  
**Checkpoint date:** 5 September 2026

---

## 1. Purpose

This file records the current engineering state of the project.

It is intended to preserve:

- validated architecture
- production-runtime choices
- benchmark results
- rejected experiments
- safety invariants
- known limitations
- unfinished hardening work
- immediate next engineering priorities

`README.md` documents the project publicly.

`CHECKPOINT.md` records internal engineering decisions.

---

# 2. Core Objective

For an eligible failed payment:

> Determine whether intervention creates positive incremental merchant value and, if so, select the safest economically justified recovery action.

The system does **not** optimize raw recovery rate alone.

Primary decision objective:

```text
maximize expected incremental merchant value
subject to payment truth and deterministic safety constraints
```

---

# 3. Frozen Architectural Boundary

The current architecture is:

```text
Financial Truth
    ↓
Recovery Eligibility
    ↓
Observable Decision State
    ↓
Counterfactual ML
    ↓
Merchant Economics
    ↓
Deterministic Recovery Governor
    ↓
Decision Audit
    ↓
Recovery Action
    ↓
Pre-Execution Truth Recheck
    ↓
Execution
    ↓
Payment Outcome
    ↓
Recovery Case Closure
```

This separation should remain intact during future refactoring.

Important principle:

```text
Prediction
≠
Policy
≠
Execution
≠
Financial Truth
```

---

# 4. Payment Truth Invariants

Payment state is authoritative over recovery logic.

## PAID

Any confirmed `CAPTURED` payment means:

```text
PAID
→ STOP
```

ML must not be invoked to override this state.

---

## UNCERTAIN

Unresolved states such as:

```text
CREATED
AUTHORIZED
```

mean:

```text
UNCERTAIN
→ WAIT_FOR_TRUTH
```

Recovery intervention is withheld.

---

## UNPAID

Recovery logic is allowed only after confirmed payment failure.

---

## Historical truth

Historical decision reconstruction must only use information known before decision time `T`.

Required conditions:

```text
payment.created_at < T

event.event_time < T

event.received_at < T
```

Future payment attempts or delayed provider events must never leak into historical model state.

---

# 5. Recovery Eligibility

Current operational policy:

```text
PAID
→ ORDER_ALREADY_PAID

UNCERTAIN
→ PAYMENT_STATE_UNCERTAIN

0 confirmed failures
→ NO_CONFIRMED_FAILURE

1 confirmed failure
→ ALLOW_NATURAL_RETRY

active case exists
→ RECOVERY_CASE_ALREADY_EXISTS

2+ confirmed failures
→ MULTIPLE_CONFIRMED_FAILURES
```

The safety policy intentionally requires multiple confirmed failures.

Do not weaken this policy merely to align with older synthetic training data.

---

# 6. Operational Action Space

Canonical action labels are:

```text
NO_ACTION
NUDGE

SWITCH_UPI
SWITCH_CREDIT_CARD
SWITCH_DEBIT_CARD
SWITCH_NETBANKING

OFFER_5
OFFER_10
```

Internal model objects may still represent:

```text
SWITCH_METHOD(target_method)

APPROVED_OFFER(discount_percent)
```

but persisted/audit labels must remain canonical.

Important reason:

```text
decision_action_scores
PRIMARY KEY (decision_id, action_type)
```

Generic labels such as `SWITCH_METHOD` would collide across target methods.

---

# 7. WAIT_FOR_TRUTH

`WAIT_FOR_TRUTH` is a deterministic workflow state.

It is **not**:

- an ML treatment
- a candidate recovery action
- a learned policy output

Do not add it to the ML action space.

---

# 8. Production ML Model

Current runtime champion:

```text
Pooled S-Learner
```

Canonical runtime artifact:

```text
models/s_learner.joblib
```

The production model estimates:

```text
P(recovery | observable state, candidate action)
```

for each candidate action.

---

# 9. Corrected Historical Dataset

Canonical dataset:

```text
data/historical_recovery.csv
```

Current corrected dataset:

```text
20,000 decision rows
45 columns
```

The corrected pipeline includes:

- temporal event filtering
- corrected prior success/failure counting
- UNCERTAIN excluded from failure count
- observable amount ratio
- per-method historical attempt/success features
- no simulator-hidden typical order value dependency

---

# 10. Current Observable Feature State

The production state includes:

## Current transaction

```text
current_method
failure_category
attempt_count
current_amount_minor
```

## Customer history

```text
customer_tenure_days

prior_checkout_count
prior_success_count
prior_failure_count
prior_success_rate

amount_ratio
```

## Historical first-method features

```text
prior_upi_count
prior_credit_card_count
prior_debit_card_count
prior_netbanking_count
```

## Per-method payment history

For each supported method:

```text
attempt_count
success_count
success_rate
```

## Runtime signals

```text
contact_consent
customer_active

available_upi
available_credit_card
available_debit_card
available_netbanking

observed_rail_health
```

---

# 11. Observable Amount Ratio

Previous implementation relied on simulator-hidden:

```text
customer.typical_order_value_minor
```

That dependency was removed.

Current implementation:

```text
amount_ratio
=
current order amount
/
median prior observed order amount
```

Fallback with no prior order history:

```text
1.0
```

Do not restore hidden simulator state into production features.

---

# 12. Prior Success / Failure Semantics

Prior orders are classified using payment truth as of decision time.

```text
PAID
→ success

UNPAID
→ failure

UNCERTAIN
→ neither success nor failure
```

Do not calculate:

```text
failure = checkouts - successes
```

because that incorrectly classifies unresolved orders as failed.

---

# 13. Payment-Method History Semantics

Method-history attempt counts use factual payment attempts known before decision time.

For a method:

```text
attempt_count
=
all known payment attempts using the method

resolved_count
=
CAPTURED + FAILED

success_count
=
CAPTURED

success_rate
=
success_count / resolved_count
```

If no resolved attempts exist:

```text
success_rate = 0.0
```

---

# 14. ML Feature Experiments

Several additional representations were evaluated.

## Raw method-history features

Twelve per-method historical features were added directly to the S-Learner.

Result:

```text
Probability MAE      approximately unchanged
Uplift MAE           worse
Uplift correlation   improved
Best-action accuracy worse
Policy recovery      very small improvement
```

Decision:

```text
NOT PROMOTED
```

Reason:

The representation did not improve counterfactual decision quality consistently.

---

## Candidate-relative method history

Features:

```text
target_method_attempt_count
target_method_success_count
target_method_success_rate
```

Result compared with corrected baseline:

```text
Probability MAE      ~same
Uplift MAE           slightly better
Uplift correlation   better
Best-action accuracy same
Policy recovery      slightly worse
Oracle regret        worse
```

Decision:

```text
NOT PROMOTED
```

---

# 15. Production Model Decision

Keep the corrected baseline pooled S-Learner as runtime champion.

Keep the following models as experiments/evaluation implementations:

```text
T-Learner
IPW S-Learner
Doubly Robust Learner
```

Do not automatically promote a model because one individual metric improves.

Production promotion requires improvement across policy-relevant counterfactual metrics.

---

# 16. Corrected S-Learner Counterfactual Benchmark

Corrected baseline evaluation:

```text
Probability MAE       0.0831

Uplift MAE            0.0336

Uplift correlation    0.2893

Best-action accuracy  50%

Policy recovery       66.84%

NO_ACTION recovery    62.21%

Oracle recovery       68.89%

Oracle regret         2.05 percentage points
```

These supersede the older checkpoint values.

Do not reuse the previous pre-pipeline-fix benchmark.

---

# 17. Economic Benchmark

Current corrected benchmark:

| Policy | Recovery Rate | Intervention Rate | Unnecessary Intervention | Incremental Value / Failure |
|---|---:|---:|---:|---:|
| NO_ACTION | 61.19% | 0.0% | 0.0% | ₹0.00 |
| BLANKET_NUDGE | 63.89% | 37.6% | 19.15% | ₹18.00 |
| RULE_BASED | 63.13% | 27.2% | 25.00% | ₹13.16 |
| S_LEARNER_RECOVERY_MAX | 65.18% | 83.2% | 43.27% | ₹13.17 |
| ECONOMIC_GOVERNOR | 65.09% | 67.6% | 26.63% | ₹25.30 |
| ECONOMIC_ORACLE | 67.18% | 67.2% | 0.0% | ₹38.33 |

Primary comparison:

```text
Recovery-max

Recovery            65.18%
Intervention        83.2%
Unnecessary         43.27%
Incremental value   ₹13.17/failure
```

versus:

```text
Economic Governor

Recovery            65.09%
Intervention        67.6%
Unnecessary         26.63%
Incremental value   ₹25.30/failure
```

The Governor sacrifices approximately:

```text
0.09 percentage points
```

of recovery while substantially improving merchant economics.

---

# 18. Merchant Utility Thresholds

Current threshold evaluation:

## T0 — Value Max

```text
Recovery             65.09%
Intervention         67.6%
Unnecessary          26.63%
Incremental value    ₹25.30/failure
```

## T5 — Balanced

```text
Recovery             64.33%
Intervention         43.6%
Unnecessary          18.35%
Incremental value    ₹22.38/failure
```

## T10 — Conservative

```text
Recovery             63.18%
Intervention         26.0%
Unnecessary          18.46%
Incremental value    ₹17.73/failure
```

Current product mapping:

```text
Value Max      → ₹0 threshold
Balanced       → ₹5 threshold
Conservative   → ₹10 threshold
```

---

# 19. Governor Rules

The deterministic Governor currently enforces:

```text
NO_ACTION always structurally permitted

maximum payment attempts

NUDGE requires:
    contact consent
    customer not actively retrying

SWITCH_METHOD requires:
    target method exists
    target != current method
    target rail available

APPROVED_OFFER requires:
    positive discount
    discount <= merchant offer cap
```

After policy eligibility, the Governor selects the highest positive incremental merchant utility.

If no intervention has positive utility:

```text
NO_ACTION
```

wins.

---

# 20. Policy Eligibility vs Economic Selection

These concepts must remain separate.

Example:

```text
OFFER_5

policy eligible = true

incremental utility = -₹60.98
```

Meaning:

```text
The action is allowed,
but should not be chosen.
```

Do not reinterpret `is_eligible` in `decision_action_scores` as "recommended".

---

# 21. Decision Audit

Current audit chain:

```text
recovery_case
    ↓
recovery_decision
    ↓
decision_action_scores
```

Every decision stores:

```text
model version
prediction time
chosen action
feature snapshot
explanation
```

Candidate scores store:

```text
canonical action label
policy eligibility
ineligibility reason
predicted recovery probability
uplift
expected merchant value
incremental utility
action cost
expected discount cost
```

---

# 22. Audit Transaction Guarantee

Decision header and candidate scores are persisted atomically.

Required behavior:

```text
all writes succeed
→ COMMIT
```

or:

```text
any write fails
→ ROLLBACK
```

A decision must never remain with only a subset of its candidate scores.

---

# 23. Recovery Action Lifecycle

Current execution states:

```text
PENDING
EXECUTED
BLOCKED
NOT_REQUIRED
```

Canonical action labels are stored in `recovery_actions.action_type`.

Example:

```text
SWITCH_UPI
```

not:

```text
SWITCH_METHOD
```

---

# 24. Pre-Execution Payment Safety

Immediately before executing an intervention:

```text
evaluate payment truth again
```

Required behavior:

```text
PAID
→ BLOCKED
→ ORDER_ALREADY_PAID_BEFORE_EXECUTION
```

```text
UNCERTAIN
→ BLOCKED
→ PAYMENT_STATE_UNCERTAIN_BEFORE_EXECUTION
```

```text
UNPAID
→ EXECUTED
```

This protects against payment completion occurring between decision time and action execution.

---

# 25. Recovery Outcome Invariant

Execution does not imply recovery.

Required relationship:

```text
EXECUTED
≠
RECOVERED
```

A `RECOVERED` outcome requires a confirmed:

```text
CAPTURED
```

payment event.

Before attributing recovery:

```text
payment must belong to recovery order

action must belong to recovery case

action must have reached executable state

latest payment event must be CAPTURED
```

---

# 26. Recovery Outcome Transaction

Successful recovery performs:

```text
insert recovery_outcome
+
close recovery_case
```

inside one transaction.

Required case state:

```text
status = CLOSED

closure_reason = RECOVERED
```

---

# 27. Verified Full Operational Lifecycle

The complete runtime lifecycle has been exercised successfully:

```text
FAILED payment
    ↓
FAILED payment
    ↓
UNPAID
    ↓
MULTIPLE_CONFIRMED_FAILURES
    ↓
Recovery Case OPEN
    ↓
Real S-Learner
    ↓
Economic Governor
    ↓
Decision Audit
    ↓
Recovery Action PENDING
    ↓
Pre-Execution Truth Check
    ↓
EXECUTED
    ↓
New CAPTURED Payment
    ↓
Financial Truth = PAID
    ↓
Recovery Outcome RECOVERED
    ↓
Recovery Case CLOSED
```

A SQL join successfully traced:

```text
Order
→ Recovery Case
→ Recovery Decision
→ Recovery Action
→ Recovery Outcome
→ Captured Payment
→ CAPTURED Payment Event
```

---

# 28. PostgreSQL Schema

The database schema is now versioned in:

```text
database/schema.sql
```

Core tables:

```text
customers
orders
payments
payment_events
recovery_cases
recovery_decisions
decision_action_scores
recovery_actions
recovery_outcomes
```

Important invariant:

```text
uq_one_active_recovery_case_per_order
```

must remain intact.

Do not weaken database uniqueness to accommodate tests.

---

# 29. Test Design Rule

Tests must not create fixed permanent IDs at module import time.

Previous pattern:

```text
create customer C101 during collection
```

caused repeated-run collisions.

Correct pattern:

```text
generate unique IDs per test
execute DB mutations inside test/fixture
clean up where appropriate
```

The old C101 collection problem has been fixed.

---

# 30. Repository Reproducibility

Current environment:

```text
Python       3.14.7
PostgreSQL   18.x
```

Pinned dependencies are stored in:

```text
requirements.txt
```

Database configuration example:

```text
.env.example
```

Database schema:

```text
database/schema.sql
```

---

# 31. Canonical Data and Model Artifacts

Keep:

```text
data/historical_recovery.csv

data/economic_benchmark_summary.csv
data/governor_evaluation.csv
data/governor_threshold_evaluation.csv
data/governor_threshold_summary.csv

models/s_learner.joblib
```

The duplicate `_corrected_final.csv` benchmark copies were removed.

Experimental local model binaries should not replace:

```text
models/s_learner.joblib
```

unless a new model is explicitly promoted.

---

# 32. Known Modeling Limitation

## Training / serving eligibility mismatch

Operational serving requires:

```text
2+ confirmed failures
```

while a significant part of the synthetic training population was generated around the initial failed attempt.

Current decision:

```text
KEEP production safety gate.
```

Do not weaken eligibility.

Longer-term fix:

```text
regenerate synthetic decision opportunities
at the exact production eligibility point
```

---

# 33. Payment Amount Limitation

Current `payments` schema does not independently store payment-level captured amount.

Therefore:

```text
recovered_amount_minor
```

currently represents recovered order value after a confirmed capture.

A production schema should eventually contain explicit payment-level:

```text
amount
currency
charged amount
settled amount
refunded amount
processing fee
```

---

# 34. Failure Reason Replay Limitation

`failure_reason` currently lives on the materialized `payments` row.

Payment events do not independently timestamp the failure reason.

Therefore historical payment status can be reconstructed from events, but failure-reason mutation history cannot be reconstructed perfectly.

---

# 35. Runtime Signal Limitation

The following are currently provided as runtime inputs:

```text
payment-method availability
observed rail health
customer activity
```

Future integration should source these from real infrastructure/services.

Do not replace unknown runtime data with simulator-hidden variables.

---

# 36. Backend Hardening Still Required

Before exposing a real event-ingestion API, complete the following.

## 36.1 Payment event idempotency

Current provider-event ingestion must safely handle duplicate webhook delivery.

Desired behavior:

```text
provider_event_id arrives once
→ process

same provider_event_id arrives again
→ idempotent no-op / existing result
```

Do not allow duplicate delivery to trigger duplicate business processing.

---

## 36.2 Materialized payment state synchronization

Target architecture:

```text
immutable payment event
    ↓
update materialized payment state
    ↓
financial truth evaluation
```

The live event ingestion path should ensure `payments.status` and event history cannot silently diverge.

---

## 36.3 Atomic action-state transition

Execution transition should eventually use:

```sql
UPDATE recovery_actions
SET execution_status = ...
WHERE action_id = ...
  AND execution_status = 'PENDING'
```

rather than relying only on a prior Python-side state check.

This prevents multiple workers from executing the same action concurrently.

---

## 36.4 Decision failure handling

Current workflow opens a recovery case before the model/Governor pipeline completes.

If inference fails after case creation, an open case may remain without a valid decision.

Add an auditable failure state or controlled case closure such as:

```text
DECISION_FAILED
```

before treating the orchestration layer as complete.

---

# 37. Cleanup Still Planned

The architecture should remain unchanged while performing the following refactors.

## Shared action codec

Canonical action-label logic currently appears in multiple locations.

Create one shared implementation for:

```text
RecoveryAction → canonical action label

canonical treatment/action label → model action features
```

This reduces train/serve inconsistencies.

---

## Shared treatment decoding

Treatment decoding logic is duplicated across causal models.

Extract common treatment parsing where practical.

---

## Evaluation utilities

Several evaluation scripts duplicate:

```text
counterfactual rollout logic
action enumeration
metric computation
policy evaluation
```

Extract common utilities and keep CLI scripts thin.

---

## Large data-access modules

`backend/data_access/recovery.py` currently contains multiple responsibilities:

```text
recovery cases
decisions
action scores
actions
outcomes
```

Eventually split into focused modules after behavior is protected by tests.

---

## Recovery-state module

`backend/services/recovery_state.py` is large because it contains:

```text
customer/order history
payment-method history
current payment state
final state assembly
```

It can be split later, but only after current behavior is frozen with tests.

---

## Comment cleanup

Comment rule:

```text
Explain WHY,
safety invariants,
modeling assumptions,
or non-obvious business behavior.
```

Avoid comments that only restate the next line of Python.

---

# 38. Immediate Next Engineering Phase

The next major layer is an event-driven API and operational observability surface.

Target direction:

```text
Payment Event Ingestion
        ↓
Financial Truth
        ↓
Recovery Workflow
        ↓
Candidate Scores
        ↓
Governor Decision
        ↓
Action State
        ↓
Payment Outcome
        ↓
Case Timeline / Metrics
```

Expected API capabilities:

```text
ingest payment events

create / inspect recovery scenarios

retrieve financial truth

retrieve recovery eligibility

retrieve recovery case state

retrieve candidate action scores

retrieve Governor reasoning

retrieve action execution status

retrieve recovery outcome

retrieve case timeline

retrieve portfolio metrics
```

API work must build on the existing service layer rather than moving business logic into route handlers.

---

# 39. Engineering Rule for Next Phase

Keep route/controller code thin.

Desired structure:

```text
API
 ↓
Application / Service Layer
 ↓
Domain / Governor
 ↓
Data Access
 ↓
PostgreSQL
```

Avoid:

```text
API route
→ direct SQL
→ ML calls
→ policy rules
```

inside one endpoint.

---

# 40. Current Stability Rule

The following components are considered behaviorally frozen unless a test exposes a defect:

```text
payment truth semantics

natural retry policy

operational eligibility

temporal filtering

observable amount ratio

S-Learner champion selection

economic utility calculation

Governor guardrails

audit transaction

pre-execution truth veto

payment-linked recovery outcome

case closure semantics
```

Refactors may change structure.

They should not silently change these behaviors.

---

# 41. Current Project State

Completed:

```text
Synthetic data generation
Temporal-safe feature construction
Corrected S-Learner
Counterfactual evaluation
Alternative causal-model experiments
Economic benchmark
Merchant utility thresholds
PostgreSQL operational schema
Financial truth service
Recovery eligibility
Operational state builder
Candidate generation
Governor integration
Decision audit
Transactional score persistence
Recovery actions
Execution-time truth recheck
Payment-linked recovery outcomes
Recovery case closure
End-to-end operational smoke path
Repository schema export
Pinned dependencies
Repeatable database tests
README documentation
```

In progress / next:

```text
Code deduplication
Backend hardening
Event ingestion
API/control plane
Operational timeline
Portfolio metrics
Dashboard
```

---

# 42. Do Not Regress

Do not:

```text
make WAIT_FOR_TRUTH an ML action

count UNCERTAIN history as failure

use future payment events in features

reintroduce hidden simulator features

weaken DB uniqueness for tests

optimize only recovery probability

assume EXECUTED means RECOVERED

record recovery without CAPTURED payment evidence

persist generic SWITCH_METHOD labels in candidate-score tables

tune simulator behavior only to make the Governor look better
```

---

# 43. Current Product Thesis

The central technical thesis remains:

> The best revenue-recovery policy is not necessarily the action with the highest recovery probability. It is the safe action with the highest positive incremental merchant value relative to natural recovery.