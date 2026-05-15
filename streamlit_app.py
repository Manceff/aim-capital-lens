"""AIM Capital Lens — entry point (Home).

Cross-class private debt comparator for Allianz Vie balance sheet.
Direct Lending × Infra Debt × Solvency II return on capital.
"""

from __future__ import annotations

import streamlit as st

from src.utils.presets_loader import load_preset_deals
from src.utils.ui_common import inject_css, render_alm_banner, render_footer, section_head

st.set_page_config(
    page_title="AIM Capital Lens",
    layout="wide",
    initial_sidebar_state="expanded",
)

inject_css()

st.title("AIM Capital Lens")
st.markdown(
    "*Cross-class private debt comparator for Allianz Vie — "
    "Direct Lending × Infrastructure Debt × Solvency II return on capital.*"
)

render_alm_banner()

st.markdown(
    """
    A unified read on two private-debt opportunities: credit ratios on one side,
    project-finance coverage on the other, Solvency II capital intensity on both.
    The verdict layer makes the analyst's call (Credit · S2) explicit, and flags
    where the ALM mandate envelope — owned upstream by the Risk &amp; ALM Committee —
    binds.
    """
)

section_head("Preloaded deals")

deals = load_preset_deals()
cols = st.columns(3)
for col, deal in zip(cols, deals):
    with col:
        st.markdown(
            f'<div class="deal-card">'
            f'<div class="deal-meta">{deal.type} · {deal.currency} · {deal.id}</div>'
            f'<h4>{deal.label}</h4>'
            f'</div>',
            unsafe_allow_html=True,
        )
        if deal.type == "DL":
            st.markdown(
                f"- Borrower: **{deal.borrower.name}** ({deal.borrower.sector})  \n"
                f"- EBITDA {deal.borrower.ebitda:.0f}M · margin {deal.borrower.ebitda_margin:.0f}%  \n"
                f"- Loan {deal.loan.loan_amount:.0f}M {deal.loan.tranche_type}  \n"
                f"- {deal.loan.base_rate_type} + {deal.loan.margin_bps:.0f} bps  \n"
                f"- Tenor {deal.loan.maturity_years:.0f}y {deal.loan.profile}  \n"
                f"- Rating {deal.risk.rating_estim}"
            )
        else:
            qii = (
                f"QII −{int(deal.risk.qii_spread_reduction)}%"
                if deal.risk.qii_eligible
                else "non-QII"
            )
            st.markdown(
                f"- Project: **{deal.spv.project_name}** ({deal.spv.sector})  \n"
                f"- Offtake {deal.offtake.offtake_type} · {deal.offtake.contract_duration_years:.0f}y  \n"
                f"- Capacity {deal.offtake.capacity_mw:.0f} MW · CF {deal.offtake.capacity_factor:.0f}%  \n"
                f"- Debt {deal.debt.debt_amount_eur_m:.0f}M · {deal.debt.debt_maturity_years}y {deal.debt.debt_profile}  \n"
                f"- Rating {deal.risk.rating_estim} ({qii})"
            )

st.markdown("")
section_head("Methodology")
st.markdown(
    """
    - **Solvency II spread shock** — Article 176(3) Règlement délégué (UE) 2015/35,
      Milliman 2019 calibration. Linear interpolation between maturity buckets.
    - **QII regime** — Articles 164a / 164b — spread shock reduction applied to
      qualifying infrastructure debt.
    - **3-pillar verdict** — Credit · Solvency II · ALM Mandate Fit. The tool flags
      where the operational analyst's call (credit + S2) sits, and where the ALM
      Committee's constraints (duration / liquidity / S2 ratio target) take over.
    """
)

render_footer()
