from html import escape

import pandas as pd
import streamlit as st

from dashboard.api_client import RecoveryAPIError
from dashboard.components.action_matrix import format_minor, humanize_action
from dashboard.components.metric_card import metric_card
from dashboard.navigation import navigate_to


RECOVERY_MAX = "S_LEARNER_RECOVERY_MAX"
ECONOMIC_GOVERNOR = "ECONOMIC_GOVERNOR"


def _number(value):
    return float(value or 0)


def prepare_overview_data(metrics):
    benchmark_by_policy = {
        row.get("policy"): row for row in metrics.get("canonical_benchmarks", [])
    }
    return {
        "live": {
            "total_recovery_cases": int(metrics.get("total_recovery_cases", 0)),
            "open_cases": int(metrics.get("open_cases", 0)),
            "closed_cases": int(metrics.get("closed_cases", 0)),
            "recovered_cases": int(metrics.get("recovered_cases", 0)),
            "recovered_order_value_minor": int(
                metrics.get("recovered_order_value_minor", 0)
            ),
            "action_counts": dict(metrics.get("action_counts") or {}),
        },
        "benchmark": {
            "recovery_max": benchmark_by_policy.get(RECOVERY_MAX),
            "economic_governor": benchmark_by_policy.get(ECONOMIC_GOVERNOR),
        },
    }


def benchmark_summary(benchmark):
    recovery_max = benchmark["recovery_max"]
    governor = benchmark["economic_governor"]
    if not recovery_max or not governor:
        return None
    return {
        "recovery_gap_pp": (
            _number(recovery_max["recovery_rate"])
            - _number(governor["recovery_rate"])
        ) * 100,
        "recovery_max": {
            "recovery_rate": _number(recovery_max["recovery_rate"]) * 100,
            "intervention_rate": _number(recovery_max["intervention_rate"]) * 100,
            "unnecessary_rate": _number(
                recovery_max["unnecessary_intervention_rate"]
            ) * 100,
            "incremental_value": _number(
                recovery_max["incremental_value_minor_per_failure"]
            ) / 100,
        },
        "economic_governor": {
            "recovery_rate": _number(governor["recovery_rate"]) * 100,
            "intervention_rate": _number(governor["intervention_rate"]) * 100,
            "unnecessary_rate": _number(
                governor["unnecessary_intervention_rate"]
            ) * 100,
            "incremental_value": _number(
                governor["incremental_value_minor_per_failure"]
            ) / 100,
        },
    }


def _short_id(value):
    text = str(value or "—")
    return text if len(text) <= 18 else f"…{text[-12:]}"


def build_recent_case_rows(cases):
    rows = []
    for case in cases or []:
        outcome = case.get("outcome_type") or (
            "In recovery" if case.get("status") == "OPEN" else case.get("closure_reason")
        )
        rows.append({
            "Order": _short_id(case.get("order_id")),
            "Amount": format_minor(case.get("amount_minor")),
            "Truth / Case": (
                f"{case.get('financial_truth', '—')} · {case.get('status', '—')}"
            ),
            "Chosen Action": humanize_action(case.get("chosen_action")),
            "Outcome": str(outcome or "—").replace("_", " ").title(),
        })
    return rows


def _comparison_chart(title, subtitle, series, ceiling):
    bars = []
    for label, value, display, tone in series:
        width = max(2.0, min(100.0, value / ceiling * 100)) if ceiling else 0
        bars.append(
            f'<div class="chart-row"><div class="chart-label">{escape(label)}</div>'
            f'<div class="bar-track"><div class="bar-fill {tone}" style="width:{width:.2f}%"></div></div>'
            f'<div class="chart-value">{escape(display)}</div></div>'
        )
    st.markdown(
        f'<div class="comparison-chart"><div class="chart-title">{escape(title)}</div>'
        f'<div class="chart-subtitle">{escape(subtitle)}</div>{"".join(bars)}</div>',
        unsafe_allow_html=True,
    )


def _go_to(page, order_id=None):
    navigate_to(st.session_state, page, order_id=order_id)
    st.rerun()


