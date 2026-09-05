from html import escape

import pandas as pd
import streamlit as st

from dashboard.api_client import RecoveryAPIError


POLICY_ORDER = (
    "NO_ACTION",
    "BLANKET_NUDGE",
    "RULE_BASED",
    "S_LEARNER_RECOVERY_MAX",
    "ECONOMIC_GOVERNOR",
    "ECONOMIC_ORACLE",
)

POLICY_LABELS = {
    "NO_ACTION": "No Action",
    "BLANKET_NUDGE": "Blanket Nudge",
    "RULE_BASED": "Rule Based",
    "S_LEARNER_RECOVERY_MAX": "Recovery-Max ML",
    "ECONOMIC_GOVERNOR": "Economic Governor",
    "ECONOMIC_ORACLE": "Economic Oracle",
}

MODE_CONFIG = {
    "GOVERNOR_T0": ("Value Max", "INR 0", "Intervene for any positive incremental value."),
    "GOVERNOR_T5": ("Balanced", "INR 5", "Require a modest value margin before intervening."),
    "GOVERNOR_T10": ("Conservative", "INR 10", "Reserve intervention for stronger economic gains."),
}


def _number(value):
    return float(value or 0)


def _benchmark_values(row):
    return {
        "recovery_rate": _number(row.get("recovery_rate")) * 100,
        "intervention_rate": _number(row.get("intervention_rate")) * 100,
        "unnecessary_rate": _number(row.get("unnecessary_intervention_rate")) * 100,
        "merchant_value": _number(row.get("merchant_value_minor_per_failure")) / 100,
        "incremental_value": _number(row.get("incremental_value_minor_per_failure")) / 100,
        "oracle_regret": _number(row.get("economic_regret_minor_per_failure")) / 100,
    }


def prepare_economics_data(metrics):
    benchmarks = {
        row.get("policy"): _benchmark_values(row)
        for row in metrics.get("canonical_benchmarks", [])
    }
    modes = []
    for row in metrics.get("canonical_thresholds", []):
        policy = row.get("policy")
        if policy in MODE_CONFIG:
            name, threshold, description = MODE_CONFIG[policy]
            modes.append({
                "policy": policy,
                "name": name,
                "threshold": threshold,
                "description": description,
                **_benchmark_values(row),
            })
    modes.sort(key=lambda mode: tuple(MODE_CONFIG).index(mode["policy"]))
    return {"benchmarks": benchmarks, "modes": modes}


