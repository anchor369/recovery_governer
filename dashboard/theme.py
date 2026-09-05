import streamlit as st


THEME_CSS = """
<style>
:root { --navy:#172033; --ink:#253044; --muted:#667085; --line:#e2e6ec;
        --surface:#ffffff; --canvas:#f6f7f9; --indigo:#4656d8; }
.stApp { background:var(--canvas); color:var(--ink); }
[data-testid="stSidebar"] { background:#111a2e; border-right:0; }
[data-testid="stSidebar"] * { color:#edf1f8; }
[data-testid="stSidebarNav"] { display:none; }
.block-container { max-width:1240px; padding-top:1.7rem; padding-bottom:3rem; }
h1,h2,h3,h4 { color:var(--navy); letter-spacing:-.025em; }
h1 { font-size:2.15rem !important; margin-bottom:.2rem !important; }
h3 { margin-top:.15rem !important; }
.eyebrow { color:var(--indigo); font-size:.7rem; font-weight:800;
           letter-spacing:.14em; text-transform:uppercase; }
.page-subtitle { color:var(--muted); max-width:850px; margin-bottom:1rem; }
.surface { background:var(--surface); border:1px solid var(--line); border-radius:9px;
           padding:1.15rem 1.3rem; }
.metric-card { background:#fff; border:1px solid var(--line); border-radius:8px;
               padding:.9rem 1rem; min-height:98px; margin-bottom:.65rem; }
.metric-label { color:var(--muted); font-size:.68rem; font-weight:800;
                letter-spacing:.08em; text-transform:uppercase; }
.metric-value { color:var(--navy); font-size:1.08rem; font-weight:750; margin-top:.38rem; }
.metric-help { color:var(--muted); font-size:.73rem; margin-top:.22rem; }
.status-badge { display:inline-flex; align-items:center; padding:.25rem .58rem;
                border-radius:999px; font-size:.72rem; font-weight:750; }
.tone-success { color:#087443; background:#eaf7f0; border:1px solid #b9e5cc; }
.tone-warning { color:#8a4b08; background:#fff6e5; border:1px solid #f5d18b; }
.tone-danger { color:#b42318; background:#fff0ee; border:1px solid #f3c1bc; }
.tone-info { color:#3448c5; background:#eef0ff; border:1px solid #cbd0ff; }
.tone-neutral { color:#475467; background:#f2f4f7; border:1px solid #dfe3e8; }
.demo-banner { display:grid; grid-template-columns:1fr 1.3fr; gap:1.4rem; color:#344054;
               background:#eef0ff; border:1px solid #cfd4ff; border-radius:8px;
               padding:.85rem 1rem; margin:.8rem 0 1.4rem; font-size:.8rem; }
.demo-banner strong { color:#2937ad; font-size:.72rem; letter-spacing:.06em; }
.demo-detail { border-left:1px solid #cfd4ff; padding-left:1.2rem; }
.order-strip { display:grid; grid-template-columns:1.3fr .8fr .8fr; gap:1rem;
               background:#fff; border:1px solid var(--line); border-radius:8px;
               padding:1rem 1.15rem; margin-bottom:1rem; }
.order-strip div { display:flex; flex-direction:column; gap:.35rem; }
.order-strip span { color:var(--muted); font-size:.66rem; font-weight:800; letter-spacing:.08em; }
.order-strip strong { color:var(--navy); font-size:1rem; }
.attempt-row { display:grid; grid-template-columns:36px 1fr auto; align-items:center; gap:.8rem;
               background:#fff; border-bottom:1px solid #edf0f4; padding:.72rem .2rem; }
.attempt-index { display:grid; place-items:center; width:28px; height:28px; border-radius:50%;
                 background:#f0f2f7; color:#475467; font-weight:750; }
.attempt-row span { color:var(--muted); font-size:.78rem; }
.gate-result { display:flex; justify-content:space-between; align-items:center; background:#fff;
               border:1px solid var(--line); padding:.7rem .9rem; border-radius:7px; margin:.5rem 0 .8rem; }
.gate-result>span { color:var(--muted); font-size:.68rem; font-weight:800; letter-spacing:.08em; }
.safety-callout { border-left:4px solid #d04437; background:#fff; padding:1rem 1.2rem;
                  border-radius:6px; margin:.7rem 0 1rem; }
.safety-callout span { color:var(--muted); font-size:.8rem; }
.model-question { background:#172033; color:#f4f6fb; border-radius:8px; padding:1rem 1.15rem; margin-bottom:1rem; }
.model-question>span { display:block; color:#aeb8ff; font-size:.67rem; font-weight:800; letter-spacing:.1em; }
.model-question>strong { display:block; max-width:850px; margin:.35rem 0 .85rem; font-size:1rem; }
.controlled-row { display:flex; flex-wrap:wrap; gap:.55rem; align-items:center; }
.controlled-row b { background:#27334c; padding:.25rem .48rem; border-radius:4px; font-size:.67rem; }
.controlled-row em { color:#c8cfdb; font-size:.74rem; margin-left:.25rem; }
.comparison-card { display:flex; flex-direction:column; min-height:125px; background:#fff;
                   border:1px solid var(--line); border-radius:8px; padding:1rem 1.1rem; }
.comparison-card span { color:var(--muted); font-size:.68rem; font-weight:800; letter-spacing:.08em; }
.comparison-card strong { color:var(--navy); font-size:2rem; margin:.25rem 0; }
.comparison-card small { color:var(--muted); }
.comparison-card.governed { border-color:#adb5ff; box-shadow:inset 3px 0 #4656d8; }
.versus { text-align:center; color:var(--muted); font-size:.72rem; font-weight:800; padding-top:3rem; }
.governance-pipeline { display:grid; grid-template-columns:1fr auto 1fr auto 1fr;
                       align-items:center; gap:.65rem; margin:1.1rem 0 .5rem; }
.governance-pipeline div { background:#fff; border:1px solid var(--line); border-radius:7px; padding:.75rem; }
.governance-pipeline span { display:block; color:var(--indigo); font-size:.65rem; font-weight:800; letter-spacing:.07em; }
.governance-pipeline strong { color:var(--navy); font-size:.78rem; }
.governance-pipeline>b { color:#8b95a6; }
.invariant-line { color:var(--muted); text-align:center; font-size:.72rem; margin-bottom:1.2rem; }
.timeline { position:relative; margin-left:.35rem; }
.timeline-item { display:grid; grid-template-columns:76px 190px 1fr; gap:.8rem; position:relative;
                 padding:.72rem 0 .72rem 1.15rem; border-left:2px solid #d7dce5; }
.timeline-item:before { content:''; position:absolute; width:9px; height:9px; border-radius:50%;
                        background:#5968dd; left:-5.5px; top:1rem; box-shadow:0 0 0 3px #eef0ff; }
.timeline-time { color:var(--muted); font-variant-numeric:tabular-nums; font-size:.76rem; }
.timeline-title { color:var(--navy); font-weight:750; font-size:.84rem; }
.timeline-summary { color:var(--muted); font-size:.79rem; }
.tone-dot-danger:before { background:#c43d32; box-shadow:0 0 0 3px #fff0ee; }
.tone-dot-success:before { background:#15905a; box-shadow:0 0 0 3px #eaf7f0; }
.health-row { display:flex; justify-content:space-between; font-size:.72rem; padding:.25rem 0; }
.health-row span:last-child { color:#7ee2ae !important; font-weight:700; }
.overview-hero { display:grid; grid-template-columns:1.45fr .75fr; gap:1.5rem; align-items:end;
                 background:linear-gradient(135deg,#172033 0%,#202b4d 100%); border-radius:11px;
                 padding:1.65rem 1.8rem; margin:.45rem 0 .8rem; }
.overview-hero h1 { color:#fff; font-size:2.45rem !important; max-width:720px; margin:0 0 .5rem !important; }
.overview-hero p { color:#cbd3e2; margin:0; max-width:700px; font-size:.95rem; }
.hero-proof { border-left:1px solid #45506c; padding-left:1.25rem; }
.hero-proof span,.inspection-banner span { display:block; color:#aeb8ff; font-size:.64rem; font-weight:800; letter-spacing:.1em; }
.hero-proof strong { display:block; color:#f5f7fb; font-size:.82rem; margin-top:.45rem; line-height:1.45; }
.architecture-strip { display:flex; align-items:center; justify-content:center; flex-wrap:wrap; gap:.55rem;
                      background:#fff; border:1px solid var(--line); border-radius:8px; padding:.65rem 1rem; }
.architecture-strip b { color:#344054; font-size:.68rem; }
.architecture-strip i { color:#8e98aa; font-style:normal; }
.source-heading { display:flex; justify-content:space-between; align-items:end; gap:1.5rem; margin:2rem 0 .7rem; }
.source-heading h2 { margin:.35rem 0 0 !important; font-size:1.45rem !important; }
.source-heading p { color:var(--muted); max-width:470px; text-align:right; margin:0; font-size:.76rem; }
.source-heading.benchmark { border-top:1px solid var(--line); padding-top:1.6rem; }
.source-pill { display:inline-block; padding:.22rem .48rem; border-radius:4px; font-size:.62rem; font-weight:850; letter-spacing:.09em; }
.source-pill.live { color:#3157a4; background:#edf3ff; }
.source-pill.benchmark { color:#6a3bb1; background:#f4edff; }
.benchmark-thesis { display:flex; align-items:center; gap:1.2rem; background:#edf9f3; border:1px solid #bce7d0;
                    border-radius:8px; padding:.85rem 1rem; margin:.4rem 0 1rem; }
.benchmark-thesis strong { color:#087443; white-space:nowrap; }
.benchmark-thesis span { color:#3f5960; font-size:.8rem; }
.comparison-chart,.distribution-card { background:#fff; border:1px solid var(--line); border-radius:9px; padding:1rem 1.05rem; min-height:188px; }
.chart-title { color:var(--navy); font-weight:800; font-size:.9rem; }
.chart-subtitle { color:var(--muted); font-size:.7rem; margin:.15rem 0 .85rem; }
.chart-row { display:grid; grid-template-columns:108px 1fr 64px; gap:.55rem; align-items:center; margin:.7rem 0; }
.chart-label { color:#556070; font-size:.67rem; line-height:1.15; }
.chart-value { color:var(--navy); text-align:right; font-weight:800; font-size:.72rem; }
.bar-track { height:8px; background:#edf0f4; border-radius:99px; overflow:hidden; }
.bar-fill { height:100%; border-radius:99px; background:#4656d8; }
.bar-fill.muted { background:#aab2c0; } .bar-fill.primary { background:#4656d8; }
.bar-fill.success { background:#15905a; } .bar-fill.danger { background:#d65b50; }
.strategy-card { background:#fff; border:1px solid var(--line); border-radius:8px; padding:1rem 1.1rem; margin-top:1rem; min-height:105px; }
.strategy-card.governed { border-color:#adb5ff; box-shadow:inset 3px 0 #4656d8; }
.strategy-card span { display:block; color:var(--muted); font-size:.63rem; font-weight:850; letter-spacing:.09em; margin-bottom:.45rem; }
.strategy-card strong { color:var(--navy); line-height:1.4; }
.section-spacer { height:.75rem; }
.ops-proof { display:flex; justify-content:space-between; gap:1.5rem; background:#eef0ff; border:1px solid #cfd4ff;
             border-radius:8px; padding:.75rem 1rem; margin:.85rem 0 1rem; }
.ops-proof strong { color:#2937ad; font-size:.8rem; }
.ops-proof span { color:#596477; font-size:.76rem; text-align:right; }
.distribution-card { min-height:150px; margin-top:1.2rem; }
.distribution-row { display:grid; grid-template-columns:145px 1fr 28px; align-items:center; gap:.65rem; margin:.65rem 0; }
.distribution-row span { color:#556070; font-size:.7rem; }
.distribution-row strong { color:var(--navy); font-size:.72rem; text-align:right; }
.case-inspector,.inspection-banner { display:grid; grid-template-columns:repeat(5,1fr); gap:1rem; background:#fff;
                                    border:1px solid var(--line); border-radius:8px; padding:1rem 1.1rem; }
.case-inspector div,.inspection-banner div { min-width:0; }
.case-inspector span { display:block; color:var(--muted); font-size:.62rem; font-weight:800; letter-spacing:.08em; margin-bottom:.35rem; }
.case-inspector strong,.inspection-banner strong { color:var(--navy); font-size:.78rem; overflow-wrap:anywhere; }
.inspection-banner { grid-template-columns:1.4fr repeat(3,1fr); margin:.85rem 0 .35rem; }
.inspection-banner span { color:#5b67c9; margin-bottom:.35rem; }
.economics-hero,.system-hero { display:grid; grid-template-columns:1.5fr .65fr; gap:1.5rem; align-items:end;
                               background:linear-gradient(135deg,#172033 0%,#252f55 100%); border-radius:11px;
                               padding:1.65rem 1.8rem; margin:.45rem 0 .9rem; }
.economics-hero h1,.system-hero h1 { color:#fff; font-size:2.25rem !important; max-width:760px; margin:.35rem 0 .55rem !important; }
.economics-hero p,.system-hero p { color:#cbd3e2; max-width:760px; margin:0; font-size:.9rem; }
.economics-hero>div>span,.system-hero>div>span { color:#aeb8ff; font-size:.64rem; font-weight:850; letter-spacing:.1em; }
.evaluation-boundary,.system-invariant { border-left:1px solid #4d5875; padding-left:1.2rem; }
.evaluation-boundary strong,.system-invariant strong { display:block; color:#f5bd68; font-size:.65rem; letter-spacing:.09em; margin-bottom:.45rem; }
.evaluation-boundary span,.system-invariant span { color:#f4f6fb; font-size:.76rem; line-height:1.5; }
.economic-result { display:grid; grid-template-columns:1fr auto 1fr; gap:.85rem; align-items:stretch; margin:1.15rem 0 .75rem; }
.economic-result>div { display:flex; flex-direction:column; background:#fff; border:1px solid var(--line); border-radius:9px; padding:1rem 1.15rem; }
.economic-result>div.governed { border-color:#aeb6ff; box-shadow:inset 4px 0 #4656d8; }
.economic-result span { color:var(--muted); font-size:.63rem; font-weight:850; letter-spacing:.09em; }
.economic-result strong { color:var(--navy); font-size:1.4rem; margin:.35rem 0; }
.economic-result small { color:var(--muted); line-height:1.55; }
.economic-result>b { align-self:center; color:#8a94a5; font-size:.62rem; letter-spacing:.08em; }
.mode-card { background:#fff; border:1px solid var(--line); border-radius:9px; padding:1rem 1.05rem; min-height:190px; }
.mode-card>span,.model-spec>span,.action-space>span { display:block; color:var(--indigo); font-size:.63rem; font-weight:850; letter-spacing:.09em; }
.mode-card>strong,.model-spec>strong { display:block; color:var(--navy); font-size:1.15rem; margin:.38rem 0; }
.mode-card p { color:var(--muted); font-size:.76rem; min-height:42px; }
.mode-card>div { border-top:1px solid #edf0f4; color:#596477; font-size:.73rem; line-height:1.8; padding-top:.55rem; }
.mode-card b { color:var(--navy); }
.baseline-note { display:grid; grid-template-columns:190px 1fr; gap:1rem; background:#eef0ff; border:1px solid #cfd4ff;
                 border-radius:8px; padding:.85rem 1rem; margin:1.1rem 0; }
.baseline-note strong { color:#2937ad; }
.baseline-note span { color:#566174; font-size:.78rem; }
.system-pipeline { display:flex; flex-direction:column; gap:.6rem; background:#fff; border:1px solid var(--line); border-radius:10px; padding:1rem 1.1rem; }
.system-pipeline section { display:grid; grid-template-columns:72px 1fr; gap:.8rem; align-items:center; }
.system-pipeline section>b { color:var(--muted); font-size:.64rem; letter-spacing:.08em; text-transform:uppercase; }
.system-pipeline main { display:grid; grid-template-columns:1fr auto 1fr auto 1fr auto 1fr; align-items:center; gap:.5rem; }
.system-pipeline main div { background:#f8f9fb; border:1px solid #e4e7ec; border-radius:7px; padding:.65rem .7rem; min-height:62px; }
.system-pipeline main span { display:block; color:var(--indigo); font-size:.58rem; font-weight:850; }
.system-pipeline main strong { color:var(--navy); font-size:.72rem; }
.system-pipeline main i { color:#8b95a6; font-style:normal; }
.compact-heading { font-size:1.25rem !important; margin:1.5rem 0 .65rem !important; }
.authority-card { background:#fff; border:1px solid var(--line); border-radius:9px; padding:1rem 1.05rem; min-height:176px; }
.authority-card span { color:var(--indigo); font-size:.62rem; font-weight:850; letter-spacing:.08em; }
.authority-card strong { display:block; color:var(--navy); margin:.45rem 0; }
.authority-card p,.guarantee-card p { color:var(--muted); font-size:.76rem; line-height:1.5; margin:.25rem 0 0; }
.model-spec,.action-space { background:#fff; border:1px solid var(--line); border-radius:9px; padding:1rem 1.1rem; min-height:224px; }
.model-spec dl { display:grid; grid-template-columns:72px 1fr; gap:.45rem .7rem; margin:.8rem 0 0; font-size:.72rem; }
.model-spec dt { color:var(--muted); } .model-spec dd { color:var(--navy); font-weight:700; margin:0; overflow-wrap:anywhere; }
.action-space>div { display:flex; flex-wrap:wrap; gap:.5rem; margin:.8rem 0 1rem; }
.action-space>div span,.stack-card span { color:#344054; background:#f1f3f7; border:1px solid #dfe3e9; border-radius:5px; padding:.35rem .52rem; font-size:.68rem; font-weight:750; }
.action-space p { color:var(--muted); font-size:.76rem; border-top:1px solid #edf0f4; padding-top:.8rem; }
.action-space p b { color:#8a4b08; }
.guarantee-grid { display:grid; grid-template-columns:repeat(3,1fr); gap:.7rem; }
.guarantee-card { background:#fff; border:1px solid var(--line); border-top:3px solid #aab2c0; border-radius:8px; padding:.85rem .95rem; min-height:140px; }
.guarantee-card.success { border-top-color:#15905a; } .guarantee-card.info { border-top-color:#4656d8; } .guarantee-card.warning { border-top-color:#d89228; }
.guarantee-card>span { color:#9aa3b1; font-size:.58rem; font-weight:850; }
.guarantee-card>strong { display:block; color:var(--navy); font-size:.82rem; margin:.25rem 0; }
.stack-card { display:flex; flex-wrap:wrap; align-content:flex-start; gap:.55rem; background:#fff; border:1px solid var(--line); border-radius:9px; padding:1rem; min-height:152px; }
.quality-card { display:grid; grid-template-columns:1fr 1.45fr; gap:.75rem; background:#edf9f3; border:1px solid #bce7d0; border-radius:9px; padding:1rem; min-height:152px; }
.quality-card>div { display:flex; flex-direction:column; }
.quality-card strong { color:#087443; font-size:1.75rem; }
.quality-card span { color:#3f5960; font-size:.68rem; }
.quality-card p { grid-column:1/-1; color:#52636a; font-size:.72rem; margin:.2rem 0 0; }
.limitations-grid { display:grid; grid-template-columns:repeat(2,1fr); gap:.7rem; }
.limitations-grid>div { background:#fff; border:1px solid var(--line); border-radius:8px; padding:.85rem 1rem; }
.limitations-grid strong { display:block; color:var(--navy); font-size:.8rem; margin-bottom:.3rem; }
.limitations-grid span { color:var(--muted); font-size:.74rem; }
div.stButton > button { border-radius:7px; font-weight:750; border:1px solid #4656d8; }
div.stButton > button[kind="primary"] { background:#4050ce; }
@media (max-width:800px) {
  .demo-banner,.order-strip,.overview-hero,.economics-hero,.system-hero,.economic-result,.baseline-note,.case-inspector,.inspection-banner { grid-template-columns:1fr; }
  .demo-detail { border-left:0; border-top:1px solid #cfd4ff; padding:.7rem 0 0; }
  .governance-pipeline { grid-template-columns:1fr; }
  .governance-pipeline>b { text-align:center; transform:rotate(90deg); }
  .timeline-item { grid-template-columns:64px 1fr; }
  .timeline-summary { grid-column:2; }
  .source-heading,.benchmark-thesis,.ops-proof { align-items:flex-start; flex-direction:column; }
  .source-heading p,.ops-proof span { text-align:left; }
  .chart-row { grid-template-columns:92px 1fr 60px; }
  .economic-result>b { padding:.2rem; }
  .system-pipeline section { grid-template-columns:1fr; }
  .system-pipeline main { grid-template-columns:1fr; }
  .system-pipeline main i { text-align:center; transform:rotate(90deg); }
  .guarantee-grid,.limitations-grid { grid-template-columns:1fr; }
}
</style>
"""


def apply_theme():
    st.markdown(THEME_CSS, unsafe_allow_html=True)
