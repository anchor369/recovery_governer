import streamlit as st


def render(_client):
    st.markdown('<div class="eyebrow">Portfolio intelligence</div>', unsafe_allow_html=True)
    st.title("Overview")
    st.markdown(
        '<div class="surface"><h3>Economic recovery overview</h3>'
        '<p>Portfolio recovery, intervention and incremental merchant-value signals will appear here next.</p></div>',
        unsafe_allow_html=True,
    )
