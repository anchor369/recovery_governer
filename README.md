# Recovery Governor

<p align="center">
  <strong>Payment-safe counterfactual intelligence for failed-revenue recovery.</strong><br>
  Choose the safe intervention with the highest positive incremental merchant value relative to natural recovery.
</p>

<p align="center">
  <a href="#why-recovery-governor">Why it exists</a> ·
  <a href="#architecture">Architecture</a> ·
  <a href="#canonical-controlled-benchmark">Evidence</a> ·
  <a href="#product-experience">Product tour</a> ·
  <a href="#quickstart">Quickstart</a> ·
  <a href="#testing">Testing</a>
</p>

> **Recovery Max ≠ Merchant Value Max.** A higher recovery probability is useful only when payment truth permits intervention and the expected incremental value remains positive after costs.

Recovery Governor is a reference implementation of an end-to-end recovery decision system. It combines immutable payment evidence, conservative eligibility, treatment-aware ML, merchant economics, deterministic policy, transactional audit, concurrency-safe execution, and payment-backed outcome attribution.

## Contents

- [Why Recovery Governor](#why-recovery-governor)
- [What the system does](#what-the-system-does)
- [Architecture and decision authority](#architecture)
- [AI model](#ai-model)
- [Economic Governor and benchmark evidence](#economic-governor)
- [Payment-safety invariants](#payment-safety-invariants)
- [Data model and audit traceability](#data-model-and-audit-traceability)
- [Product experience](#product-experience)
- [API](#api)
- [Quickstart](#quickstart)
- [Project structure](#project-structure)
- [Testing](#testing)
- [Provider boundary and limitations](#provider-boundary)
- [Repository artifacts](#repository-artifacts)

## At a glance

| Question | Implemented answer |
|---|---|
| What is optimized? | Expected incremental merchant value versus `NO_ACTION` |
| What has final authority? | Payment truth and deterministic policy—not the model |
| What does ML estimate? | Recovery probability under each candidate action |
| What is the production model? | Pooled S-Learner in [`models/s_learner.joblib`](models/s_learner.joblib) |
| What makes recovery verified? | A linked `CAPTURED` payment event |
| Where is the decision explained? | Candidate-level audit plus the Recovery Lab |
| What is persisted? | Orders, payments, events, cases, decisions, action scores, actions, and outcomes |
| What data supports the demo and evaluation? | Persisted synthetic journeys and canonical controlled benchmark artifacts |
| How is it validated? | Controlled policy comparisons and 231 automated tests |
| What is the integration boundary? | Provider-agnostic event contract; provider-specific adapters are outside the current implementation |

### Choose a reading path

| Reader | Start here |
|---|---|
| Product or business reviewer | [Problem](#why-recovery-governor) → [benchmark](#canonical-controlled-benchmark) → [product tour](#product-experience) |
| Payments or backend engineer | [Architecture](#architecture) → [safety invariants](#payment-safety-invariants) → [API](#api) |
| ML or causal-inference reviewer | [AI model](#ai-model) → [economic objective](#economic-governor) → [canonical artifacts](#repository-artifacts) |
| Evaluator running the project | [Quickstart](#quickstart) → [guided walkthrough](#first-end-to-end-walkthrough) → [testing](#testing) |

The system deliberately keeps its responsibilities separate:

```text
Payment Truth
→ Recovery Eligibility
→ Observable Decision State
→ Counterfactual ML
→ Merchant Economics
→ Deterministic Governor
→ Decision Audit
→ Execution
→ Payment-backed Outcome
```

## Why Recovery Governor

A failed-looking payment does not automatically justify intervention:

- the customer may recover naturally;
- payment state may still be unresolved;
- retries, messages, and payment-method switches have execution costs;
- discounts can increase recovery while destroying merchant value;
- payment truth may change after a decision; and
- executing an action is not the same as recovering revenue.

The system therefore optimizes expected incremental merchant value—not intervention volume or recovery probability alone—subject to authoritative payment truth and deterministic safety constraints.

## What the system does

For each payment journey, the implemented workflow:

1. Receives and materializes immutable payment-event evidence.
2. Establishes authoritative financial truth: `PAID`, `UNCERTAIN`, or `UNPAID`.
3. Applies deterministic recovery eligibility.
4. Builds a decision-time state from observable information only.
5. Scores every structurally available action with the pooled S-Learner.
6. Calculates expected merchant value relative to `NO_ACTION`.
7. Lets the deterministic Economic Governor select a policy-safe, positive-value action.
8. Persists the decision and every candidate score atomically.
9. Creates and atomically claims the recovery action.
10. Rechecks payment truth immediately before execution.
11. Records recovery only after a linked `CAPTURED` payment event.

**ML predicts. The Governor decides. Payment truth remains authoritative.**

## Architecture

```mermaid
flowchart TD
    E[Provider or Demo Events] --> I[Payment Event Ingestion]
    I --> T[Financial Truth]
    T --> G[Recovery Eligibility]
    G --> S[Observable Decision State]
    S --> M[Pooled S-Learner]
    M --> C[Counterfactual Action Scores]
    C --> V[Merchant Economics]
    V --> R[Economic Governor]
    R --> A[Transactional Decision Audit]
    A --> X[Recovery Action]
    X --> P[Payment Truth Recheck]
    P --> K[CAPTURED Payment Evidence]
    K --> O[Verified Recovery Outcome]

    API[FastAPI] --- I
    DB[(PostgreSQL)] --- T
    DB --- A
    UI[Streamlit] --- API
```

FastAPI provides the application boundary, PostgreSQL stores financial and audit state, and Streamlit reads and operates the system only through the HTTP API.

### Decision authority

| Layer | Owns | Does not own |
|---|---|---|
| Financial truth | Whether evidence means `PAID`, `UNCERTAIN`, or `UNPAID` | Recovery recommendations |
| Eligibility | Whether an order may enter recovery | Candidate ranking |
| Counterfactual ML | Predicted recovery under each candidate action | Payment state, policy, or execution |
| Economic Governor | Policy-safe action selection by incremental value | Payment attribution |
| Execution | Claiming and performing the chosen action | Proof of recovery |
| Outcome attribution | Linking a recovery to confirmed `CAPTURED` evidence | Retrospective model authority |

This direction is enforced in code and audit data: the model can inform a decision, but it cannot promote uncertain evidence to failure, execute an action, or declare revenue recovered.

### Operational decision sequence

The runtime keeps state changes on explicit service and transaction boundaries. In particular, decision persistence, action execution, and recovery attribution are separate operations with independent payment-truth checks.

```mermaid
sequenceDiagram
    autonumber
    participant Source as Event Source
    participant API as FastAPI
    participant DB as PostgreSQL
    participant Recovery as Recovery Service
    participant Model as S-Learner
    participant Governor as Economic Governor
    participant Executor as Action Executor
    participant Outcome as Outcome Service

    Source->>API: Payment event
    API->>DB: Persist event + update payment state
    Note over API,DB: One ingestion transaction

    API->>Recovery: Run recovery for order
    Recovery->>DB: Read truth + eligibility
    alt Paid or uncertain
        Recovery-->>API: STOP or WAIT_FOR_TRUTH
    else Eligible unpaid order
        Recovery->>DB: Open recovery case
        Recovery->>Model: Score observable state under each action
        Model-->>Recovery: Counterfactual probabilities
        Recovery->>Governor: Probabilities + policy + economics
        Governor-->>Recovery: Chosen action or NO_ACTION
        Recovery->>DB: Persist decision + candidate scores
        Note over Recovery,DB: Candidate audit is atomic
        Recovery->>DB: Create recovery action
        Recovery->>Executor: Process chosen action
        Executor->>DB: Recheck current payment truth
        alt Still unpaid
            Executor->>DB: Atomically claim PENDING action
        else Paid or uncertain
            Executor->>DB: Mark action BLOCKED
        end
    end

    Source->>API: Later CAPTURED event
    API->>DB: Persist event + materialize PAID
    API->>Outcome: Attribute recovery request
    Outcome->>DB: Verify case, action, payment, and CAPTURED event
    Outcome->>DB: Insert outcome + close case
    Note over Outcome,DB: Attribution and closure are atomic
```

## AI model

The production champion is a pooled **S-Learner**, stored at [`models/s_learner.joblib`](models/s_learner.joblib). It performs treatment-aware supervised prediction of:

```text
P(recovery | observable state, candidate action)
```

The same observable state is scored under each canonical candidate action:

- `NO_ACTION`
- `NUDGE`
- `SWITCH_UPI`
- `SWITCH_CREDIT_CARD`
- `SWITCH_DEBIT_CARD`
- `SWITCH_NETBANKING`
- `OFFER_5`
- `OFFER_10`

`NO_ACTION` is always the natural-recovery baseline. `WAIT_FOR_TRUTH` is a deterministic workflow state for unresolved payment evidence; it is not an ML treatment.

T-Learner, inverse-propensity-weighted S-Learner, and doubly robust learner implementations remain in the repository as experiments and evaluation approaches. They are not the deployed champion. The Economic Governor is deterministic policy and economics logic, not an AI model.

## Economic Governor

Recovery-Max asks:

> Which action gives the highest recovery probability?

The Economic Governor asks:

> Which safe action creates the highest positive incremental merchant value compared with natural recovery?

For candidate action `a`:

```text
Incremental Utility(a)
= Expected Merchant Value(a)
- Expected Merchant Value(NO_ACTION)
```

If no intervention clears policy constraints and produces positive incremental utility, `NO_ACTION` wins.

### From prediction to governed action

```mermaid
flowchart LR
    S[Observable decision state] --> C[Generate structural candidates]
    C --> A[Score the same state under every action]
    A --> M[Pooled S-Learner]
    M --> P[Predicted recovery probabilities]

    P --> E[Expected merchant value]
    B[NO_ACTION natural-recovery baseline] --> E
    K[Processing, action, and discount costs] --> E

    E --> U[Incremental utility vs NO_ACTION]
    G[Deterministic policy guardrails] --> R[Economic Governor]
    U --> R
    T[Merchant utility threshold] --> R

    R --> W{Positive value and policy-safe?}
    W -->|Yes| I[Choose best intervention]
    W -->|No| N[Choose NO_ACTION]
```

The prediction layer never selects an action by itself. The Governor compares policy-eligible candidates in merchant-value terms, and `NO_ACTION` remains the fallback when intervention cannot justify its incremental cost.

### Canonical controlled benchmark

The committed [`data/economic_benchmark_summary.csv`](data/economic_benchmark_summary.csv) reports:

| Strategy | Recovery rate | Intervention rate | Unnecessary intervention | Incremental value / failure |
|---|---:|---:|---:|---:|
| `NO_ACTION` | 61.19% | 0.0% | 0.00% | INR 0.00 |
| `BLANKET_NUDGE` | 63.89% | 37.6% | 19.15% | INR 18.00 |
| `RULE_BASED` | 63.13% | 27.2% | 25.00% | INR 13.16 |
| `S_LEARNER_RECOVERY_MAX` | 65.18% | 83.2% | 43.27% | INR 13.17 |
| `ECONOMIC_GOVERNOR` | 65.09% | 67.6% | 26.63% | INR 25.30 |
| `ECONOMIC_ORACLE` | 67.18% | 67.2% | 0.00% | INR 38.33 |

Compared with Recovery-Max ML, the Economic Governor delivers:

- only **0.09 percentage points** less recovery;
- approximately **1.92×** incremental merchant value per failure;
- **15.6 percentage points** lower intervention; and
- **16.64 percentage points** lower unnecessary intervention.

These are controlled offline evaluation results, not live merchant metrics. `ECONOMIC_ORACLE` is a hindsight upper bound used for regret measurement; it is not a deployable policy.

### Merchant threshold modes

The canonical threshold evaluation exposes policy modes, not separate ML models:

| Mode | Minimum incremental value | Recovery | Intervention | Unnecessary | Incremental value / failure |
|---|---:|---:|---:|---:|---:|
| Value Max (`T=0`) | INR 0 | 65.09% | 67.6% | 26.63% | INR 25.30 |
| Balanced (`T=5`) | INR 5 | 64.33% | 43.6% | 18.35% | INR 22.38 |
| Conservative (`T=10`) | INR 10 | 63.18% | 26.0% | 18.46% | INR 17.73 |

The threshold is the minimum predicted incremental merchant value required before an intervention may be selected.

### Offline evaluation pipeline

The controlled benchmark is produced separately from the operational database. Synthetic hidden variables generate outcomes for evaluation, but they never enter the production feature state.

```mermaid
flowchart TD
    SIM[Synthetic journey simulator]

    subgraph Training[Training path]
        H[Observed historical journeys]
        D[Temporal-safe historical dataset]
        TR[Train pooled S-Learner]
        ART[Canonical model artifact]
    end

    subgraph Evaluation[Controlled evaluation path]
        F[Fixed observable decision states]
        CF[Repeated independent rollouts per action]
        TP[Estimated true counterfactual probabilities]
        MP[Model counterfactual predictions]
        CM[Probability, uplift, policy, and regret metrics]
        PE[Governor and policy comparison]
        BENCH[Canonical benchmark artifacts]
    end

    SIM --> H --> D --> TR --> ART
    SIM --> F --> CF --> TP
    ART --> MP
    F --> MP
    TP --> CM
    MP --> CM
    TP --> PE
    MP --> PE
    PE --> BENCH
```

This provenance is why benchmark percentages are presented as controlled offline evidence rather than live merchant performance.

## Payment-safety invariants

Financial truth always outranks prediction:

```text
CAPTURED → PAID → STOP
CREATED / AUTHORIZED → UNCERTAIN → WAIT_FOR_TRUTH
```

Recovery eligibility remains deliberately conservative:

```text
0 confirmed failures → NO_CONFIRMED_FAILURE
1 confirmed failure  → ALLOW_NATURAL_RETRY
2+ confirmed failures → may become recovery eligible
```

```mermaid
flowchart TD
    O[Order payment evidence] --> C{Any CAPTURED payment?}
    C -->|Yes| PAID[PAID]
    PAID --> STOP[STOP recovery]

    C -->|No| U{Any CREATED or AUTHORIZED payment?}
    U -->|Yes| UNCERTAIN[UNCERTAIN]
    UNCERTAIN --> WAIT[WAIT_FOR_TRUTH]

    U -->|No| UNPAID[UNPAID]
    UNPAID --> AC{Open recovery case exists?}
    AC -->|Yes| OPEN[RECOVERY_ALREADY_OPEN]
    AC -->|No| F{Confirmed failure count}
    F -->|0| NONE[NO_CONFIRMED_FAILURE]
    F -->|1| NATURAL[ALLOW_NATURAL_RETRY]
    F -->|2 or more| ELIGIBLE[MULTIPLE_CONFIRMED_FAILURES]
    ELIGIBLE --> CASE[Open recovery case]
```

`WAIT_FOR_TRUTH` is a deterministic workflow state, not an ML action. An existing open case is also rejected before a second case can be created.

The implementation enforces:

- **One active case per order:** PostgreSQL partial unique index `uq_one_active_recovery_case_per_order`.
- **Idempotent events:** `provider_event_id` is unique; exact redelivery is a safe no-op and conflicting reuse is rejected.
- **Ordered truth:** late or stale events cannot regress terminal `CAPTURED` state.
- **Temporal safety:** historical inputs require `payment.created_at < T`, `event_time < T`, and `received_at < T`.
- **Transactional audit:** feature snapshot, model version, selected action, and every candidate score commit or roll back together.
- **Concurrency-safe action transition:** only one worker can move an action out of `PENDING`.
- **Pre-execution veto:** payment truth is checked again before an intervention executes.
- **Payment-backed attribution:** `RECOVERED` requires relational links to the recovery case, action, payment, and confirmed `CAPTURED` evidence.

Decision does not imply execution. Execution does not imply recovery.

## Data model and audit traceability

PostgreSQL stores both materialized payment state and the evidence needed to reconstruct the recovery lifecycle. The schema keeps financial evidence, decisions, executions, and outcomes relationally linked.

```mermaid
erDiagram
    CUSTOMERS ||--o{ ORDERS : places
    ORDERS ||--o{ PAYMENTS : contains
    PAYMENTS ||--o{ PAYMENT_EVENTS : records

    ORDERS ||--o{ RECOVERY_CASES : may_open
    RECOVERY_CASES ||--o{ RECOVERY_DECISIONS : contains
    RECOVERY_DECISIONS ||--o{ DECISION_ACTION_SCORES : evaluates
    RECOVERY_DECISIONS ||--o{ RECOVERY_ACTIONS : creates

    RECOVERY_CASES ||--o{ RECOVERY_OUTCOMES : resolves_with
    RECOVERY_ACTIONS o|--o{ RECOVERY_OUTCOMES : attributed_through
    PAYMENTS o|--o{ RECOVERY_OUTCOMES : confirmed_by

    CUSTOMERS {
        varchar customer_id PK
        boolean contact_consent
        timestamptz created_at
    }
    ORDERS {
        varchar order_id PK
        varchar customer_id FK
        bigint amount_minor
        varchar currency
        varchar status
    }
    PAYMENTS {
        varchar payment_id PK
        varchar order_id FK
        varchar method
        varchar status
        varchar failure_reason
    }
    PAYMENT_EVENTS {
        bigint event_id PK
        varchar payment_id FK
        varchar provider_event_id UK
        varchar event_type
        timestamptz event_time
        timestamptz received_at
    }
    RECOVERY_CASES {
        varchar recovery_case_id PK
        varchar order_id FK
        varchar status
        varchar closure_reason
        timestamptz opened_at
        timestamptz closed_at
    }
    RECOVERY_DECISIONS {
        varchar decision_id PK
        varchar recovery_case_id FK
        varchar model_version
        varchar proposed_action
        jsonb feature_snapshot
    }
    DECISION_ACTION_SCORES {
        varchar decision_id PK, FK
        varchar action_type PK
        boolean is_eligible
        float predicted_success_probability
        bigint expected_incremental_utility_minor
        bigint expected_merchant_value_minor
    }
    RECOVERY_ACTIONS {
        varchar action_id PK
        varchar decision_id FK
        varchar action_type
        varchar execution_status
        varchar blocked_reason
    }
    RECOVERY_OUTCOMES {
        varchar outcome_id PK
        varchar recovery_case_id FK
        varchar action_id FK
        varchar payment_id FK
        varchar outcome_type
        bigint recovered_amount_minor
    }
```

Two constraints are especially important:

- `payment_events.provider_event_id` is unique, supporting idempotent event delivery.
- `uq_one_active_recovery_case_per_order` is a partial unique index on open cases, preventing concurrent duplicate recovery workflows for one order.

A verified recovery remains traceable from order → case → decision → action → outcome → captured payment → payment event. The canonical schema is versioned in [`database/schema.sql`](database/schema.sql).

## Product experience

The Streamlit product has five connected pages:

- **Overview** — business value, current persisted recovery activity, and the controlled Governor benchmark.
- **Recovery Lab** — deep inspection of one payment journey, counterfactual candidate matrix, Governor decision, and lifecycle audit.
- **Merchant Ops** — many persisted recovery cases, operational filters, distributions, and order drill-down.
- **Economics & Policy** — controlled strategy benchmarks and merchant utility-threshold tradeoffs.
- **System** — architecture, authority boundaries, model action space, enforced guarantees, and known limitations.

### Recovery Lab: one decision, end to end

Recovery Lab freezes the observable decision-time state, compares the same order under every valid action, and exposes the Governor's selected action separately from current payment truth. In the captured scenario below, natural recovery is predicted at 71.0%; the Governor correctly keeps `NO_ACTION` because no permitted intervention creates positive incremental merchant value.

![Recovery Lab decision snapshot and counterfactual comparison](docs/assets/recovery-lab-counterfactual.png)

*Decision-time truth, model output, and merchant value remain visibly separate.*

The explanation layer then shows why the action won and confirms that the feature snapshot, candidate scores, policy reasons, and chosen action were persisted as a decision audit.

![Recovery Lab Governor explanation and decision audit](docs/assets/recovery-lab-governor-audit.png)

*A valid recovery decision can be `NO_ACTION`; restraint is a first-class outcome, not a missing prediction.*

The remaining pages answer different operational questions without duplicating the full decision inspector:

| Page | Question answered |
|---|---|
| Overview | Is the Governor creating merchant value overall? |
| Merchant Ops | Which persisted orders are open, recovered, blocked, or otherwise resolved? |
| Recovery Lab | Why did this payment journey receive this decision? |
| Economics & Policy | Does the strategy beat simpler policies across controlled opportunities? |
| System | How does the engine preserve payment safety and technical auditability? |

## API

The implemented FastAPI routes are:

| Method | Route | Purpose |
|---|---|---|
| `GET` | `/health` | API, database, and model health |
| `POST` | `/api/payment-events` | Idempotently ingest payment evidence and synchronize payment state |
| `POST` | `/api/demo/scenarios` | Create an explicit deterministic demonstration journey |
| `POST` | `/api/orders/{order_id}/recovery` | Run the recovery workflow for an order |
| `GET` | `/api/orders/{order_id}/recovery` | Read the complete persisted recovery view |
| `GET` | `/api/orders/{order_id}/timeline` | Read the payment and recovery lifecycle timeline |
| `GET` | `/api/recovery-cases` | List persisted recovery cases |
| `GET` | `/api/metrics` | Read operational metrics and canonical benchmark artifacts |
| `POST` | `/api/recovery-cases/{case_id}/outcome` | Attribute a payment-backed recovery outcome |

Interactive OpenAPI documentation is available at `http://127.0.0.1:8000/docs` while FastAPI is running.

## Quickstart

### Prerequisites

- Python 3.14 (the verified environment uses Python 3.14.7)
- PostgreSQL 18 (the tracked schema was exported from PostgreSQL 18.6)
- `psql` available in `PATH`, or the full path to the PostgreSQL client

Run all commands from the repository root.

### 1. Clone and create an environment

```bash
git clone <repository-url>
cd recovery_governer
python -m venv .venv
```

Activate it:

```powershell
# Windows PowerShell
.\.venv\Scripts\Activate.ps1
```

```bash
# Linux / macOS
source .venv/bin/activate
```

Install the pinned dependencies:

```bash
python -m pip install -r requirements.txt
python -m pip check
```

### 2. Configure PostgreSQL

Create the database:

```sql
CREATE DATABASE razorpay_recovery;
```

Copy the environment template and replace its placeholders with local credentials:

```powershell
# Windows PowerShell
Copy-Item .env.example .env
```

```bash
# Linux / macOS
cp .env.example .env
```

Initialize the schema:

```bash
psql -U postgres -d razorpay_recovery -f database/schema.sql
```

### 3. Start the applications

In one terminal:

```bash
python -m uvicorn backend.api.main:app --host 127.0.0.1 --port 8000
```

In another terminal:

```bash
python -m streamlit run dashboard/app.py --server.port 8501
```

Open:

- Streamlit UI: `http://127.0.0.1:8501`
- FastAPI: `http://127.0.0.1:8000`
- Swagger UI: `http://127.0.0.1:8000/docs`

The dashboard uses `RECOVERY_API_BASE_URL` from `.env` and otherwise defaults to `http://127.0.0.1:8000`.

### First end-to-end walkthrough

The UI is the clearest way to exercise the complete system:

1. Open **Recovery Lab**.
2. Keep **New customer** and **Two confirmed failures** selected.
3. Initialize the checkout journey. The API persists an order, two failed attempts, and their payment events.
4. Confirm that truth is `UNPAID`, two failures are observed, and the order is recovery eligible.
5. Run recovery intelligence. The real S-Learner scores the candidates and the real Governor makes the decision; no action label is hard-coded by the preset.
6. Inspect the candidate evidence, Governor explanation, decision audit, current outcome, and lifecycle timeline.
7. Open **Merchant Ops** to see the persisted case in the wider operational portfolio.

The same deterministic scenario can be initialized over HTTP:

```bash
curl -X POST http://127.0.0.1:8000/api/demo/scenarios \
  -H "Content-Type: application/json" \
  -d '{"preset":"two_failures","customer_profile":"new_customer"}'
```

Use the returned `order_id` to run recovery with observable runtime signals:

```bash
curl -X POST http://127.0.0.1:8000/api/orders/<order_id>/recovery \
  -H "Content-Type: application/json" \
  -d '{"available_upi":true,"available_credit_card":true,"available_debit_card":true,"available_netbanking":true,"observed_rail_health":0.9,"customer_active":false}'
```

These demo endpoints create persisted synthetic evidence. Viewing Overview, Merchant Ops, or an existing recovery record remains read-only.

## Project structure

```text
backend/
  api/          FastAPI routes, schemas, application boundary, read models
  data_access/  PostgreSQL persistence and transactional state transitions
  services/     payment truth, eligibility, decision, audit, execution, outcome
dashboard/      Streamlit application, pages, navigation, and shared visual language
ml/             production and experimental causal learners and feature pipelines
models/         tracked trained model artifacts
policy/         merchant economics and deterministic Recovery Governor
simulator/      synthetic journeys and counterfactual outcome environment
scripts/        dataset, training, evaluation, inspection, and smoke commands
data/           canonical dataset and benchmark artifacts
database/       reproducible PostgreSQL schema
tests/          unit, integration, transactional, concurrency, API, and UI helpers
```

## Testing

The final verified repository suite is:

```text
231 passed, 1 existing dependency deprecation warning
```

Run it with:

```bash
python -m compileall -q backend ml policy simulator scripts tests dashboard
python -m pytest -q
```

Coverage includes payment truth, event ingestion and idempotency, event ordering, temporal safety, eligibility and natural retry, counterfactual prediction, Governor economics, workflow-failure preservation, transactional audit, concurrency, API behavior, dashboard helpers, and payment-backed outcome attribution.

An end-to-end operational smoke is also available:

```bash
python -m scripts.smoke_operational_recovery
```

It uses PostgreSQL, the tracked production model, the real Governor, decision audit persistence, execution-state transitions, payment-event truth, outcome attribution, and case closure.

## Provider boundary

The recovery core is provider-agnostic. Production payment-provider webhooks can be adapted into the hardened payment-event ingestion contract.

Provider-specific webhook adapters, provider test modes, and live payment-provider integrations are outside the current implementation.

## Known limitations and production hardening

- **Training/serving alignment:** much of the synthetic training population was generated closer to the first-failure decision point, while operational eligibility requires multiple confirmed failures. The safety gate is intentionally unchanged.
- **Historical failure-reason replay:** event history reconstructs payment status at decision time, but `failure_reason` is materialized on the payment row and cannot be replayed perfectly across mutations.
- **Runtime signal sourcing:** payment-method availability, observed rail health, and customer activity must come from provider or application infrastructure in a production integration.
- **Payment accounting:** recovered value currently represents captured order value, not independently verified settlement value with fees, refunds, and net settlement.
- **External side effects:** payment-state and audit guarantees are implemented. Before connecting irreversible external messaging or provider side effects, execution should move behind a transactional claim/outbox boundary with an explicit lock-order design to fully close the payment-versus-action race.
- **Causal validation:** benchmark results use the synthetic counterfactual environment. Production evaluation requires logged interventions and experimental or defensible quasi-experimental data.

## Repository artifacts

The runtime and evaluation paths depend on these tracked canonical assets:

- [`models/s_learner.joblib`](models/s_learner.joblib) — production S-Learner artifact
- [`data/historical_recovery.csv`](data/historical_recovery.csv) — canonical historical training dataset
- [`data/economic_benchmark_summary.csv`](data/economic_benchmark_summary.csv) — policy comparison summary
- [`data/governor_evaluation.csv`](data/governor_evaluation.csv) — detailed Governor evaluation
- [`data/governor_threshold_summary.csv`](data/governor_threshold_summary.csv) — merchant threshold summary
- [`data/governor_threshold_evaluation.csv`](data/governor_threshold_evaluation.csv) — detailed threshold evaluation
- [`database/schema.sql`](database/schema.sql) — reproducible PostgreSQL schema

The public repository contains no real credentials. Copy [`.env.example`](.env.example) to an ignored `.env` file and supply local values before running the applications.
