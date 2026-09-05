import uuid
from html import escape

import streamlit as st

from dashboard.api_client import RecoveryAPIError
from dashboard.components.action_matrix import (
    format_minor,
    format_percentage_points,
    format_probability,
    humanize_action,
    humanize_method,
    humanize_reason,
    render_action_matrix,
)
from dashboard.components.governor_reasoning import render_governor_reasoning
from dashboard.components.metric_card import metric_card
from dashboard.components.section_header import section_header
from dashboard.components.status_badge import status_badge, tone_for_status
from dashboard.components.timeline import render_timeline


PAYMENT_SITUATIONS = {
    "two_failures": "Two confirmed failures",
    "technical_failure": "Technical failure",
    "wrong_pin": "Wrong PIN",
    "no_contact_consent": "No contact consent",
    "active_customer": "Customer actively retrying",
    "payment_uncertain": "Payment uncertain",
    "already_paid": "Already paid",
    "natural_retry": "Natural retry",
}

CUSTOMER_PROFILES = {
    "new_customer": "New customer",
    "loyal_returning": "Loyal returning customer",
    "mixed_history": "Mixed payment history",
}

GATE_LABELS = {
    "MULTIPLE_CONFIRMED_FAILURES": "Recovery eligible",
    "ORDER_ALREADY_PAID": "Stop — order already paid",
    "PAYMENT_STATE_UNCERTAIN": "Wait for payment truth",
    "ALLOW_NATURAL_RETRY": "Allow natural retry",
    "NO_CONFIRMED_FAILURE": "No confirmed failure",
    "RECOVERY_CASE_ALREADY_EXISTS": "Recovery already active",
}

