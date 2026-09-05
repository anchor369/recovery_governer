from html import escape

import streamlit as st


def render_timeline(items):
    if not items:
        st.info("Lifecycle events will appear here as the scenario progresses.")
        return

    blocks = []
    for item in items:
        details = item.get("details") or {}
        detail_text = " · ".join(
            f"{str(key).replace('_', ' ').title()}: {value}"
            for key, value in details.items()
            if value is not None
        )
        blocks.append(
            '<div class="timeline-item">'
            f'<div class="timeline-title">{escape(str(item.get("title", "Event")))}</div>'
            f'<div class="timeline-meta">{escape(str(item.get("type", "")))} · '
            f'{escape(str(item.get("timestamp", "")))}</div>'
            f'<div class="timeline-meta">{escape(detail_text)}</div></div>'
        )
    st.markdown(
        f'<div class="surface"><div class="timeline">{"".join(blocks)}</div></div>',
        unsafe_allow_html=True,
    )
