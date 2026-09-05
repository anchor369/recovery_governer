import uuid

import streamlit as st

from dashboard.api_client import RecoveryAPIError
from dashboard.components.action_matrix import (
    format_minor,
    format_probability,
    humanize_action,
    render_action_matrix,
)
from dashboard.components.governor_reasoning import render_governor_reasoning
from dashboard.components.metric_card import metric_card
from dashboard.components.section_header import section_header
from dashboard.components.status_badge import status_badge, tone_for_status
from dashboard.components.timeline import render_timeline


PRESETS = {
    "two_failures": "Two confirmed failures",
    "technical_failure": "Technical failure",
    "wrong_pin": "Wrong PIN",
    "no_contact_consent": "No contact consent",
    "active_customer": "Customer actively retrying",
    "payment_uncertain": "Payment uncertain",
    "already_paid": "Already paid",
    "natural_retry": "Natural retry",
}

SESSION_DEFAULTS = {
    "lab_scenario": None,
    "lab_workflow": None,
    "lab_recovery": None,
    "lab_timeline": [],
    "lab_outcome": None,
    "lab_order_id": None,
    "lab_case_id": None,
    "lab_decision_id": None,
    "lab_action_id": None,
}


def initialize_lab_state():
    for key, value in SESSION_DEFAULTS.items():
        st.session_state.setdefault(key, value)


def extract_identifiers(scenario, workflow):
    scenario = scenario or {}
    workflow = workflow or {}
    recovery_case = workflow.get("case") or {}
    decision = workflow.get("decision") or {}
    action = workflow.get("execution_action") or {}
    return {
        "order_id": scenario.get("order_id"),
        "case_id": recovery_case.get("recovery_case_id"),
        "decision_id": decision.get("decision_id"),
        "action_id": action.get("action_id"),
    }


def chosen_score(workflow):
    workflow = workflow or {}
    chosen = workflow.get("chosen_action")
    return next(
        (
            score
            for score in workflow.get("candidate_action_scores", [])
            if score.get("action_type") == chosen
        ),
        None,
    )


def safety_message(workflow):
    state = (workflow or {}).get("workflow_state")
    messages = {
        "STOP": ("PAID → STOP", "Payment truth stopped recovery before ML."),
        "WAIT_FOR_TRUTH": (
            "UNCERTAIN → WAIT FOR TRUTH",
            "The payment state is unresolved, so no intervention is allowed.",
        ),
        "ALLOW_NATURAL_RETRY": (
            "1 CONFIRMED FAILURE → NATURAL RETRY",
            "The first confirmed failure is reserved for natural customer recovery.",
        ),
    }
    return messages.get(state)


def _refresh_order(client, order_id):
    st.session_state.lab_recovery = client.get_recovery(order_id)
    st.session_state.lab_timeline = client.get_timeline(order_id)


def _store_identifiers():
    identifiers = extract_identifiers(
        st.session_state.lab_scenario, st.session_state.lab_workflow
    )
    for name, value in identifiers.items():
        st.session_state[f"lab_{name}"] = value


def _show_api_error(error):
    st.error(str(error))
    st.caption("Check that FastAPI is running and retry the last action.")


def render_scenario_zone(client):
    section_header(
        "01 · Scenario",
        "Create a payment state, then run the Governor",
        "Scenario creation establishes payment evidence. Recovery is a separate, explicit decision.",
    )
    preset = st.selectbox(
        "Scenario preset",
        options=list(PRESETS),
        format_func=PRESETS.get,
        key="lab_preset",
    )
    create_col, run_col = st.columns([1, 1])
    with create_col:
        create_clicked = st.button(
            "CREATE SCENARIO", width="stretch", key="create_scenario"
        )
    with run_col:
        run_clicked = st.button(
            "RUN RECOVERY GOVERNOR",
            type="primary",
            width="stretch",
            key="run_governor",
        )

    if create_clicked:
        try:
            with st.spinner("Creating observable payment evidence…"):
                scenario = client.create_demo_scenario(preset)
            for key, value in SESSION_DEFAULTS.items():
                st.session_state[key] = value
            st.session_state.lab_scenario = scenario
            st.session_state.lab_order_id = scenario["order_id"]
            st.session_state.lab_notice = (
                f"Scenario ready · Order {scenario['order_id']}"
            )
            st.rerun()
        except RecoveryAPIError as error:
            _show_api_error(error)

    if run_clicked:
        scenario = st.session_state.lab_scenario
        if scenario is None:
            st.warning("Create a scenario before running the Governor.")
            return
        try:
            with st.spinner("Evaluating payment truth, counterfactuals and merchant value…"):
                workflow = client.run_recovery(
                    scenario["order_id"], scenario["metadata"]["runtime_signals"]
                )
                st.session_state.lab_workflow = workflow
                _store_identifiers()
                _refresh_order(client, scenario["order_id"])
        except RecoveryAPIError as error:
            _show_api_error(error)

    scenario = st.session_state.lab_scenario
    if scenario:
        if notice := st.session_state.pop("lab_notice", None):
            st.success(notice)
        st.caption(
            f"Preset: {PRESETS[scenario['preset']]}  ·  Order: {scenario['order_id']}  ·  "
            f"Payment attempts: {len(scenario['payment_ids'])}"
        )


