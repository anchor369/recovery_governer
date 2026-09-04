# AGENTS.md

# Repository Instructions for Coding Agents

This repository implements a payment-safe causal revenue recovery system.

Changes must preserve the separation between:

```text
Financial Truth
→ Recovery Eligibility
→ Observable Decision State
→ Counterfactual ML
→ Merchant Economics
→ Deterministic Governor
→ Audit
→ Execution
→ Outcome
```

Do not collapse these responsibilities during refactoring.

---

# 1. Primary Engineering Principle

The system optimizes:

```text
expected incremental merchant value
```

subject to:

```text
payment truth
+
deterministic policy constraints
```

It does NOT optimize raw recovery probability alone.

The machine-learning model is predictive only.

It is not the authority for:

- payment state
- eligibility
- policy
- execution
- final recovery attribution

---

# 2. Financial Truth Invariants

Financial truth always has priority over ML output.

## PAID

Any confirmed `CAPTURED` payment means:

```text
PAID
→ STOP
```

No recovery action may proceed.

Do not add model logic that can override this.

---

## UNCERTAIN

Statuses such as:

```text
CREATED
AUTHORIZED
```

represent unresolved payment state.

Required behavior:

```text
UNCERTAIN
→ WAIT_FOR_TRUTH
```

`WAIT_FOR_TRUTH` is a deterministic workflow state.

It is NOT:

- an ML treatment
- a candidate action
- a policy-learned action

Never add `WAIT_FOR_TRUTH` to the ML action space.

---

## UNPAID

Only confirmed failure can enter recovery logic.

---

# 3. Historical Truth and Temporal Safety

Historical state at decision time `T` must use only information that was actually observable before `T`.

Required conditions include:

```text
payment.created_at < T

payment_event.event_time < T

payment_event.received_at < T
```

Do not use:

- future retries
- future captures
- future failures
- events received after decision time

when reconstructing historical features.

Temporal leakage is considered a correctness defect.

---

# 4. Recovery Eligibility Invariants

Current operational policy:

```text
0 confirmed failures
→ NO_CONFIRMED_FAILURE

1 confirmed failure
→ ALLOW_NATURAL_RETRY

2+ confirmed failures
→ recovery may become eligible
```

Also:

```text
PAID
→ ORDER_ALREADY_PAID

UNCERTAIN
→ PAYMENT_STATE_UNCERTAIN

existing open case
→ RECOVERY_CASE_ALREADY_EXISTS
```

Do not weaken the production eligibility rule merely to align with synthetic training data.

The training/serving population mismatch is documented separately and must be corrected through data/model work, not by weakening safety.

---

# 5. Recovery Case Database Invariant

The database contains a partial unique index enforcing one active recovery case per order:

```text
uq_one_active_recovery_case_per_order
```

Do not remove, weaken, or bypass this constraint to make tests pass.

Tests must use unique IDs and proper cleanup instead.

---

# 6. Observable Feature Rule

Operational ML features must use only observable production-compatible information.

Do not introduce simulator-hidden variables into:

```text
backend/services/recovery_state.py
ML production features
runtime prediction
```

The simulator may contain hidden behavioral variables for generating synthetic outcomes.

Those variables must remain unavailable to the operational model.

---

# 7. Amount-Ratio Rule

Do not restore hidden simulator customer value into the production amount-ratio feature.

Current observable design:

```text
current order amount
/
median observed prior order amount
```

Fallback with no prior history:

```text
1.0
```

---

# 8. Prior Outcome Semantics

