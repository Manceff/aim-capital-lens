"""Page Deal Direct Lending — inputs éditables + ratios live + stress + S2."""

from __future__ import annotations

import streamlit as st

from src.calculations.dl_metrics import compute_dl_metrics
from src.calculations.s2_capital import return_on_capital_s2, s2_shock_effective
from src.calculations.verdict_engine import verdict_dl
from src.models.dl_deal import DLDeal
from src.utils.presets_loader import get_deal_by_id, load_preset_deals
from src.utils.ui_common import (
    inject_css,
    kpi_tile,
    render_alm_banner,
    render_footer,
    safe_fmt,
    section_head,
    verdict_badge_html,
)

st.set_page_config(page_title="Capital Lens — DL", page_icon="📊", layout="wide")
inject_css()
st.title("📊 Direct Lending Deal")

alm = render_alm_banner()

# Select base preset
dl_deals = [d for d in load_preset_deals() if d.type == "DL"]
preset_ids = [d.id for d in dl_deals]
preset_id = st.selectbox(
    "Preset deal", options=preset_ids,
    format_func=lambda x: get_deal_by_id(x).label,
)
preset: DLDeal = get_deal_by_id(preset_id)

# Layout: 4 columns
col_in, col_ratios, col_stress, col_s2 = st.columns([1.1, 1, 1, 1])

with col_in:
    section_head("Inputs (editable)")
    name = st.text_input("Borrower name", value=preset.borrower.name)
    sector = st.selectbox(
        "Sector",
        ["SaaS", "Healthcare", "Industrials", "Consumer", "TMT", "Other"],
        index=["SaaS", "Healthcare", "Industrials", "Consumer", "TMT", "Other"].index(
            preset.borrower.sector
        ),
    )
    currency = st.selectbox("Currency", ["EUR", "USD", "GBP"], index=["EUR", "USD", "GBP"].index(preset.currency))
    ebitda = st.number_input("EBITDA (M)", value=float(preset.borrower.ebitda), min_value=0.1, step=1.0)
    ebitda_growth = st.number_input("EBITDA growth (%/y)", value=float(preset.borrower.ebitda_growth), step=0.5)
    capex_maint = st.number_input(
        "Capex maintenance (M/y)", value=float(preset.borrower.capex_maintenance), min_value=0.0, step=0.5
    )
    fcf_conv = st.number_input(
        "FCF conversion (%)", value=float(preset.borrower.fcf_conversion), min_value=0.0, max_value=100.0, step=1.0
    )
    sponsor_tier = st.selectbox(
        "Sponsor tier", ["Top-tier", "Mid-tier", "New"],
        index=["Top-tier", "Mid-tier", "New"].index(preset.borrower.sponsor_tier),
    )

    st.divider()
    loan_amount = st.number_input(
        "Loan amount (M)", value=float(preset.loan.loan_amount), min_value=1.0, step=5.0
    )
    rcf_amount = st.number_input("RCF amount (M)", value=float(preset.loan.rcf_amount), min_value=0.0, step=5.0)
    tranche = st.selectbox(
        "Tranche", ["RCF", "1L Term Loan", "Unitranche", "2L", "Mezzanine"],
        index=["RCF", "1L Term Loan", "Unitranche", "2L", "Mezzanine"].index(preset.loan.tranche_type),
    )
    base_rate_type = st.selectbox(
        "Base rate", ["EURIBOR 3M", "SOFR 3M", "SONIA", "ESTR"],
        index=["EURIBOR 3M", "SOFR 3M", "SONIA", "ESTR"].index(preset.loan.base_rate_type),
    )
    base_rate_level = st.number_input(
        "Base rate level (%)", value=float(preset.loan.base_rate_level), min_value=0.0, step=0.05
    )
    margin_bps = st.number_input(
        "Margin (bps)", value=float(preset.loan.margin_bps), min_value=0.0, step=25.0
    )
    oid = st.number_input("OID (%)", value=float(preset.loan.oid_pct), min_value=0.0, step=0.1)
    upfront = st.number_input("Upfront fee (%)", value=float(preset.loan.upfront_pct), min_value=0.0, step=0.1)
    floor = st.number_input("Floor (%)", value=float(preset.loan.floor_pct), min_value=0.0, step=0.1)
    maturity = st.number_input(
        "Maturity (years)", value=float(preset.loan.maturity_years), min_value=1.0, step=1.0
    )
    profile = st.selectbox(
        "Profile", ["Bullet", "Amortizing", "DDTL"],
        index=["Bullet", "Amortizing", "DDTL"].index(preset.loan.profile),
    )

    st.divider()
    cov_lev = st.number_input(
        "Covenant Net Lev cap (×)", value=float(preset.covenants.cov_net_lev_cap), min_value=0.5, step=0.25
    )
    cov_ic = st.number_input(
        "Covenant IC min (×)", value=float(preset.covenants.cov_ic_min), min_value=0.5, step=0.05
    )
    cov_fccr = st.number_input(
        "Covenant FCCR min (×)", value=float(preset.covenants.cov_fccr_min), min_value=0.5, step=0.05
    )
    cov_lite = st.checkbox("Cov-lite", value=preset.covenants.cov_lite)

    st.divider()
    rating_choices = ["AAA", "AA", "A", "BBB+", "BBB", "BBB-", "BB+", "BB", "BB-", "B+", "B", "B-", "CCC"]
    rating = st.selectbox(
        "Rating estimation", rating_choices,
        index=rating_choices.index(preset.risk.rating_estim) if preset.risk.rating_estim in rating_choices else 10,
    )
    pd_annual = st.number_input("PD annual (%)", value=float(preset.risk.pd_annual), min_value=0.0, step=0.1)
    lgd = st.number_input("LGD (%)", value=float(preset.risk.lgd), min_value=0.0, max_value=100.0, step=5.0)

