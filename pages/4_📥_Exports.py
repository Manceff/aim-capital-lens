"""Page Exports — boutons Excel + PowerPoint."""

from __future__ import annotations

import datetime as _dt

import streamlit as st

from src.exports.excel_builder import build_excel_report
from src.exports.pptx_builder import build_pptx_report
from src.utils.presets_loader import get_deal_by_id, load_preset_deals
from src.utils.ui_common import inject_css, render_alm_banner, render_footer, section_head

st.set_page_config(page_title="Capital Lens — Exports", page_icon="📥", layout="wide")
inject_css()
st.title("📥 Exports — Investment Committee package")

render_alm_banner()

st.markdown(
    """
    Generate the two artefacts you'd post on a real IC table:
    a **5-tab Excel model** with formulas exposed (auditable) and a **7-slide PowerPoint**
    in Allianz palette ready for the meeting.

    Pick the two deals to bundle (one DL + one Infra Debt), then click each button.
    """
)

deals = load_preset_deals()
dl_options = [d for d in deals if d.type == "DL"]
infra_options = [d for d in deals if d.type == "INFRA"]

col_a, col_b = st.columns(2)
with col_a:
    dl_id = st.selectbox(
        "Deal A — Direct Lending",
        options=[d.id for d in dl_options],
        format_func=lambda x: get_deal_by_id(x).label,
    )
with col_b:
    infra_id = st.selectbox(
        "Deal B — Infrastructure Debt",
        options=[d.id for d in infra_options],
        format_func=lambda x: get_deal_by_id(x).label,
    )

dl = get_deal_by_id(dl_id)
infra = get_deal_by_id(infra_id)

st.divider()
section_head("1. Excel model — 5 tabs")
st.markdown(
    """
    - **Tab 1 Inputs** — DL + Infra + ALM constraints (read-only)
    - **Tab 2 DL Calculations** — ratios + EL with Excel formulas visible (auditable)
    - **Tab 3 Infra Cashflows** — year-by-year CFADS + DSCR with conditional formatting
    - **Tab 4 Stress Tests** — 4 scenarios × 2 deals, colour-coded
    - **Tab 5 S2 + Comparator + Verdict** — Art 176(3) table + side-by-side + verdict 3 piliers
    """
)
xlsx_bytes = build_excel_report(dl=dl, infra=infra)
st.download_button(
    "⬇️  Download Excel model (.xlsx)",
    data=xlsx_bytes,
    file_name=f"aim_capital_lens_{_dt.date.today().isoformat()}.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
)

st.divider()
section_head("2. PowerPoint deck — 7 slides")
st.markdown(
    """
    1. **Cover** — title + author + disclaimer
    2. **Deal A executive summary** — 4 KPI tiles + verdict + 3 bullets
    3. **Deal B executive summary** — 4 KPI tiles + verdict + 3 bullets (QII flagged)
    4. **Side-by-side comparator** — 10-row table, RoC S2 row highlighted in gold
    5. **Stress test results** — 4 × 2 matrix with pass / tight / breach icons
    6. **S2 capital decomposition** — bar chart yield → EL → shock → RoC S2
    7. **Recommendation** — verdict 3 piliers + next-steps DD
    """
)
pptx_bytes = build_pptx_report(dl=dl, infra=infra)
st.download_button(
    "⬇️  Download IC slide deck (.pptx)",
    data=pptx_bytes,
    file_name=f"aim_capital_lens_{_dt.date.today().isoformat()}.pptx",
    mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
)

render_footer()
