from html import escape

import streamlit as st

from dashboard.components.action_matrix import format_minor, humanize_action


def render_governor_reasoning(scores, chosen_action):
    scores = scores or []
    selected = next((row for row in scores if row.get("action_type") == chosen_action), None)
    blocked = [row for row in scores if not row.get("is_eligible")]
    negative = [
        row
        for row in scores
        if row.get("is_eligible")
        and row.get("expected_incremental_utility_minor") is not None
        and row["expected_incremental_utility_minor"] < 0
    ]

    if selected:
        utility = format_minor(selected.get("expected_incremental_utility_minor"))
        if chosen_action == "NO_ACTION":
            st.markdown(
                "**No action** remained the natural-recovery baseline because no "
                "policy-eligible intervention produced greater persisted incremental value."
            )
        else:
            st.markdown(
                f"**{escape(humanize_action(chosen_action))}** was policy allowed and "
                f"beat the NO_ACTION baseline by **{escape(utility)}** in persisted "
                "incremental utility."
            )
    else:
        st.info("Governor reasoning is available after a persisted decision.")

    if blocked:
        st.markdown("**Policy-blocked alternatives**")
        for row in blocked[:3]:
            reason = str(row.get("ineligible_reason") or "Blocked by deterministic policy")
            st.markdown(f"- {humanize_action(row.get('action_type'))}: `{reason}`")

    if negative:
        st.markdown("**Economically negative alternatives**")
        for row in sorted(
            negative, key=lambda item: item["expected_incremental_utility_minor"]
        )[:3]:
            st.markdown(
                f"- {humanize_action(row.get('action_type'))}: "
                f"{format_minor(row.get('expected_incremental_utility_minor'))}"
            )

    st.markdown(
        """
        <div class="layer-row"><div class="layer-name">AI layer</div>
        <div class="layer-copy">Predicts recovery outcomes for each candidate action.</div></div>
        <div class="layer-row"><div class="layer-name">Economic Governor</div>
        <div class="layer-copy">Applies merchant economics and deterministic policy.</div></div>
        <div class="layer-row"><div class="layer-name">Payment truth</div>
        <div class="layer-copy">Remains authoritative before decision, execution and recovery.</div></div>
        """,
        unsafe_allow_html=True,
    )
