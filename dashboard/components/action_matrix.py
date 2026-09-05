import pandas as pd
import streamlit as st


ACTION_LABELS = {
    "NO_ACTION": "No action",
    "NUDGE": "Customer nudge",
    "SWITCH_UPI": "Switch to UPI",
    "SWITCH_CREDIT_CARD": "Switch to credit card",
    "SWITCH_DEBIT_CARD": "Switch to debit card",
    "SWITCH_NETBANKING": "Switch to netbanking",
    "OFFER_5": "Offer 5%",
    "OFFER_10": "Offer 10%",
}


def humanize_action(action):
    return ACTION_LABELS.get(action, str(action or "—").replace("_", " ").title())


def format_probability(value):
    return "—" if value is None else f"{float(value):.1%}"


def format_minor(value):
    return "—" if value is None else f"INR {float(value) / 100:,.2f}"


def build_action_rows(scores, chosen_action):
    rows = []
    for score in scores or []:
        action = score.get("action_type")
        rows.append(
            {
                "Action": humanize_action(action),
                "Policy Allowed": "Allowed" if score.get("is_eligible") else "Blocked",
                "Predicted Recovery": format_probability(
                    score.get("predicted_success_probability")
                ),
                "Recovery Uplift": format_probability(score.get("uplift")),
                "Expected Merchant Value": format_minor(
                    score.get("expected_merchant_value_minor")
                ),
                "Incremental Utility": format_minor(
                    score.get("expected_incremental_utility_minor")
                ),
                "Policy Reason": score.get("ineligible_reason") or "—",
                "Selected": action == chosen_action,
                "_utility": score.get("expected_incremental_utility_minor"),
                "_action": action,
            }
        )
    return rows


def render_action_matrix(scores, chosen_action):
    rows = build_action_rows(scores, chosen_action)
    if not rows:
        st.info("Counterfactual scores are available only when the ML decision stage runs.")
        return

    frame = pd.DataFrame(rows).drop(columns=["_utility", "_action"])
    utility_column = frame.columns.get_loc("Incremental Utility")

    def style_row(row):
        source = rows[row.name]
        if row["Selected"]:
            styles = ["background-color:#eef0ff;font-weight:700"] * len(row)
        elif row["Policy Allowed"] == "Blocked":
            styles = ["color:#7b8494;background-color:#f7f8fa"] * len(row)
        elif source["_action"] == "NO_ACTION":
            styles = ["background-color:#fafafa"] * len(row)
        else:
            styles = [""] * len(row)

        utility = source["_utility"]
        if utility is not None and row["Policy Allowed"] != "Blocked":
            utility_color = "#16794a" if utility >= 0 else "#b42318"
            styles[utility_column] += f";color:{utility_color};font-weight:700"
        return styles

    st.dataframe(
        frame.style.apply(style_row, axis=1),
        hide_index=True,
        width="stretch",
        column_config={
            "Selected": st.column_config.CheckboxColumn("Selected", disabled=True),
        },
    )
