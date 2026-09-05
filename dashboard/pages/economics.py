import streamlit as st


def render(_client):
    st.markdown('<div class="eyebrow">Merchant value</div>', unsafe_allow_html=True)
    st.title("Economics & Policy")
    st.markdown(
        '<div class="surface"><h3>Policy and benchmark comparison</h3>'
        '<p>Economic thresholds, recovery tradeoffs and intervention efficiency will be presented here next.</p></div>',
        unsafe_allow_html=True,
    )
