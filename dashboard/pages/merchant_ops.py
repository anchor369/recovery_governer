from collections import Counter
from html import escape

import pandas as pd
import streamlit as st

from dashboard.api_client import RecoveryAPIError
from dashboard.components.action_matrix import format_minor, humanize_action
from dashboard.components.metric_card import metric_card
from dashboard.components.status_badge import status_badge, tone_for_status
from dashboard.navigation import navigate_to


ACTION_GROUP_LABELS = {
    "NO_ACTION": "No action",
    "NUDGE": "Nudge",
    "SWITCH_METHOD": "Switch method",
    "OFFER": "Offer",
    "NOT_DECIDED": "Not decided",
}


def action_group(action):
    if not action:
        return "NOT_DECIDED"
    if action.startswith("SWITCH_"):
        return "SWITCH_METHOD"
    if action.startswith("OFFER_"):
        return "OFFER"
    return action


def outcome_group(case):
    if case.get("outcome_type") == "RECOVERED":
        return "Recovered"
    if case.get("status") == "OPEN":
        return "Not yet recovered"
    return str(case.get("closure_reason") or "Other closure").replace("_", " ").title()


def available_case_filters(cases):
    statuses = sorted({case.get("status") for case in cases if case.get("status")})
    outcomes = sorted({outcome_group(case) for case in cases})
    action_groups = sorted(
        {action_group(case.get("chosen_action")) for case in cases},
        key=lambda value: ACTION_GROUP_LABELS.get(value, value),
    )
    return {
        "statuses": ["All", *statuses],
        "outcomes": ["All", *outcomes],
        "actions": ["All", *action_groups],
    }


def filter_recovery_cases(cases, status="All", outcome="All", action="All"):
    return [
        case for case in cases
        if (status == "All" or case.get("status") == status)
        and (outcome == "All" or outcome_group(case) == outcome)
        and (action == "All" or action_group(case.get("chosen_action")) == action)
    ]


def _short_id(value):
    text = str(value or "—")
    return text if len(text) <= 20 else f"…{text[-14:]}"


def build_case_table_rows(cases):
    return [
        {
            "Order": _short_id(case.get("order_id")),
            "Opened": str(case.get("opened_at") or "—")[:16].replace("T", " "),
            "Order Value": format_minor(case.get("amount_minor")),
            "Payment Truth": case.get("financial_truth") or "—",
            "Case": case.get("status") or "—",
            "Chosen Action": humanize_action(case.get("chosen_action")),
            "Execution": case.get("execution_status") or "—",
            "Outcome": outcome_group(case),
        }
        for case in cases
    ]


def _distribution(title, counts, labeler=lambda value: value):
    if not counts:
        st.info(f"No {title.lower()} data yet.")
        return
    maximum = max(counts.values())
    rows = []
    for label, count in sorted(counts.items(), key=lambda item: (-item[1], item[0])):
        width = count / maximum * 100 if maximum else 0
        rows.append(
            f'<div class="distribution-row"><span>{escape(str(labeler(label)))}</span>'
            f'<div class="bar-track"><div class="bar-fill primary" style="width:{width:.2f}%"></div></div>'
            f'<strong>{count}</strong></div>'
        )
    st.markdown(
        f'<div class="distribution-card"><div class="chart-title">{escape(title)}</div>{"".join(rows)}</div>',
        unsafe_allow_html=True,
    )


def _go_to_lab(order_id):
    navigate_to(st.session_state, "Recovery Lab", order_id=order_id)
    st.rerun()