Prior orders are classified as:

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
prior_failure_count
=
prior_checkout_count - prior_success_count
```

because this incorrectly classifies unresolved history as failed.

---

# 9. Production Model

Current runtime model:

```text
models/s_learner.joblib
```

Current champion architecture:

```text
pooled S-Learner
```

Alternative implementations such as:

```text
T-Learner
IPW S-Learner
Doubly Robust Learner
```

are retained as experiments.

Do not replace the production model merely because an alternative improves one isolated metric.

Model promotion requires explicit evaluation and approval.

---

# 10. Canonical Recovery Actions

Canonical persisted/model action labels include:

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

Internally, domain objects may use:

```text
SWITCH_METHOD(target_method)
APPROVED_OFFER(discount_percent)
```

Canonical string serialization must use the shared action codec.

Do not reintroduce local copies of action-label formatting.

---

# 11. Governor Responsibility

The Governor combines:

```text
predicted recovery probability
+
merchant economics
+
deterministic policy
```

The Governor may reject an ML-favored action.

An action can be:

```text
structurally available
policy eligible
economically unattractive
```

These concepts must remain separate.

---

# 12. Incremental Utility

The core comparison is against natural recovery:

```text
Incremental Utility(action)
=
Expected Merchant Value(action)
-
Expected Merchant Value(NO_ACTION)
```

If no intervention produces positive incremental value:

```text
NO_ACTION
```

must remain available.

Do not remove `NO_ACTION` from candidate evaluation.

---

# 13. Policy Eligibility Does Not Mean Selection

In audit records:

```text
is_eligible = true
```

means the deterministic policy permits the action.

It does NOT mean:

```text
chosen
recommended
economically positive
```

Do not change this meaning.

---

# 14. Decision Audit

A recovery decision must preserve candidate-level audit information.

Persisted information includes:

```text
feature snapshot
model version
chosen action
candidate action labels
predicted probabilities
uplift
expected merchant value
incremental utility
policy eligibility
policy rejection reason
action cost
discount cost
```

Do not remove candidate-level scores for simplification.

---

# 15. Audit Atomicity

Decision header and all candidate action scores must be written atomically.

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

Never leave a partially populated decision audit.

---

# 16. Decision Is Not Execution

A chosen action is only a decision.

It does not prove the action was executed.

Current action states include:

```text
PENDING
EXECUTED
BLOCKED
NOT_REQUIRED
```

Keep decision and execution as separate concepts.

---

# 17. Pre-Execution Truth Recheck

Immediately before executing an intervention, financial truth must be checked again.

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
→ action may execute
```

This protects against customer recovery occurring between decision and execution.

Do not remove this recheck.

---

# 18. Execution Is Not Recovery

Never infer:

```text
EXECUTED
→ RECOVERED
```

A successful recovery requires payment evidence.

Current invariant:

```text
RECOVERED
requires
CAPTURED payment event
```

Before recording recovery, verify:

```text
payment belongs to recovery order
action belongs to recovery case
action has acceptable execution state
latest relevant payment event is CAPTURED
```

---

# 19. Recovery Outcome Attribution

Recovery outcomes must remain relationally linked to:

```text
recovery_case_id
action_id
payment_id
```

Do not replace payment-backed attribution with a boolean flag such as:

```text
recovered = true
```

without payment evidence.

---

# 20. Current Accounting Limitation

The current `payments` schema does not independently store all production financial fields.

Current recovery value represents recovered order value after a confirmed capture.

Do not describe it as verified:

```text
net settlement value
```

unless payment-level accounting is extended.

Future production accounting may require:

```text
charged amount
currency
processor fee
refund amount
settled amount
```

---

# 21. Payment Events

Provider/payment events should be treated as immutable financial evidence.

Future event ingestion must preserve:

```text
event persistence
+
materialized payment state update
```

as one coherent transaction.

Do not create a new API path that updates only `payments.status` while bypassing event persistence.

---

# 22. Idempotency

External payment providers may deliver the same event more than once.

Event ingestion must eventually provide an idempotent contract using the provider event identifier.

Desired semantics:

```text
first provider_event_id
→ process once

same provider_event_id again
→ safe duplicate response
→ no duplicate business effects
```

Do not implement duplicate handling by simply catching all database exceptions.

---

# 23. Concurrency

Recovery action execution must become concurrency-safe.

Do not rely only on:

```text
SELECT action
check PENDING in Python
UPDATE later
```

The database must enforce the state transition, for example through:

```sql
UPDATE ...
WHERE action_id = ...
  AND execution_status = 'PENDING'
RETURNING ...
```

or equivalent row-lock semantics.

Only one worker may successfully claim an action.

---

# 24. Workflow Failure Handling

A recovery case is currently opened before ML inference and downstream workflow steps finish.

Future hardening must ensure that exceptions cannot silently leave unusable open cases.

Use explicit and auditable handling.

Examples may include:

```text
DECISION_FAILED
retryable workflow state
controlled case closure
```