SESSION_DEFAULTS = {
    "lab_scenario": None,
    "lab_workflow": None,
    "lab_recovery": None,
    "lab_timeline": [],
    "lab_decision_snapshot": None,
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


def score_for_action(workflow, action):
    return next(
        (
            score for score in (workflow or {}).get("candidate_action_scores", [])
            if score.get("action_type") == action
        ),
        None,
    )


def chosen_score(workflow):
    return score_for_action(workflow, (workflow or {}).get("chosen_action"))


def comparison_summary(workflow):
    baseline = score_for_action(workflow, "NO_ACTION") or {}
    selected = chosen_score(workflow) or {}
    return {
        "baseline_action": "NO_ACTION",
        "baseline_probability": baseline.get("predicted_success_probability"),
        "baseline_value_minor": baseline.get("expected_merchant_value_minor"),
        "chosen_action": (workflow or {}).get("chosen_action"),
        "chosen_probability": selected.get("predicted_success_probability"),
        "chosen_value_minor": selected.get("expected_merchant_value_minor"),
        "uplift": selected.get("uplift"),
        "incremental_value_minor": selected.get("expected_incremental_utility_minor"),
    }


def safety_message(workflow):
    state = (workflow or {}).get("workflow_state")
    messages = {
        "STOP": ("PAID → STOP", "Payment truth stopped recovery before the AI model."),
        "WAIT_FOR_TRUTH": (
            "UNCERTAIN → WAIT FOR TRUTH",
            "The payment state is unresolved, so no recovery intervention is allowed.",
        ),
        "ALLOW_NATURAL_RETRY": (
            "1 CONFIRMED FAILURE → NATURAL RETRY",
            "The first confirmed failure is reserved for natural customer recovery.",
        ),
    }
    return messages.get(state)


def capture_decision_snapshot(scenario, workflow, recovery):
    journey = (scenario or {}).get("journey") or {}
    return {
        "customer": journey.get("customer") or {},
        "order": journey.get("order") or {},
        "recovery_gate": journey.get("recovery_gate") or {},
        "runtime_signals": (scenario or {}).get("metadata", {}).get("runtime_signals", {}),
        "financial_truth": (recovery or {}).get("financial_truth"),
        "eligibility_reason": (workflow or {}).get("reason"),
        "chosen_action": (workflow or {}).get("chosen_action"),
        "execution_status": ((workflow or {}).get("execution_action") or {}).get("execution_status"),
    }


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
    st.caption("Check that FastAPI is running, then retry the last action.")


def _humanize(value):
    return str(value or "—").replace("_", " ").title()


def render_demo_context():
    st.markdown(
        """
        <div class="demo-banner">
          <div><strong>DEMO ENVIRONMENT</strong><br>
          Synthetic payment journey · Real Recovery Governor · Real persisted audit trail</div>
          <div class="demo-detail"><strong>Synthetic:</strong> checkout data and future CAPTURED event<br>
          <strong>Real logic:</strong> PostgreSQL, payment truth, S-Learner inference, economics, policy, audit and attribution</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_configuration(client):
    section_header(
        "01 · Payment journey simulator",
        "Configure a merchant checkout",
        "Create persisted demo evidence first. Recovery intelligence is a separate action.",
    )
    profile_col, situation_col = st.columns(2)
    with profile_col:
        customer_profile = st.selectbox(
            "Customer profile",
            options=list(CUSTOMER_PROFILES),
            format_func=CUSTOMER_PROFILES.get,
            key="lab_customer_profile",
        )
    with situation_col:
        payment_situation = st.selectbox(
            "Payment situation",
            options=list(PAYMENT_SITUATIONS),
            format_func=PAYMENT_SITUATIONS.get,
            key="lab_payment_situation",
        )

    if st.button(
        "INITIALIZE CHECKOUT JOURNEY",
        type="primary",
        width="stretch",
        key="initialize_journey",
    ):
        try:
            with st.spinner("Persisting synthetic customer, order and payment evidence…"):
                scenario = client.create_demo_scenario(
                    payment_situation,
                    customer_profile,
                )
            for key, value in SESSION_DEFAULTS.items():
                st.session_state[key] = value
            st.session_state.lab_scenario = scenario
            st.session_state.lab_order_id = scenario["order_id"]
            _refresh_order(client, scenario["order_id"])
            st.session_state.lab_notice = "Checkout journey initialized from persisted demo data."
            st.rerun()
        except RecoveryAPIError as error:
            _show_api_error(error)


def render_checkout_context():
    scenario = st.session_state.lab_scenario
    if not scenario:
        return
    journey = scenario["journey"]
    customer = journey["customer"]
    order = journey["order"]
    history = journey["history"]
    attempts = journey["current_payment_attempts"]

    if notice := st.session_state.pop("lab_notice", None):
        st.success(notice)

    section_header("02 · Merchant checkout", "What was persisted")
    st.markdown(
        f'<div class="order-strip"><div><span>ORDER</span><strong>{escape(order["order_id"])}</strong></div>'
        f'<div><span>ORDER VALUE</span><strong>{format_minor(order["amount_minor"])}</strong></div>'
        f'<div><span>PAYMENT TRUTH</span>{status_badge(order["financial_truth"], tone_for_status(order["financial_truth"]))}</div></div>',
        unsafe_allow_html=True,
    )

    customer_col, attempts_col = st.columns([0.9, 1.35], gap="large")
    with customer_col:
        st.markdown("#### Customer & observed history")
        st.markdown(f"**{customer['profile_label']}**  \n{customer['tenure_days']} days observed tenure")
        h1, h2, h3 = st.columns(3)
        h1.metric("Prior orders", history["prior_checkout_count"])
        h2.metric("Successful", history["prior_success_count"])
        h3.metric("Failed", history["prior_failure_count"])
        st.caption(
            f"Median prior order: {format_minor(history['median_prior_amount_minor'])} · "
            f"Current / median: {history['amount_ratio']:.2f}× · "
            f"Contact consent: {'Yes' if customer['contact_consent'] else 'No'} · "
            f"Currently retrying: "
            f"{'Yes' if scenario['metadata']['runtime_signals']['customer_active'] else 'No'}"
        )
        if history["orders"]:
            with st.expander("Persisted prior orders"):
                for prior in history["orders"]:
                    st.markdown(
                        f"**{format_minor(prior['amount_minor'])}** · "
                        f"{_humanize(prior['financial_truth'])} · "
                        f"{str(prior['created_at'])[:10]}"
                    )
        else:
            st.info("Cold start: no earlier checkout history exists for this customer.")

    with attempts_col:
        st.markdown("#### Current payment attempts")
        for attempt in attempts:
            reason = (
                humanize_reason(attempt.get("failure_reason"))
                if attempt.get("failure_reason")
                else "No failure reason"
            )
            st.markdown(
                f'<div class="attempt-row"><div class="attempt-index">{attempt["attempt_number"]}</div>'
                f'<div><strong>{humanize_method(attempt["method"])}</strong><br><span>{escape(reason)}</span></div>'
                f'<div>{status_badge(attempt["status"], tone_for_status(attempt["status"]))}</div></div>',
                unsafe_allow_html=True,
            )


def render_recovery_gate(client):
    scenario = st.session_state.lab_scenario
    if not scenario:
        return
    gate = scenario["journey"]["recovery_gate"]
    section_header(
        "03 · Recovery gate",
        "Can this order enter recovery?",
        "This read-only gate is evaluated before the AI model is invoked.",
    )
    col1, col2, col3 = st.columns(3)
    col1.metric("Payment truth", gate["financial_truth"])
    col2.metric("Confirmed failures", gate["confirmed_failure_count"])
    col3.metric("Active case at initialization", "Yes" if gate["active_recovery_case"] else "No")
    result = GATE_LABELS.get(gate["reason"], _humanize(gate["reason"]))
    tone = "success" if gate["eligible"] else tone_for_status(gate["financial_truth"])
    st.markdown(
        f'<div class="gate-result"><span>GATE RESULT</span>{status_badge(result, tone)}</div>',
        unsafe_allow_html=True,
    )

    if st.button(
        "RUN RECOVERY INTELLIGENCE",
        type="primary",
        width="stretch",
        key="run_recovery_intelligence",
    ):
        try:
            with st.spinner("Evaluating truth, state, counterfactuals and merchant economics…"):
                workflow = client.run_recovery(
                    scenario["order_id"],
                    scenario["metadata"]["runtime_signals"],
                )
                st.session_state.lab_workflow = workflow
                _store_identifiers()
                _refresh_order(client, scenario["order_id"])
                st.session_state.lab_decision_snapshot = capture_decision_snapshot(
                    scenario,
                    workflow,
                    st.session_state.lab_recovery,
                )
            st.rerun()
        except RecoveryAPIError as error:
            _show_api_error(error)


def render_safety_result():
    workflow = st.session_state.lab_workflow
    message = safety_message(workflow)
    if not message:
        return
    section_header("04 · Recovery result", "Payment truth remains authoritative")
    st.markdown(
        f'<div class="safety-callout"><strong>{message[0]}</strong><br>{message[1]}<br>'
        '<span>No candidate predictions, Governor selection or action execution occurred.</span></div>',
        unsafe_allow_html=True,
    )


def render_decision_snapshot():
    workflow = st.session_state.lab_workflow
    snapshot = st.session_state.lab_decision_snapshot
    if not workflow or not snapshot or not workflow.get("candidate_action_scores"):
        return
    selected = chosen_score(workflow) or {}
    decision = workflow.get("decision") or {}

    section_header(
        "04 · Decision snapshot",
        "At decision time",
        "Frozen in this UI session before any later CAPTURED payment changes current truth.",
    )
    columns = st.columns(4)
    cards = [
        ("Payment truth", snapshot["financial_truth"], "At recovery decision time"),
        ("Eligibility", "Recovery eligible", "Multiple confirmed failures"),
        ("Chosen action", humanize_action(workflow.get("chosen_action")), "Economic Governor"),
        ("Execution", snapshot["execution_status"], "Decision is separate from execution"),
        ("Predicted recovery", format_probability(selected.get("predicted_success_probability")), "Under chosen action"),
        ("Lift vs natural", format_percentage_points(selected.get("uplift")), "Compared with NO_ACTION"),
        ("Incremental value", format_minor(selected.get("expected_incremental_utility_minor")), "After intervention costs"),
        ("Model", decision.get("model_version", "—"), "Predictive, not authoritative"),
    ]
    for index, card in enumerate(cards):
        with columns[index % 4]:
            metric_card(*card)


def render_ai_model():
    workflow = st.session_state.lab_workflow
    if not workflow or not workflow.get("candidate_action_scores"):
        return
    summary = comparison_summary(workflow)
    scores = workflow["candidate_action_scores"]

    section_header("05 · AI counterfactual model", "What does the model predict?")
    st.markdown(
        '<div class="model-question"><span>QUESTION</span><strong>For the same currently unpaid order, '
        'what is the predicted probability that it eventually recovers under each possible recovery action?</strong>'
        '<div class="controlled-row"><b>SAME CUSTOMER</b><b>SAME ORDER</b><b>SAME PAYMENT STATE</b>'
        '<em>Change only: recovery action</em></div></div>',
        unsafe_allow_html=True,
    )

    natural_col, versus_col, governed_col = st.columns([1, 0.25, 1])
    with natural_col:
        st.markdown(
            f'<div class="comparison-card baseline"><span>NATURAL RECOVERY · NO ACTION</span>'
            f'<strong>{format_probability(summary["baseline_probability"])}</strong>'
            f'<small>{format_minor(summary["baseline_value_minor"])} expected merchant value</small></div>',
            unsafe_allow_html=True,
        )
    with versus_col:
        st.markdown('<div class="versus">VS</div>', unsafe_allow_html=True)
    with governed_col:
        st.markdown(
            f'<div class="comparison-card governed"><span>BEST GOVERNED ACTION</span>'
            f'<strong>{format_probability(summary["chosen_probability"])}</strong>'
            f'<small>{escape(humanize_action(summary["chosen_action"]))} · '
            f'{format_percentage_points(summary["uplift"])} · '
            f'{format_minor(summary["incremental_value_minor"])} incremental</small></div>',
            unsafe_allow_html=True,
        )

    st.markdown("#### Detailed candidate evidence")
    st.caption(
        "Predicted recovery is the estimated recovery probability under each action. "
        "Lift and incremental value are measured against NO_ACTION, the natural-recovery baseline."
    )
    render_action_matrix(scores, workflow.get("chosen_action"))


def render_governance_pipeline():
    workflow = st.session_state.lab_workflow
    if not workflow or not workflow.get("candidate_action_scores"):
        return
    st.markdown(
        """
        <div class="governance-pipeline">
          <div><span>AI MODEL</span><strong>Predicts candidate outcomes</strong></div><b>→</b>
          <div><span>ECONOMIC GOVERNOR</span><strong>Applies policy + economics</strong></div><b>→</b>
          <div><span>PAYMENT TRUTH</span><strong>Vetoes execution and verifies recovery</strong></div>
        </div>
        <div class="invariant-line">AI prediction ≠ final decision · Governor decision ≠ execution · Execution ≠ recovery · Recovery requires CAPTURED evidence</div>
        """,
        unsafe_allow_html=True,
    )


def render_governor_and_audit():
    workflow = st.session_state.lab_workflow
    if not workflow or not workflow.get("candidate_action_scores"):
        return
    section_header("06 · Economic Governor", "Why this action won")
    left, right = st.columns([1.1, 0.9], gap="large")
    with left:
        with st.container(border=True):
            render_governor_reasoning(
                workflow["candidate_action_scores"],
                workflow.get("chosen_action"),
                st.session_state.lab_decision_snapshot or {},
            )
    with right:
        st.markdown("#### Decision audit")
        st.markdown(
            "The feature snapshot, model version, candidate scores, policy reasons and chosen action were persisted atomically."
        )
        with st.expander("Technical decision details"):
            st.json({
                "order_id": st.session_state.lab_order_id,
                "recovery_case_id": st.session_state.lab_case_id,
                "decision_id": st.session_state.lab_decision_id,
                "action_id": st.session_state.lab_action_id,
                "model_version": (workflow.get("decision") or {}).get("model_version"),
            })


def render_current_outcome(client):
    workflow = st.session_state.lab_workflow or {}
    recovery = st.session_state.lab_recovery or {}
    scenario = st.session_state.lab_scenario or {}
    action = workflow.get("execution_action") or {}
    if not workflow.get("candidate_action_scores"):
        return

    section_header(
        "07 · Current outcome",
        "What is true now?",
        "Current payment evidence is intentionally separate from the earlier decision snapshot.",
    )
    outcome = recovery.get("outcome")
    case = recovery.get("recovery_case") or {}
    columns = st.columns(4)
    columns[0].metric("Financial truth", recovery.get("financial_truth", "—"))
    columns[1].metric("Payment evidence", "CAPTURED" if outcome else "Awaiting capture")
    columns[2].metric("Recovery outcome", (outcome or {}).get("outcome_type", "Not attributed"))
    columns[3].metric("Recovery case", case.get("status", "—"))

    if outcome:
        st.success("CAPTURED → PAID → RECOVERED → CLOSED")
        st.markdown(
            f"**Recovered order value:** {format_minor(outcome['recovered_amount_minor'])}  "
            f"\nPayment-backed attribution is complete."
        )
        return

    st.warning(
        f"Action status: {action.get('execution_status', '—')}. Execution alone is not recovery."
    )
    if action.get("execution_status") == "EXECUTED" and st.button(
        "SIMULATE FUTURE CAPTURED PAYMENT",
        type="primary",
        width="stretch",
        key="simulate_capture",
    ):
        payment_id = scenario["payment_ids"][-1]
        try:
            with st.spinner("Persisting CAPTURED evidence and verifying attribution…"):
                client.record_payment_event(
                    payment_id=payment_id,
                    provider_event_id=f"EV_UI_CAPTURE_{uuid.uuid4().hex[:12]}",
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


def render_timeline_section():
    workflow = st.session_state.lab_workflow
    if not workflow:
        return
    section_number = "08" if workflow.get("candidate_action_scores") else "05"
    section_header(f"{section_number} · Payment journey", "Lifecycle timeline")
    render_timeline(st.session_state.lab_timeline)


def render(client):
    initialize_lab_state()
    st.markdown('<div class="eyebrow">Recovery Governor</div>', unsafe_allow_html=True)
    st.title("Recovery Lab")
    st.markdown(
        '<div class="page-subtitle">Understand why one payment journey received one recovery decision—and how recovered revenue is verified.</div>',
        unsafe_allow_html=True,
    )
    render_demo_context()
    render_configuration(client)
    render_checkout_context()
    render_recovery_gate(client)
    render_safety_result()
    render_decision_snapshot()
    render_ai_model()
    render_governance_pipeline()
    render_governor_and_audit()
    render_current_outcome(client)
    render_timeline_section()
