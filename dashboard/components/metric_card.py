from html import escape

import streamlit as st


def metric_card(label, value, help_text=None):
    help_html = f'<div class="metric-help">{escape(str(help_text))}</div>' if help_text else ""
    st.markdown(
        '<div class="metric-card">'
        f'<div class="metric-label">{escape(str(label))}</div>'
        f'<div class="metric-value">{escape(str(value))}</div>{help_html}</div>',
        unsafe_allow_html=True,
    )
