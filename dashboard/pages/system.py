from html import escape

import streamlit as st

from dashboard.components.action_matrix import ACTION_LABELS


PIPELINE_ROWS = (
    ("Evidence", ("Payment Events", "Financial Truth", "Eligibility", "Observable State")),
    ("Decision", ("Causal S-Learner", "Counterfactual Scores", "Merchant Economics", "Governor")),
    ("Proof", ("Decision Audit", "Execution", "Captured Payment", "Verified Recovery")),
)

SAFETY_GUARANTEES = (
    ("Authoritative truth", "CAPTURED means PAID and stops recovery; unresolved states wait for truth.", "success"),
    ("Idempotent event ingestion", "A provider event ID is processed once; duplicate delivery has no duplicate effect.", "info"),
    ("Monotonic event ordering", "Late or stale provider states cannot regress newer materialized payment truth.", "info"),
    ("Temporal feature cutoffs", "Historical features use only payments and events observable before decision time.", "warning"),
    ("One active case", "A database partial unique index permits only one open recovery case per order.", "neutral"),
    ("Atomic decision audit", "The decision header and every candidate score commit together or roll back together.", "neutral"),
    ("Concurrency-safe execution", "Only one worker can claim a pending recovery action transition.", "warning"),
    ("Payment-backed recovery", "RECOVERED requires a linked CAPTURED payment event; execution alone is not recovery.", "success"),
    ("Bounded database pooling", "Application access uses a bounded PostgreSQL connection pool with explicit lifecycle.", "neutral"),
)