# Live compute
m = compute_dl_metrics(
    ebitda=ebitda,
    loan_amount=loan_amount,
    rcf_amount=rcf_amount,
    base_rate_level=base_rate_level,
    margin_bps=margin_bps,
    oid_pct=oid,
    upfront_pct=upfront,
    floor_pct=floor,
    maturity_years=maturity,
    profile=profile,
    capex_maintenance=capex_maint,
    fcf_conversion=fcf_conv,
    pd_annual=pd_annual,
    lgd=lgd,
    cov_net_lev_cap=cov_lev,
)
shock = s2_shock_effective(rating, maturity)
roc = return_on_capital_s2(m.yield_net, shock)
v = verdict_dl(m, roc, maturity, alm)

with col_ratios:
    section_head("Credit ratios")
    st.markdown(kpi_tile("Net leverage", f"{m.net_leverage:.2f}×"), unsafe_allow_html=True)
    st.markdown(kpi_tile("Interest coverage", safe_fmt(m.interest_coverage, "{:.2f}×")), unsafe_allow_html=True)
    st.markdown(kpi_tile("FCCR", safe_fmt(m.fccr, "{:.2f}×")), unsafe_allow_html=True)
    st.markdown(kpi_tile("Debt yield", f"{m.debt_yield:.1f}%"), unsafe_allow_html=True)
    st.markdown(kpi_tile("All-in yield", f"{m.all_in_yield:.2f}%"), unsafe_allow_html=True)
    st.markdown(kpi_tile("Covenant headroom", f"{m.headroom_net_lev*100:+.1f}%"), unsafe_allow_html=True)

with col_stress:
    section_head("Stress tests")
    st.markdown("**Stress 1 — EBITDA −20 %**")
    st.markdown(kpi_tile("Net lev stressed", f"{m.net_lev_stressed:.2f}×"), unsafe_allow_html=True)
    st.markdown(kpi_tile("IC stressed", safe_fmt(m.ic_stressed, "{:.2f}×")), unsafe_allow_html=True)
    st.markdown(kpi_tile("FCCR stressed", safe_fmt(m.fccr_stressed, "{:.2f}×")), unsafe_allow_html=True)
    st.markdown("**Stress 2 — base rate +200 bps**")
    st.markdown(kpi_tile("IC vs rate shock", safe_fmt(m.ic_rate_stressed, "{:.2f}×")), unsafe_allow_html=True)
    st.markdown("**Stress 3 — combined**")
    st.markdown(kpi_tile("IC combined", safe_fmt(m.ic_combined, "{:.2f}×")), unsafe_allow_html=True)
    st.markdown(kpi_tile("FCCR combined", safe_fmt(m.fccr_combined, "{:.2f}×")), unsafe_allow_html=True)

with col_s2:
    section_head("Solvency II")
    st.markdown(kpi_tile("Spread shock — Art 176(3)", f"{shock:.1f}%"), unsafe_allow_html=True)
    st.markdown(kpi_tile("Expected loss (annual)", f"{m.el_annual:.2f}%"), unsafe_allow_html=True)
    st.markdown(kpi_tile("Yield net of EL", f"{m.yield_net:.2f}%"), unsafe_allow_html=True)
    st.markdown(kpi_tile("Return on capital S2", f"{roc:.1f}%"), unsafe_allow_html=True)

st.divider()
section_head("Verdict — 3 pillars")
vcols = st.columns(4)
vcols[0].markdown(
    f"**Crédit** {verdict_badge_html(v.credit.status)}<br><small>{v.credit.reason or 'all credit thresholds met'}</small>",
    unsafe_allow_html=True,
)
vcols[1].markdown(
    f"**Solvency II** {verdict_badge_html(v.s2.status)}<br><small>{v.s2.reason or 'RoC S2 above 35% threshold'}</small>",
    unsafe_allow_html=True,
)
vcols[2].markdown(
    f"**ALM Mandate Fit** {verdict_badge_html(v.alm.status)}<br><small>{v.alm.reason or 'duration & liquidity within mandate'}</small>",
    unsafe_allow_html=True,
)
vcols[3].markdown(
    f"**Final** {verdict_badge_html(v.final)}",
    unsafe_allow_html=True,
)

# Cache metrics in session for comparator + exports
st.session_state["dl_state"] = {
    "label": f"Deal {preset_id.split('_')[1].upper()} — {sector} — {name}",
    "preset_id": preset_id,
    "currency": currency,
    "inputs": {
        "ebitda": ebitda, "loan_amount": loan_amount, "margin_bps": margin_bps,
        "base_rate_level": base_rate_level, "maturity_years": maturity, "profile": profile,
        "oid_pct": oid, "upfront_pct": upfront, "rating": rating,
        "pd_annual": pd_annual, "lgd": lgd, "cov_net_lev_cap": cov_lev,
        "sector": sector, "name": name, "tranche_type": tranche,
        "capex_maintenance": capex_maint, "fcf_conversion": fcf_conv,
    },
    "metrics": m.__dict__,
    "shock_s2": shock,
    "roc_s2": roc,
    "verdict": v.model_dump(),
}

render_footer()
