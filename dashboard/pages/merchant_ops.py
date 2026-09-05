import streamlit as st


def render(_client):
    st.markdown('<div class="eyebrow">Operations</div>', unsafe_allow_html=True)
    st.title("Merchant Ops")
    st.markdown(
        '<div class="surface"><h3>Recovery case operations</h3>'
        '<p>Case queues, action states and verified outcome workflows will be built here next.</p></div>',
        unsafe_allow_html=True,
    )
