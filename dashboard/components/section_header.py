import streamlit as st


def section_header(eyebrow, title, description=None):
    st.markdown(f'<div class="eyebrow">{eyebrow}</div>', unsafe_allow_html=True)
    st.subheader(title)
    if description:
        st.markdown(f'<div class="page-subtitle">{description}</div>', unsafe_allow_html=True)
