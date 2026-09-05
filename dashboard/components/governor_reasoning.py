import streamlit as st

from dashboard.components.action_matrix import (
    format_minor,
    format_percentage_points,
    format_probability,
    humanize_action,
)


def score_for_action(scores, action):
    return next((score for score in scores or [] if score.get("action_type") == action), None)


def _humanize_reason(reason):
    return str(reason or "Blocked by deterministic policy").replace("_", " ").title()


def render_governor_reasoning(scores, chosen_action, decision_snapshot):
    selected = score_for_action(scores, chosen_action)
    baseline = score_for_action(scores, "NO_ACTION")
    if not selected or not baseline:
        st.info("Governor reasoning is available after a persisted decision.")
        return

    st.markdown(f"### Why {humanize_action(chosen_action)}?")
    if chosen_action == "NO_ACTION":
        st.markdown(
            "No permitted intervention created more expected merchant value than natural recovery."
        )
    else:
        probability_col, value_col = st.columns(2)
        with probability_col:
            st.caption("PREDICTED RECOVERY")
            st.markdown(
                f"**{format_probability(baseline.get('predicted_success_probability'))} → "
                f"{format_probability(selected.get('predicted_success_probability'))}**  "
                f"\n{format_percentage_points(selected.get('uplift'))} lift"
            )
        with value_col:
            st.caption("EXPECTED MERCHANT VALUE")
            st.markdown(
                f"**{format_minor(baseline.get('expected_merchant_value_minor'))} → "
                f"{format_minor(selected.get('expected_merchant_value_minor'))}**  "
                f"\n{format_minor(selected.get('expected_incremental_utility_minor'))} incremental"
            )

    st.caption("POLICY CHECKS")
    st.markdown("✓ Permitted by deterministic policy")
    if chosen_action == "NUDGE":
        customer = decision_snapshot.get("customer") or {}
        signals = decision_snapshot.get("runtime_signals") or {}
        st.markdown(
            f"✓ Contact consent: {'available' if customer.get('contact_consent') else 'not available'}  "
            f"\n✓ Customer currently retrying: {'yes' if signals.get('customer_active') else 'no'}"
        )

    negative = sorted(
        (
            score for score in scores
            if score.get("is_eligible")
            and score.get("expected_incremental_utility_minor") is not None
            and score["expected_incremental_utility_minor"] < 0
        ),
        key=lambda score: score["expected_incremental_utility_minor"],
    )
    if negative:
        st.caption("WHY NOT A COSTLIER ALTERNATIVE?")
        for score in negative[:3]:
            st.markdown(
                f"**{humanize_action(score['action_type'])}** · "
                f"{format_minor(score['expected_incremental_utility_minor'])} incremental value"
            )

    blocked = [score for score in scores if not score.get("is_eligible")]
    if blocked:
        with st.expander("Policy-blocked alternatives"):
            for score in blocked:
                st.markdown(
                    f"**{humanize_action(score['action_type'])}** · "
                    f"{_humanize_reason(score.get('ineligible_reason'))}"
                )