def render(_client):
    st.markdown(
        '<div class="eyebrow">System Assurance</div>', unsafe_allow_html=True
    )
    st.markdown(
        '<div class="system-hero"><div><span>PAYMENT-SAFE BY DESIGN</span>'
        '<h1>Prediction proposes. Policy governs. Payment truth decides.</h1>'
        '<p>The engine preserves financial authority from immutable payment evidence through audited action and verified recovery.</p></div>'
        '<div class="system-invariant"><strong>NON-NEGOTIABLE</strong><span>Decision is not execution.<br>Execution is not recovery.<br>Recovery requires CAPTURED evidence.</span></div></div>',
        unsafe_allow_html=True,
    )

    st.markdown('<div class="source-heading"><div><span class="source-pill live">SYSTEM ARCHITECTURE</span><h2>Evidence to verified outcome</h2></div><p>Each boundary has one job and a distinct source of authority.</p></div>', unsafe_allow_html=True)
    pipeline_html = []
    stage_index = 1
    for row_name, steps in PIPELINE_ROWS:
        rendered = []
        for step in steps:
            rendered.append(
                f'<div><span>{stage_index:02d}</span><strong>{escape(step)}</strong></div>'
            )
            stage_index += 1
        rendered_steps = '<i>&rarr;</i>'.join(rendered)
        pipeline_html.append(f'<section><b>{escape(row_name)}</b><main>{rendered_steps}</main></section>')
    st.markdown(f'<div class="system-pipeline">{"".join(pipeline_html)}</div>', unsafe_allow_html=True)

    st.markdown('<h2 class="compact-heading">Three authority layers</h2>', unsafe_allow_html=True)
    authority_columns = st.columns(3, gap="large")
    authority_cards = (
        ("01 / AI MODEL", "Estimates counterfactual recovery", "Scores the same observable state under each canonical action. It predicts probabilities; it does not decide truth or policy."),
        ("02 / ECONOMIC GOVERNOR", "Selects safe positive value", "Applies deterministic constraints and compares merchant value against natural recovery before choosing an action."),
        ("03 / PAYMENT TRUTH", "Authorizes outcome", "Confirmed CAPTURED evidence stops recovery and is required before any recovered outcome can be attributed."),
    )
    for column, (label, title, copy) in zip(authority_columns, authority_cards):
        with column:
            st.markdown(f'<div class="authority-card"><span>{escape(label)}</span><strong>{escape(title)}</strong><p>{escape(copy)}</p></div>', unsafe_allow_html=True)

    st.markdown('<div class="source-heading"><div><span class="source-pill benchmark">MODEL &amp; ACTION SPACE</span><h2>What the learner is allowed to do</h2></div><p>The deployed champion is fixed; this page does not retrain or replace it.</p></div>', unsafe_allow_html=True)
    model_column, actions_column = st.columns([1, 1.5], gap="large")
    with model_column:
        st.markdown(
            '<div class="model-spec"><span>PRODUCTION CHAMPION</span><strong>Pooled S-Learner</strong>'
            '<dl><dt>Artifact</dt><dd>models/s_learner.joblib</dd><dt>Inputs</dt><dd>Observable decision-time features</dd>'
            '<dt>Output</dt><dd>Recovery probability by treatment</dd><dt>Authority</dt><dd>Predictive only</dd></dl></div>',
            unsafe_allow_html=True,
        )
    with actions_column:
        action_chips = ''.join(f'<span>{escape(action)}</span>' for action in ACTION_LABELS)
        st.markdown(
            f'<div class="action-space"><span>CANONICAL TREATMENTS</span><div>{action_chips}</div>'
            '<p><b>WAIT_FOR_TRUTH is intentionally absent.</b> It is a deterministic workflow state for unresolved payment evidence, never an ML treatment.</p></div>',
            unsafe_allow_html=True,
        )

    st.markdown('<div class="source-heading"><div><span class="source-pill live">SAFETY GUARANTEES</span><h2>Controls enforced across the lifecycle</h2></div><p>These are executable invariants and persistence guarantees, not model promises.</p></div>', unsafe_allow_html=True)
    guarantees = ''.join(
        f'<div class="guarantee-card {escape(tone)}"><span>{index:02d}</span><strong>{escape(title)}</strong><p>{escape(copy)}</p></div>'
        for index, (title, copy, tone) in enumerate(SAFETY_GUARANTEES, start=1)
    )
    st.markdown(f'<div class="guarantee-grid">{guarantees}</div>', unsafe_allow_html=True)

    stack_column, quality_column = st.columns([1, 1.15], gap="large")
    with stack_column:
        st.markdown('<h2 class="compact-heading">Technical stack</h2>', unsafe_allow_html=True)
        st.markdown(
            '<div class="stack-card"><span>Python 3.14</span><span>FastAPI</span><span>Streamlit</span>'
            '<span>PostgreSQL 18</span><span>psycopg 3</span><span>scikit-learn</span><span>pandas</span><span>pytest</span></div>',
            unsafe_allow_html=True,
        )
    with quality_column:
        st.markdown('<h2 class="compact-heading">Verified quality status</h2>', unsafe_allow_html=True)
        st.markdown(
            '<div class="quality-card"><div><strong>231</strong><span>tests passing</span></div>'
            '<div><strong>1</strong><span>existing Starlette deprecation warning</span></div>'
            '<p>Coverage spans financial truth, event ingestion, temporal safety, eligibility, Governor economics, transactional audit, concurrency, APIs and dashboard helpers.</p></div>',
            unsafe_allow_html=True,
        )

    st.markdown('<div class="source-heading"><div><span class="source-pill benchmark">KNOWN BOUNDARIES</span><h2>Deliberate limitations</h2></div><p>Clear constraints are safer than implied production readiness.</p></div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="limitations-grid">'
        '<div><strong>Training / serving alignment</strong><span>Synthetic training opportunities are not yet fully aligned to the production two-failure eligibility point.</span></div>'
        '<div><strong>Payment accounting</strong><span>Recovered value is captured order value, not independently verified net settlement value.</span></div>'
        '<div><strong>Runtime signals</strong><span>Rail availability, health and customer activity remain integration-provided signals.</span></div>'
        '<div><strong>Provider boundary</strong><span>The event contract is provider-agnostic; provider-specific webhook adapters are outside the current implementation.</span></div>'
        '</div>',
        unsafe_allow_html=True,
    )
