import streamlit as st

from dashboard.api_client import RecoveryAPIClient, RecoveryAPIError
from dashboard.pages import economics, merchant_ops, overview, recovery_lab, system
from dashboard.theme import apply_theme


st.set_page_config(
    page_title="Recovery Governor",
    page_icon="RG",
    layout="wide",
    initial_sidebar_state="expanded",
)
apply_theme()


@st.cache_resource
def get_api_client():
    return RecoveryAPIClient()


client = get_api_client()

with st.sidebar:
    st.markdown("## Recovery Governor")
    st.caption("Payment-safe revenue recovery")
    st.divider()
    page = st.radio(
        "Navigation",
        ["Overview", "Recovery Lab", "Merchant Ops", "Economics & Policy", "System"],
        index=1,
        label_visibility="collapsed",
    )
    st.divider()
    try:
        health = client.health_check()
        if health.get("database") == "connected" and health.get("model") == "loaded":
            st.success("Backend connected")
        else:
            st.warning("Backend health is degraded")
    except RecoveryAPIError:
        st.error("FastAPI unavailable")
        st.caption(f"Expected at {client.base_url}")
        if st.button("Retry connection", width="stretch"):
            st.rerun()


PAGES = {
    "Overview": overview.render,
    "Recovery Lab": recovery_lab.render,
    "Merchant Ops": merchant_ops.render,
    "Economics & Policy": economics.render,
    "System": system.render,
}
PAGES[page](client)