def render_decision_summary():
    workflow = st.session_state.lab_workflow
    recovery = st.session_state.lab_recovery
    if not workflow or not recovery:
        return

    section_header(
        "02 · Decision summary",
        "Truth first. Economics second. Action last.",
    )
    message = safety_message(workflow)
    if message:
        st.markdown(
            f'<div class="safety-callout"><strong>{message[0]}</strong><br>{message[1]}</div>',
            unsafe_allow_html=True,
        )

    case = recovery.get("recovery_case") or {}
    decision = recovery.get("decision") or {}
    selected = chosen_score(workflow) or {}
    cards = [
        ("Financial truth", recovery.get("financial_truth", "—"), "Authoritative payment state"),
        ("Recovery eligibility", workflow.get("reason", "—"), "Deterministic workflow gate"),
        ("Recovery case", case.get("status", "Not opened"), case.get("recovery_case_id")),
        ("AI model", decision.get("model_version", "Not invoked"), "Predictive, not authoritative"),
        ("Chosen action", humanize_action(workflow.get("chosen_action")), "Governor selection"),
        (
            "Predicted recovery",
            format_probability(selected.get("predicted_success_probability")),
            "Chosen-action counterfactual",
        ),
        (
            "Incremental value",
            format_minor(selected.get("expected_incremental_utility_minor")),
            "Relative to NO_ACTION",
        ),
        (
            "Execution",
            (workflow.get("execution_action") or {}).get("execution_status", "Not created"),
            "Separate from recovery outcome",
        ),
    ]
    columns = st.columns(4)
    for index, card in enumerate(cards):
        with columns[index % 4]:
            metric_card(*card)

    truth = recovery.get("financial_truth")
    state = workflow.get("workflow_state")
    st.markdown(
        f"{status_badge(truth, tone_for_status(truth))} &nbsp; "
        f"{status_badge(state, tone_for_status(state))}",
        unsafe_allow_html=True,
    )


def render_decision_evidence():
    workflow = st.session_state.lab_workflow
    if not workflow:
        return
    scores = workflow.get("candidate_action_scores") or []
    if not scores:
        return

    section_header(
        "03 · Counterfactual evidence",
        "AI Counterfactual Action Scores",
        "The model estimates each possible outcome. The Governor decides whether acting is safe and economically justified.",
    )
    st.markdown("**AI prediction ≠ Governor decision**")
    render_action_matrix(scores, workflow.get("chosen_action"))

    reasoning_col, timeline_col = st.columns([1, 1], gap="large")
    with reasoning_col:
        section_header("04 · Governor", "Why this action won")
        with st.container(border=True):
            render_governor_reasoning(scores, workflow.get("chosen_action"))
    with timeline_col:
        section_header("05 · Evidence trail", "Lifecycle timeline")
        render_timeline(st.session_state.lab_timeline)


def render_capture_zone(client):
    workflow = st.session_state.lab_workflow or {}
    recovery = st.session_state.lab_recovery or {}
    scenario = st.session_state.lab_scenario or {}
    action = workflow.get("execution_action") or {}
    outcome = recovery.get("outcome")

    if action.get("execution_status") != "EXECUTED":
        return

    st.divider()
    section_header(
        "06 · Verified outcome",
        "Execution is not recovery",
        "A recovery is attributed only after new CAPTURED payment evidence is persisted.",
    )

    if outcome:
        st.success("CAPTURED → PAID → RECOVERED → CLOSED")
        st.caption(
            f"Outcome {outcome['outcome_id']} · Payment {outcome['payment_id']} · "
            f"Recovered order value {format_minor(outcome['recovered_amount_minor'])}"
        )
        return

    if st.button(
        "SIMULATE CAPTURED PAYMENT",
        type="primary",
        width="stretch",
        key="simulate_capture",
    ):
        payment_id = scenario["payment_ids"][-1]
        provider_event_id = f"EV_UI_CAPTURE_{uuid.uuid4().hex[:12]}"
        try:
            with st.spinner("Persisting CAPTURED evidence and verifying attribution…"):
                client.record_payment_event(
                    payment_id=payment_id,
                    provider_event_id=provider_event_id,
                    event_type="CAPTURED",
                )
                st.session_state.lab_outcome = client.record_recovery_outcome(
                    case_id=st.session_state.lab_case_id,
                    action_id=st.session_state.lab_action_id,
                    payment_id=payment_id,
                )
                _refresh_order(client, scenario["order_id"])
            st.rerun()
        except RecoveryAPIError as error:
            _show_api_error(error)


def render(client):
    initialize_lab_state()
    st.markdown('<div class="eyebrow">Recovery Governor</div>', unsafe_allow_html=True)
    st.title("Recovery Lab")
    st.markdown(
        '<div class="page-subtitle">Trace one failed-payment decision from observable truth '
        'through counterfactual scoring, merchant economics and payment-backed recovery.</div>',
        unsafe_allow_html=True,
    )
    st.markdown("<br>", unsafe_allow_html=True)
    render_scenario_zone(client)
    render_decision_summary()
    render_decision_evidence()
    render_capture_zone(client)