def render(client):
    st.markdown('<div class="eyebrow">Merchant Operations</div>', unsafe_allow_html=True)
    st.title("Recovery case console")
    st.markdown(
        '<div class="page-subtitle">Which failed payments are currently being recovered, waiting, blocked or already resolved?</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="ops-proof"><strong>Many customers → many orders → different decisions → payment-backed outcomes</strong>'
        '<span>Every row is backed by persisted order, payment, decision, action and outcome state in the demo database.</span></div>',
        unsafe_allow_html=True,
    )

    try:
        metrics = client.get_metrics()
        cases = client.list_recovery_cases(limit=500)
    except RecoveryAPIError as error:
        st.error(str(error))
        st.caption("Start FastAPI to load the recovery operations read model.")
        return

    st.markdown(
        '<div class="source-heading"><div><span class="source-pill live">LIVE / DEMO OPERATIONS</span>'
        '<h2>Current demo portfolio</h2></div><p>Read-only view of the current PostgreSQL state. No cases are created by viewing this page.</p></div>',
        unsafe_allow_html=True,
    )
    summary_columns = st.columns(5)
    summary_cards = [
        ("Total cases", f"{int(metrics.get('total_recovery_cases', 0)):,}", "Persisted journeys"),
        ("Open cases", f"{int(metrics.get('open_cases', 0)):,}", "Active recovery work"),
        ("Closed cases", f"{int(metrics.get('closed_cases', 0)):,}", "All closure reasons"),
        ("Recovered", f"{int(metrics.get('recovered_cases', 0)):,}", "Verified CAPTURED evidence"),
        ("Recovered value", format_minor(metrics.get("recovered_order_value_minor", 0)), "Recovered order value"),
    ]
    for column, card in zip(summary_columns, summary_cards):
        with column:
            metric_card(*card)

    if not cases:
        st.info("No recovery cases exist yet. Use Recovery Lab to create a deterministic demo journey; this page will remain read-only.")
        return

    st.subheader("Recovery queue")
    filters = available_case_filters(cases)
    filter_columns = st.columns(3)
    with filter_columns[0]:
        status = st.selectbox("Case status", filters["statuses"], key="ops_status")
    with filter_columns[1]:
        outcome = st.selectbox("Outcome", filters["outcomes"], key="ops_outcome")
    with filter_columns[2]:
        action = st.selectbox(
            "Action",
            filters["actions"],
            format_func=lambda value: ACTION_GROUP_LABELS.get(value, value),
            key="ops_action",
        )

    filtered = filter_recovery_cases(cases, status, outcome, action)
    total_cases = int(metrics.get("total_recovery_cases", len(cases)))
    scope = (
        f"latest {len(cases)} of {total_cases} total cases"
        if total_cases > len(cases)
        else f"all {len(cases)} persisted cases"
    )
    st.caption(f"Showing {len(filtered)} filtered rows from {scope} · select a row or use the case picker")
    if not filtered:
        st.info("No cases match these filters.")
        return

    table_rows = build_case_table_rows(filtered)
    event = st.dataframe(
        pd.DataFrame(table_rows),
        hide_index=True,
        width="stretch",
        height=min(510, 72 + 35 * len(table_rows)),
        on_select="rerun",
        selection_mode="single-row",
        key="ops_case_table",
    )
    selected_rows = event.selection.rows
    if selected_rows:
        st.session_state.ops_selected_case_id = filtered[selected_rows[0]]["recovery_case_id"]

    picker_options = [None, *[case["recovery_case_id"] for case in filtered]]
    previous_case_id = st.session_state.get("ops_selected_case_id")
    picker_index = (
        picker_options.index(previous_case_id)
        if previous_case_id in picker_options
        else 0
    )
    picked_case_id = st.selectbox(
        "Open case inspector",
        options=picker_options,
        index=picker_index,
        format_func=lambda case_id: (
            "Select a recovery case"
            if case_id is None
            else next(
                f"Order {_short_id(case['order_id'])} · {outcome_group(case)}"
                for case in filtered if case["recovery_case_id"] == case_id
            )
        ),
        key="ops_case_picker",
    )
    if picked_case_id is not None:
        st.session_state.ops_selected_case_id = picked_case_id

    selected = next(
        (
            case for case in filtered
            if case["recovery_case_id"] == st.session_state.get("ops_selected_case_id")
        ),
        None,
    )
    if selected:
        st.markdown('<div class="section-spacer"></div>', unsafe_allow_html=True)
        st.subheader("Case inspector")
        outcome_label = outcome_group(selected)
        if selected.get("recovered_amount_minor") is not None:
            outcome_label += f" · {format_minor(selected['recovered_amount_minor'])}"
        st.markdown(
            f'<div class="case-inspector"><div><span>ORDER</span><strong>{escape(_short_id(selected["order_id"]))}</strong></div>'
            f'<div><span>CASE STATE</span>{status_badge(selected["status"], tone_for_status(selected["status"]))}</div>'
            f'<div><span>ACTION</span><strong>{escape(humanize_action(selected.get("chosen_action")))}</strong></div>'
            f'<div><span>EXECUTION</span><strong>{escape(str(selected.get("execution_status") or "—"))}</strong></div>'
            f'<div><span>OUTCOME</span><strong>{escape(outcome_label)}</strong></div></div>',
            unsafe_allow_html=True,
        )
        detail_left, detail_right = st.columns([3, 1])
        with detail_left:
            st.caption(
                f"Case {_short_id(selected['recovery_case_id'])} · Opened {str(selected['opened_at'])[:19].replace('T', ' ')} · "
                f"Closed {str(selected.get('closed_at') or '—')[:19].replace('T', ' ')} · "
                f"Closure {str(selected.get('closure_reason') or '—').replace('_', ' ').title()}"
            )
        with detail_right:
            if st.button("INSPECT FULL DECISION", type="primary", width="stretch", key="ops_inspect"):
                _go_to_lab(selected["order_id"])

    distribution_columns = st.columns(2, gap="large")
    with distribution_columns[0]:
        _distribution(
            "Chosen action distribution",
            Counter(case.get("chosen_action") or "NOT_DECIDED" for case in cases),
            lambda value: humanize_action(value) if value != "NOT_DECIDED" else "Not decided",
        )
    with distribution_columns[1]:
        _distribution("Case / outcome distribution", Counter(outcome_group(case) for case in cases))
