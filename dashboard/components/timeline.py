from datetime import datetime
from html import escape

import streamlit as st

from dashboard.components.action_matrix import (
    format_minor,
    humanize_action,
    humanize_method,
    humanize_reason,
)


def _humanize(value):
    return str(value or "").replace("_", " ").title()


def _clock_time(value):
    timestamp = value if isinstance(value, datetime) else datetime.fromisoformat(str(value))
    return timestamp.strftime("%H:%M:%S")


def build_timeline_rows(items):
    rows = []
    for item in items or []:
        event_type = item.get("type")
        title = item.get("title")
        details = item.get("details") or {}

        if event_type == "PAYMENT_EVENT":
            if title == "FAILED":
                display_title = "Payment attempt failed"
                summary = " · ".join(filter(None, [
                    humanize_method(details.get("method")),
                    humanize_reason(details.get("failure_reason")),
                ]))
                tone = "danger"
            elif title == "CAPTURED":
                display_title = "Payment captured"
                summary = " · ".join(filter(None, [
                    humanize_method(details.get("method")),
                    format_minor(details.get("amount_minor")),
                ]))
                tone = "success"
            else:
                display_title = f"Payment {_humanize(title).lower()}"
                summary = humanize_method(details.get("method"))
                tone = "warning"
        elif event_type == "RECOVERY_CASE_OPENED":
            display_title, summary, tone = "Recovery case opened", "Eligible order entered recovery", "info"
        elif event_type == "RECOVERY_DECISION":
            display_title, summary, tone = "Recovery decision", humanize_action(title), "info"
        elif event_type == "RECOVERY_ACTION":
            status = details.get("execution_status")
            display_title = "Action executed" if status == "EXECUTED" else "Action updated"
            summary, tone = humanize_action(title), "success" if status == "EXECUTED" else "warning"
        elif event_type == "RECOVERY_OUTCOME":
            display_title = "Revenue recovered" if title == "RECOVERED" else _humanize(title)
            summary, tone = format_minor(details.get("recovered_amount_minor")), "success"
        elif event_type == "RECOVERY_CASE_CLOSED":
            display_title, summary, tone = "Recovery case closed", _humanize(title), "success"
        else:
            display_title, summary, tone = _humanize(title or event_type), "", "neutral"

        rows.append({
            "_timestamp": datetime.fromisoformat(str(item["timestamp"])),
            "_priority": {
                "RECOVERY_CASE_OPENED": 1,
                "RECOVERY_DECISION": 2,
                "RECOVERY_ACTION": 3,
                "PAYMENT_EVENT": 4 if title == "CAPTURED" else 0,
                "RECOVERY_OUTCOME": 5,
                "RECOVERY_CASE_CLOSED": 6,
            }.get(event_type, 9),
            "time": _clock_time(item["timestamp"]),
            "title": display_title,
            "summary": summary,
            "tone": tone,
        })
    rows.sort(key=lambda row: (
        row["_timestamp"].replace(microsecond=0),
        row["_priority"],
        row["_timestamp"],
    ))
    return [
        {key: value for key, value in row.items() if not key.startswith("_")}
        for row in rows
    ]


def render_timeline(items):
    if not items:
        st.info("Lifecycle events will appear here as the payment journey progresses.")
        return

    blocks = []
    for row in build_timeline_rows(items):
        blocks.append(
            f'<div class="timeline-item tone-dot-{row["tone"]}">'
            f'<div class="timeline-time">{escape(row["time"])}</div>'
            f'<div class="timeline-title">{escape(row["title"])}</div>'
            f'<div class="timeline-summary">{escape(row["summary"])}</div></div>'
        )
    st.markdown(
        f'<div class="timeline">{"".join(blocks)}</div>',
        unsafe_allow_html=True,
    )
    with st.expander("Technical audit details"):
        st.json(items, expanded=False)