Do not silently delete failed workflow evidence.

---

# 25. API Layer Rule

Future API route handlers must remain thin.

Preferred dependency direction:

```text
API
↓
service/application layer
↓
domain / Governor
↓
data access
↓
PostgreSQL
```

Avoid implementing inside route handlers:

```text
raw SQL
feature engineering
ML treatment decoding
Governor economics
payment truth rules
```

---

# 26. Repository Refactoring Rule

Refactoring may change structure.

Refactoring must not silently change domain behavior.

Before large refactors:

1. inspect existing tests,
2. understand current invariants,
3. make the smallest coherent change,
4. add/update tests,
5. run focused tests,
6. run the complete test suite.

---

# 27. Large Modules

The following modules currently contain multiple responsibilities:

```text
backend/data_access/recovery.py
backend/services/recovery_state.py
```

They may be split later.

Do not split them and alter behavior simultaneously.

Prefer:

```text
behavior-preserving structural refactor
```

followed by separate functional changes.

---

# 28. Test Rules

Do not create permanent fixed database IDs at module import time.

Use unique IDs per test/fixture.

Do not weaken database constraints to satisfy tests.

Behavioral changes must include regression tests.

For transaction-sensitive changes, test both:

```text
success
rollback/failure
```

For concurrency-sensitive changes, test competing transitions where practical.

---

# 29. Required Verification

After Python code changes, run:

```bash
python -m compileall -q backend ml policy simulator scripts tests
```

Then run relevant focused tests.

Then run:

```bash
pytest -q
```

Do not claim tests passed unless they were actually executed successfully.

If execution is impossible due to environment/tooling problems, report that explicitly.

---

# 30. Dependency and Environment Files

Repository reproducibility files include:

```text
requirements.txt
.env.example
database/schema.sql
```

Do not put real secrets into:

```text
.env.example
README.md
tests
committed source files
```

---

# 31. Canonical Artifacts

Canonical artifacts include:

```text
models/s_learner.joblib

data/historical_recovery.csv

data/economic_benchmark_summary.csv
data/governor_evaluation.csv
data/governor_threshold_evaluation.csv
data/governor_threshold_summary.csv
```

Do not create new `_final`, `_latest`, or `_corrected_final` copies when the canonical artifact can be updated intentionally.

---

# 32. Known Training/Serving Mismatch

Current operational serving requires multiple confirmed failures.

Much of the synthetic training population was generated closer to the first-failure decision point.

This is a documented modeling limitation.

Do NOT solve it by weakening operational eligibility.

The proper future correction is:

```text
regenerate aligned training opportunities
→ retrain
→ counterfactual re-evaluation
→ economic re-evaluation
→ explicit model promotion
```

---

# 33. Comment Style

Keep comments that explain:

```text
WHY
financial/safety invariant
temporal assumption
causal assumption
non-obvious business behavior
transaction boundary
```

Remove comments that merely restate obvious Python syntax.

---

# 34. Change Scope

When assigned a specific task:

- inspect relevant code first;
- do not opportunistically redesign unrelated modules;
- preserve public/domain behavior unless requested;
- report unexpected architectural conflicts before broad changes;
- keep diffs focused.

---

# 35. Current Priority Order

Current engineering sequence:

```text
1. safe code deduplication
2. payment-system hardening
3. structural cleanup
4. full regression
5. FastAPI application boundary
6. event ingestion
7. operational APIs
8. metrics
9. dashboard
```

Do not jump to dashboard implementation while payment-event and execution hardening remain incomplete unless explicitly instructed.

---

# 36. Non-Negotiable Summary

Never regress these rules:

```text
CAPTURED means PAID.

UNCERTAIN is not FAILED.

WAIT_FOR_TRUTH is not an ML action.

First confirmed failure gets natural retry.

Production eligibility remains safety-first.

Future information cannot enter historical features.

Simulator-hidden variables cannot enter operational features.

NO_ACTION remains a valid baseline.

Governor optimizes incremental value, not raw recovery.

Policy eligibility does not mean recommendation.

Decision does not mean execution.

Execution does not mean recovery.

RECOVERED requires CAPTURED payment evidence.

Payment truth is rechecked before execution.

Audit writes remain transactional.

One active recovery case per order remains database-enforced.
```