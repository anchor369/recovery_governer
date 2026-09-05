import streamlit as st


THEME_CSS = """
<style>
:root { --navy:#14213d; --ink:#233044; --muted:#667085; --line:#e4e7ec;
        --surface:#ffffff; --canvas:#f6f7f9; --indigo:#4457d9; }
.stApp { background:var(--canvas); color:var(--ink); }
[data-testid="stSidebar"] { background:#111b31; }
[data-testid="stSidebar"] * { color:#e9edf7; }
.block-container { max-width:1280px; padding-top:2.2rem; padding-bottom:4rem; }
h1,h2,h3 { color:var(--navy); letter-spacing:-0.025em; }
.eyebrow { color:var(--indigo); font-size:.72rem; font-weight:700;
           letter-spacing:.13em; text-transform:uppercase; }
.page-subtitle { color:var(--muted); max-width:760px; margin-top:-.5rem; }
.surface { background:var(--surface); border:1px solid var(--line); border-radius:10px;
           padding:1.2rem 1.35rem; box-shadow:0 1px 2px rgba(16,24,40,.03); }
.metric-card { background:#fff; border:1px solid var(--line); border-radius:9px;
               padding:1rem 1.05rem; min-height:108px; }
.metric-label { color:var(--muted); font-size:.72rem; font-weight:700;
                letter-spacing:.08em; text-transform:uppercase; }
.metric-value { color:var(--navy); font-size:1.2rem; font-weight:720; margin-top:.45rem; }
.metric-help { color:var(--muted); font-size:.76rem; margin-top:.25rem; }
.status-badge { display:inline-flex; align-items:center; padding:.25rem .58rem;
                border-radius:999px; font-size:.73rem; font-weight:700; }
.tone-success { color:#087443; background:#eaf7f0; border:1px solid #b9e5cc; }
.tone-warning { color:#8a4b08; background:#fff6e5; border:1px solid #f5d18b; }
.tone-danger { color:#b42318; background:#fff0ee; border:1px solid #f3c1bc; }
.tone-info { color:#3448c5; background:#eef0ff; border:1px solid #cbd0ff; }
.tone-neutral { color:#475467; background:#f2f4f7; border:1px solid #dfe3e8; }
.safety-callout { border-left:4px solid var(--indigo); background:#fff; padding:1rem 1.2rem;
                  border-radius:6px; margin:.8rem 0 1.2rem; }
.timeline { border-left:2px solid #d7dce5; margin-left:.5rem; padding-left:1.35rem; }
.timeline-item { position:relative; padding:0 0 1.25rem .25rem; }
.timeline-item:before { content:''; position:absolute; width:10px; height:10px;
                        border-radius:50%; background:#5968dd; left:-1.72rem; top:.35rem;
                        box-shadow:0 0 0 4px #eef0ff; }
.timeline-title { color:var(--navy); font-weight:700; }
.timeline-meta { color:var(--muted); font-size:.78rem; margin-top:.18rem; }
.layer-row { display:grid; grid-template-columns:140px 1fr; gap:1rem; padding:.6rem 0;
             border-bottom:1px solid #eef0f3; }
.layer-row:last-child { border-bottom:0; }
.layer-name { color:var(--navy); font-weight:700; }
.layer-copy { color:var(--muted); }
div.stButton > button { border-radius:7px; font-weight:700; border:1px solid #4457d9; }
div.stButton > button[kind="primary"] { background:#3f51d7; }
</style>
"""


def apply_theme():
    st.markdown(THEME_CSS, unsafe_allow_html=True)