def render(client):
    st.markdown('<div class="eyebrow">Recovery Governor</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="overview-hero"><div><h1>Recover failed revenue without over-intervening.</h1>'
        '<p>Counterfactual recovery intelligence governed by merchant economics and authoritative payment truth.</p></div>'
        '<div class="hero-proof"><span>PRODUCT THESIS</span><strong>Choose the safe action with positive incremental value—not simply the highest recovery probability.</strong></div></div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="architecture-strip"><b>Payment Truth</b><i>→</i><b>Eligibility</b><i>→</i>'
        '<b>AI Counterfactual Scoring</b><i>→</i><b>Merchant Economics</b><i>→</i>'
        '<b>Governor</b><i>→</i><b>Verified Recovery</b></div>',
        unsafe_allow_html=True,
    )

    try:
        metrics = client.get_metrics()
        cases = client.list_recovery_cases(limit=6)
    except RecoveryAPIError as error:
        st.error(str(error))
        st.caption("Start FastAPI to load the operational and benchmark read models.")
        return

    page_data = prepare_overview_data(metrics)
    live = page_data["live"]
    benchmark = benchmark_summary(page_data["benchmark"])

    st.markdown(
        '<div class="source-heading"><div><span class="source-pill live">LIVE / DEMO OPERATIONS</span>'
        '<h2>Operational demo state</h2></div><p>Derived from current PostgreSQL recovery records. This is not a production merchant portfolio.</p></div>',
        unsafe_allow_html=True,
    )
    columns = st.columns(5)
    live_cards = [
        ("Total cases", f"{live['total_recovery_cases']:,}", "Persisted recovery journeys"),
        ("Open", f"{live['open_cases']:,}", "Currently in recovery"),
        ("Closed", f"{live['closed_cases']:,}", "Resolved or closed"),
        ("Verified recovered", f"{live['recovered_cases']:,}", "Backed by CAPTURED evidence"),
        ("Recovered order value", format_minor(live["recovered_order_value_minor"]), "Confirmed recovered order value"),
    ]
    for column, card in zip(columns, live_cards):
        with column:
            metric_card(*card)

    st.markdown(
        '<div class="source-heading benchmark"><div><span class="source-pill benchmark">EVALUATION BENCHMARK</span>'
        '<h2>Measured economic result</h2></div><p>Controlled evaluation from the canonical policy benchmark artifact—not today\'s operational database.</p></div>',
        unsafe_allow_html=True,
    )
    if benchmark is None:
        st.warning("The canonical Governor comparison is unavailable in the benchmark artifact.")
    else:
        recovery_max = benchmark["recovery_max"]
        governor = benchmark["economic_governor"]
        st.markdown(
            f'<div class="benchmark-thesis"><strong>{benchmark["recovery_gap_pp"]:.2f} percentage points less recovery.</strong>'
            f'<span>Incremental merchant value rises from INR {recovery_max["incremental_value"]:.2f} to '
            f'INR {governor["incremental_value"]:.2f} per failed payment, while unnecessary intervention falls '
            f'from {recovery_max["unnecessary_rate"]:.2f}% to {governor["unnecessary_rate"]:.2f}%.</span></div>',
            unsafe_allow_html=True,
        )
        chart_columns = st.columns(3, gap="large")
        with chart_columns[0]:
            _comparison_chart(
                "Recovery rate",
                "Controlled evaluation",
                [
                    ("Recovery Max", recovery_max["recovery_rate"], f'{recovery_max["recovery_rate"]:.2f}%', "muted"),
                    ("Economic Governor", governor["recovery_rate"], f'{governor["recovery_rate"]:.2f}%', "primary"),
                ],
                100,
            )
        with chart_columns[1]:
            _comparison_chart(
                "Incremental value / failure",
                "After intervention costs",
                [
                    ("Recovery Max", recovery_max["incremental_value"], f'INR {recovery_max["incremental_value"]:.2f}', "muted"),
                    ("Economic Governor", governor["incremental_value"], f'INR {governor["incremental_value"]:.2f}', "success"),
                ],
                max(recovery_max["incremental_value"], governor["incremental_value"]),
            )
        with chart_columns[2]:
            _comparison_chart(
                "Intervention discipline",
                "Intervention / unnecessary",
                [
                    ("Max · intervention", recovery_max["intervention_rate"], f'{recovery_max["intervention_rate"]:.1f}%', "muted"),
                    ("Governor · intervention", governor["intervention_rate"], f'{governor["intervention_rate"]:.1f}%', "primary"),
                    ("Max · unnecessary", recovery_max["unnecessary_rate"], f'{recovery_max["unnecessary_rate"]:.2f}%', "danger"),
                    ("Governor · unnecessary", governor["unnecessary_rate"], f'{governor["unnecessary_rate"]:.2f}%', "success"),
                ],
                100,
            )

    thesis_left, thesis_right = st.columns(2, gap="large")
    with thesis_left:
        st.markdown(
            '<div class="strategy-card"><span>RECOVERY MAX ASKS</span>'
            '<strong>“Which action gives the highest recovery probability?”</strong></div>',
            unsafe_allow_html=True,
        )
    with thesis_right:
        st.markdown(
            '<div class="strategy-card governed"><span>ECONOMIC GOVERNOR ASKS</span>'
            '<strong>“Which safe action creates the highest positive incremental merchant value compared with natural recovery?”</strong></div>',
            unsafe_allow_html=True,
        )

    st.markdown('<div class="section-spacer"></div>', unsafe_allow_html=True)
    heading, action = st.columns([4, 1])
    with heading:
        st.subheader("Recent recovery cases")
        st.caption("A small read-only window into persisted demo journeys.")
    with action:
        if st.button("VIEW ALL CASES", width="stretch", key="overview_all_cases"):
            _go_to("Merchant Ops")

    rows = build_recent_case_rows(cases)
    if rows:
        st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")
        selected_order = st.selectbox(
            "Inspect a recent order",
            options=[case["order_id"] for case in cases],
            format_func=lambda order_id: f"Order {_short_id(order_id)}",
            key="overview_inspect_order",
        )
        if st.button("INSPECT IN RECOVERY LAB", key="overview_inspect", type="primary"):
            _go_to("Recovery Lab", selected_order)
    else:
        st.info("No recovery cases are persisted yet. Create one in Recovery Lab to populate this operational view.")