def build_strategy_rows(benchmarks):
    rows = []
    for policy in POLICY_ORDER:
        values = benchmarks.get(policy)
        if values is None:
            continue
        rows.append({
            "Strategy": POLICY_LABELS[policy],
            "Recovery": f'{values["recovery_rate"]:.2f}%',
            "Intervention": f'{values["intervention_rate"]:.1f}%',
            "Unnecessary": f'{values["unnecessary_rate"]:.2f}%',
            "Merchant Value / Failure": f'INR {values["merchant_value"]:,.2f}',
            "Incremental Value / Failure": f'INR {values["incremental_value"]:,.2f}',
            "Oracle Regret / Failure": f'INR {values["oracle_regret"]:,.2f}',
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


def render(client):
    st.markdown('<div class="eyebrow">Economics &amp; Policy</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="economics-hero"><div><span>CONTROLLED EVALUATION</span>'
        '<h1>Recover nearly as much revenue. Intervene far more intelligently.</h1>'
        '<p>Canonical offline policy evaluation compares recovery performance, intervention discipline and merchant value across the same opportunities.</p></div>'
        '<div class="evaluation-boundary"><strong>NOT LIVE OPERATIONS</strong>'
        '<span>These results come from committed benchmark artifacts, not today\'s demo database.</span></div></div>',
        unsafe_allow_html=True,
    )

    try:
        metrics = client.get_metrics()
    except RecoveryAPIError as error:
        st.error(str(error))
        st.caption("Start FastAPI to load the canonical benchmark read model.")
        return

    data = prepare_economics_data(metrics)
    benchmarks = data["benchmarks"]
    recovery_max = benchmarks.get("S_LEARNER_RECOVERY_MAX")
    governor = benchmarks.get("ECONOMIC_GOVERNOR")
    oracle = benchmarks.get("ECONOMIC_ORACLE")
    if not recovery_max or not governor:
        st.warning("The canonical Recovery-Max and Economic Governor rows are unavailable.")
        return

    recovery_gap = recovery_max["recovery_rate"] - governor["recovery_rate"]
    value_multiple = governor["incremental_value"] / recovery_max["incremental_value"]
    st.markdown(
        f'<div class="economic-result"><div><span>RECOVERY-MAX ML</span>'
        f'<strong>{recovery_max["recovery_rate"]:.2f}% recovery</strong>'
        f'<small>{recovery_max["intervention_rate"]:.1f}% intervention &middot; '
        f'{recovery_max["unnecessary_rate"]:.2f}% unnecessary<br>INR {recovery_max["incremental_value"]:.2f} incremental value / failure</small></div>'
        '<b>VERSUS</b><div class="governed"><span>ECONOMIC GOVERNOR</span>'
        f'<strong>{governor["recovery_rate"]:.2f}% recovery</strong>'
        f'<small>{governor["intervention_rate"]:.1f}% intervention &middot; '
        f'{governor["unnecessary_rate"]:.2f}% unnecessary<br>INR {governor["incremental_value"]:.2f} incremental value / failure</small></div></div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<div class="benchmark-thesis"><strong>Only {recovery_gap:.2f} percentage points less recovery.</strong>'
        f'<span>The Governor delivers {value_multiple:.2f}&times; the incremental merchant value per failure and cuts unnecessary intervention by '
        f'{recovery_max["unnecessary_rate"] - governor["unnecessary_rate"]:.2f} percentage points.</span></div>',
        unsafe_allow_html=True,
    )

    chart_columns = st.columns(3, gap="large")
    with chart_columns[0]:
        _comparison_chart("Recovery rate", "Governor preserves the recovery outcome", [("Recovery Max", recovery_max["recovery_rate"], f'{recovery_max["recovery_rate"]:.2f}%', "muted"), ("Governor", governor["recovery_rate"], f'{governor["recovery_rate"]:.2f}%', "primary")], 100)
    with chart_columns[1]:
        _comparison_chart("Incremental value / failure", "After action and discount costs", [("Recovery Max", recovery_max["incremental_value"], f'INR {recovery_max["incremental_value"]:.2f}', "muted"), ("Governor", governor["incremental_value"], f'INR {governor["incremental_value"]:.2f}', "success")], max(recovery_max["incremental_value"], governor["incremental_value"]))
    with chart_columns[2]:
        _comparison_chart("Unnecessary intervention", "Lower is better", [("Recovery Max", recovery_max["unnecessary_rate"], f'{recovery_max["unnecessary_rate"]:.2f}%', "danger"), ("Governor", governor["unnecessary_rate"], f'{governor["unnecessary_rate"]:.2f}%', "success")], max(recovery_max["unnecessary_rate"], governor["unnecessary_rate"]))

    thesis_left, thesis_right = st.columns(2, gap="large")
    with thesis_left:
        st.markdown('<div class="strategy-card"><span>RECOVERY MAX ASKS</span><strong>&ldquo;Which action gives the highest recovery probability?&rdquo;</strong></div>', unsafe_allow_html=True)
    with thesis_right:
        st.markdown('<div class="strategy-card governed"><span>ECONOMIC GOVERNOR ASKS</span><strong>&ldquo;Which safe action creates the highest positive incremental merchant value compared with natural recovery?&rdquo;</strong></div>', unsafe_allow_html=True)

    st.markdown('<div class="source-heading benchmark"><div><span class="source-pill benchmark">CANONICAL POLICY BENCHMARK</span><h2>Strategy comparison</h2></div><p>Every row is loaded from the committed benchmark artifact through the metrics API.</p></div>', unsafe_allow_html=True)
    st.dataframe(pd.DataFrame(build_strategy_rows(benchmarks)), hide_index=True, width="stretch")
    if oracle:
        st.caption(f'Economic Oracle is a hindsight reference upper bound ({oracle["recovery_rate"]:.2f}% recovery; INR {oracle["incremental_value"]:.2f} incremental value/failure), not a deployable policy.')

    st.markdown('<div class="source-heading"><div><span class="source-pill benchmark">MERCHANT CONTROL</span><h2>Utility threshold modes</h2></div><p>The threshold is the minimum predicted incremental value required before intervention.</p></div>', unsafe_allow_html=True)
    mode_columns = st.columns(3, gap="large")
    for column, mode in zip(mode_columns, data["modes"]):
        with column:
            st.markdown(
                f'<div class="mode-card"><span>{escape(mode["name"].upper())}</span><strong>{escape(mode["threshold"])} threshold</strong><p>{escape(mode["description"])}</p>'
                f'<div><b>{mode["recovery_rate"]:.2f}%</b> recovery <b>{mode["intervention_rate"]:.1f}%</b> intervention<br><b>INR {mode["incremental_value"]:.2f}</b> incremental value / failure</div></div>',
                unsafe_allow_html=True,
            )

    st.markdown(
        '<div class="baseline-note"><strong>Why NO_ACTION matters</strong><span>NO_ACTION represents natural recovery and remains the zero-incremental-utility baseline. '
        'An intervention must be policy-safe and create positive value above that baseline; otherwise the Governor does nothing.</span></div>',
        unsafe_allow_html=True,
    )
