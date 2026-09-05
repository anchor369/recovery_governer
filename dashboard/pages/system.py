import streamlit as st


def render(_client):
    st.markdown('<div class="eyebrow">Technical assurance</div>', unsafe_allow_html=True)
    st.title("System")
    st.markdown(
        '<div class="surface"><h3>Architecture and guarantees</h3>'
        '<p>Payment-truth, transaction, model and execution guarantees will be documented here next.</p></div>',
        unsafe_allow_html=True,
    )
