"""AIM Capital Lens — entry point (Home).

Cross-class private debt comparator for Allianz Vie balance sheet.
Direct Lending × Infra Debt × Solvency II return on capital.
"""

from __future__ import annotations

import streamlit as st

from src.utils.presets_loader import load_preset_deals
from src.utils.ui_common import inject_css, render_alm_banner, render_footer

st.set_page_config(
    page_title="AIM Capital Lens",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

inject_css()

st.title("AIM Capital Lens")
st.markdown(
    "*Cross-class private debt comparator for Allianz Vie balance sheet — "
    "DL × Infra Debt × Solvency II return on capital*"
)

render_alm_banner()

st.markdown(
    """
    Welcome. This tool compares **Direct Lending** and **Infrastructure Debt** deals
    on a unified metric set (credit ratios, project-finance DSCR/LLCR/PLCR, and
    Solvency II return on capital under Article 176(3) + QII regime),
    against the mandate constraints set by the Risk & ALM Committee.

    Use the sidebar to navigate to each deal page, the side-by-side comparator,
    or the exports panel (Excel + PowerPoint).
    """
)

st.subheader("Preloaded deals")

deals = load_preset_deals()
cols = st.columns(3)
for col, deal in zip(cols, deals):
    with col:
        st.markdown(f"#### {deal.label}")
        st.caption(f"Type: {deal.type} · Currency: {deal.currency} · ID: `{deal.id}`")
        if deal.type == "DL":
            st.markdown(
                f"- Borrower: **{deal.borrower.name}** ({deal.borrower.sector})\n"
                f"- EBITDA: {deal.borrower.ebitda:.0f}M · "
                f"Margin {deal.borrower.ebitda_margin:.0f}%\n"
                f"- Loan: {deal.loan.loan_amount:.0f}M {deal.loan.tranche_type}\n"
                f"- Pricing: {deal.loan.base_rate_type} + {deal.loan.margin_bps:.0f} bps\n"
                f"- Tenor: {deal.loan.maturity_years:.0f}y {deal.loan.profile}\n"
                f"- Rating: {deal.risk.rating_estim}"
            )
        else:
            st.markdown(
                f"- Project: **{deal.spv.project_name}** ({deal.spv.sector})\n"
                f"- Offtake: {deal.offtake.offtake_type} · "
                f"{deal.offtake.contract_duration_years:.0f}y\n"
                f"- Capacity: {deal.offtake.capacity_mw:.0f} MW · "
                f"CF {deal.offtake.capacity_factor:.0f}%\n"
                f"- Debt: {deal.debt.debt_amount_eur_m:.0f}M · "
                f"{deal.debt.debt_maturity_years:.0f}y {deal.debt.debt_profile}\n"
                f"- Rating: {deal.risk.rating_estim} "
                f"({'QII ' + str(int(deal.risk.qii_spread_reduction)) + '%' if deal.risk.qii_eligible else 'non-QII'})"
            )

st.markdown("---")
st.markdown(
    """
    ##### Methodology highlights
    - **Solvency II spread shock** — Article 176(3) Règlement délégué (UE) 2015/35,
      Milliman 2019 calibration. Linear interpolation between maturity buckets.
    - **QII regime** — Articles 164a (infrastructure corporates) / 164b (infrastructure
      project entities) — spread shock reduction applied to qualifying infrastructure.
    - **Verdict 3-piliers** — Credit · S2 · ALM Mandate Fit. The tool flags where the
      operational analyst's call (credit + S2) sits, and where the ALM Committee's
      constraints (duration / liquidity / S2 ratio target) take over.
    """
)

render_footer()
