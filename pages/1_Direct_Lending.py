"""Direct Lending deal — editable inputs, live ratios, stress, S2."""

from __future__ import annotations

import streamlit as st

from src.calculations.dl_metrics import compute_dl_metrics
from src.calculations.s2_capital import return_on_capital_s2, s2_shock_effective
from src.calculations.verdict_engine import verdict_dl
from src.models.dl_deal import DLDeal
from src.utils.presets_loader import get_deal_by_id, load_preset_deals
from src.utils.ui_common import (
    inject_css,
    kpi_row,
    pillar_line,
    render_alm_banner,
    render_footer,
    safe_fmt,
    section_head,
    verdict_pill_html,
)

st.set_page_config(page_title="Capital Lens — Direct Lending", layout="wide")
inject_css()
st.title("Direct Lending Deal")

alm = render_alm_banner()

dl_deals = [d for d in load_preset_deals() if d.type == "DL"]
preset_ids = [d.id for d in dl_deals]
preset_id = st.selectbox(
    "Preset deal", options=preset_ids,
    format_func=lambda x: get_deal_by_id(x).label,
)
preset: DLDeal = get_deal_by_id(preset_id)

col_in, col_ratios, col_stress, col_s2 = st.columns([1.1, 1, 1, 1])

with col_in:
    section_head("Inputs")
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

    st.markdown('<div class="section-head">Loan</div>', unsafe_allow_html=True)
    loan_amount = st.number_input("Loan amount (M)", value=float(preset.loan.loan_amount), min_value=1.0, step=5.0)
    rcf_amount = st.number_input("RCF amount (M)", value=float(preset.loan.rcf_amount), min_value=0.0, step=5.0)
    tranche = st.selectbox(
        "Tranche", ["RCF", "1L Term Loan", "Unitranche", "2L", "Mezzanine"],
        index=["RCF", "1L Term Loan", "Unitranche", "2L", "Mezzanine"].index(preset.loan.tranche_type),
    )
    base_rate_type = st.selectbox(
        "Base rate", ["EURIBOR 3M", "SOFR 3M", "SONIA", "ESTR"],
        index=["EURIBOR 3M", "SOFR 3M", "SONIA", "ESTR"].index(preset.loan.base_rate_type),
    )
    base_rate_level = st.number_input("Base rate level (%)", value=float(preset.loan.base_rate_level), min_value=0.0, step=0.05)
    margin_bps = st.number_input("Margin (bps)", value=float(preset.loan.margin_bps), min_value=0.0, step=25.0)
    oid = st.number_input("OID (%)", value=float(preset.loan.oid_pct), min_value=0.0, step=0.1)
    upfront = st.number_input("Upfront fee (%)", value=float(preset.loan.upfront_pct), min_value=0.0, step=0.1)
    floor = st.number_input("Floor (%)", value=float(preset.loan.floor_pct), min_value=0.0, step=0.1)
    maturity = st.number_input("Maturity (years)", value=float(preset.loan.maturity_years), min_value=1.0, step=1.0)
    profile = st.selectbox(
        "Profile", ["Bullet", "Amortizing", "DDTL"],
        index=["Bullet", "Amortizing", "DDTL"].index(preset.loan.profile),
    )

    st.markdown('<div class="section-head">Covenants</div>', unsafe_allow_html=True)
    cov_lev = st.number_input("Covenant Net Lev cap (×)", value=float(preset.covenants.cov_net_lev_cap), min_value=0.5, step=0.25)
    cov_ic = st.number_input("Covenant IC min (×)", value=float(preset.covenants.cov_ic_min), min_value=0.5, step=0.05)
    cov_fccr = st.number_input("Covenant FCCR min (×)", value=float(preset.covenants.cov_fccr_min), min_value=0.5, step=0.05)
    cov_lite = st.checkbox("Cov-lite", value=preset.covenants.cov_lite)

    st.markdown('<div class="section-head">Risk</div>', unsafe_allow_html=True)
    rating_choices = ["AAA", "AA", "A", "BBB+", "BBB", "BBB-", "BB+", "BB", "BB-", "B+", "B", "B-", "CCC"]
    rating = st.selectbox(
        "Rating estimation", rating_choices,
        index=rating_choices.index(preset.risk.rating_estim) if preset.risk.rating_estim in rating_choices else 10,
    )
    pd_annual = st.number_input("PD annual (%)", value=float(preset.risk.pd_annual), min_value=0.0, step=0.1)
    lgd = st.number_input("LGD (%)", value=float(preset.risk.lgd), min_value=0.0, max_value=100.0, step=5.0)

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
    rows = [
        ("Net leverage", f"{m.net_leverage:.2f}×"),
        ("Interest coverage", safe_fmt(m.interest_coverage, "{:.2f}×")),
        ("FCCR", safe_fmt(m.fccr, "{:.2f}×")),
        ("Debt yield", f"{m.debt_yield:.1f}%"),
        ("All-in yield", f"{m.all_in_yield:.2f}%"),
        ("Covenant headroom", f"{m.headroom_net_lev*100:+.1f}%"),
    ]
    st.markdown("".join(kpi_row(lbl, val) for lbl, val in rows), unsafe_allow_html=True)

