"""AIM Capital Lens — Home.

Pick a template to start analyzing a private debt deal. The chosen template is
written to st.session_state and the user lands on the Analyzer page.
"""

from __future__ import annotations

import streamlit as st

from src.utils.ui_common import inject_css, render_alm_banner, render_footer, section_head

st.set_page_config(
    page_title="AIM Capital Lens",
    layout="wide",
    initial_sidebar_state="expanded",
)

inject_css()

st.title("AIM Capital Lens")
st.markdown(
    "*Single-deal credit analyzer for Allianz Vie balance sheet — "
    "Direct Lending and Infrastructure Debt, with Solvency II capital lens.*"
)

render_alm_banner()

st.markdown(
    """
    Pick a template below to load typical inputs for a deal type, then refine
    the numbers on the Analyzer page. The analysis reads the metrics in plain
    English (verdict, three pillars, narrative interpretation) so you can
    focus on the call rather than on the dashboard.
    """
)

section_head("Templates")

TEMPLATES = [
    {
        "id": "deal_a_dl_saas",
        "kicker": "Direct Lending",
        "name": "Unitranche LBO — SaaS / TMT",
        "body": (
            "Sponsor-backed unitranche, EBITDA-positive scale-up borrower. "
            "EURIBOR + 600–700 bps area, 7-year bullet, covenant package. "
            "Calibrated to a B+ rated profile."
        ),
    },
    {
        "id": "deal_b_infra_offshore",
        "kicker": "Infrastructure Debt",
        "name": "Renewable — offshore wind (CfD)",
        "body": (
            "Long-dated project finance debt, sculpted amortisation, "
            "UK-style CfD with CPI indexation. BBB rating, QII regime "
            "applied at the standard reduction."
        ),
    },
    {
        "id": "deal_c_infra_datacenter",
        "kicker": "Infrastructure Debt",
        "name": "Data center — hyperscale take-or-pay",
        "body": (
            "Hyperscaler-backed take-or-pay contract with escalator, "
            "amortising debt across 15 years. BBB- rating, QII applied."
        ),
    },
    {
        "id": "deal_custom_dl",
        "kicker": "Custom",
        "name": "Blank Direct Lending deal",
        "body": (
            "Start from a generic mid-cap unitranche stub and fill in the "
            "borrower, loan, and risk inputs yourself."
        ),
    },
]

cols = st.columns(2)
for idx, tpl in enumerate(TEMPLATES):
    with cols[idx % 2]:
        st.markdown(
            f"""
            <div class="deal-card">
                <div class="deal-meta">{tpl['kicker']}</div>
                <h4>{tpl['name']}</h4>
                <p style="color:var(--ink-soft); font-size:0.92rem; line-height:1.55;">
                    {tpl['body']}
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button("Open in analyzer", key=f"open_{tpl['id']}"):
            st.session_state["selected_template_id"] = tpl["id"]
            st.switch_page("pages/1_Analyzer.py")

section_head("Methodology")
st.markdown(
    """
    - **Solvency II spread shock** — Article 176(3) Règlement délégué (UE) 2015/35,
      Milliman 2019 calibration. Linear interpolation between maturity buckets.
    - **QII regime** — Articles 164a / 164b — spread shock reduction applied to
      qualifying infrastructure debt.
    - **3-pillar verdict** — Credit · Solvency II · ALM Mandate Fit. The tool
      flags where the operational analyst's call (credit + S2) sits, and where
      the ALM Committee's constraints (duration / liquidity / S2 ratio target)
      take over.
    """
)

render_footer()