with col_stress:
    section_head("Stress tests")
    st.markdown(
        '<div style="font-size:0.72rem;color:var(--ink-soft);margin:8px 0 0;letter-spacing:0.14em;text-transform:uppercase">EBITDA &minus;20%</div>',
        unsafe_allow_html=True,
    )
    st.markdown("".join([
        kpi_row("Net lev stressed", f"{m.net_lev_stressed:.2f}×"),
        kpi_row("IC stressed", safe_fmt(m.ic_stressed, "{:.2f}×")),
        kpi_row("FCCR stressed", safe_fmt(m.fccr_stressed, "{:.2f}×")),
    ]), unsafe_allow_html=True)
    st.markdown(
        '<div style="font-size:0.72rem;color:var(--ink-soft);margin:14px 0 0;letter-spacing:0.14em;text-transform:uppercase">Base rate +200 bps</div>',
        unsafe_allow_html=True,
    )
    st.markdown(kpi_row("IC vs rate shock", safe_fmt(m.ic_rate_stressed, "{:.2f}×")), unsafe_allow_html=True)
    st.markdown(
        '<div style="font-size:0.72rem;color:var(--ink-soft);margin:14px 0 0;letter-spacing:0.14em;text-transform:uppercase">Combined</div>',
        unsafe_allow_html=True,
    )
    st.markdown("".join([
        kpi_row("IC combined", safe_fmt(m.ic_combined, "{:.2f}×")),
        kpi_row("FCCR combined", safe_fmt(m.fccr_combined, "{:.2f}×")),
    ]), unsafe_allow_html=True)

with col_s2:
    section_head("Solvency II")
    st.markdown("".join([
        kpi_row("Spread shock — Art 176(3)", f"{shock:.1f}%"),
        kpi_row("Expected loss (annual)", f"{m.el_annual:.2f}%"),
        kpi_row("Yield net of EL", f"{m.yield_net:.2f}%"),
        kpi_row("Return on capital S2", f"{roc:.1f}%", best=True),
    ]), unsafe_allow_html=True)

st.markdown("")
section_head("Verdict — 3 pillars")
st.markdown(
    pillar_line("Credit", v.credit.status, v.credit.reason or "All credit thresholds met.")
    + pillar_line("Solvency II", v.s2.status, v.s2.reason or "RoC S2 above 35% threshold.")
    + pillar_line("ALM Mandate Fit", v.alm.status, v.alm.reason or "Duration and liquidity within mandate."),
    unsafe_allow_html=True,
)
st.markdown(
    f'<div style="margin-top:16px;font-size:0.7rem;letter-spacing:0.18em;text-transform:uppercase;color:var(--ink-soft)">Final&nbsp;&nbsp; {verdict_pill_html(v.final)}</div>',
    unsafe_allow_html=True,
)

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
