"""Infrastructure Debt deal — SPV + offtake + year-by-year CFADS + DSCR + S2 QII."""

from __future__ import annotations

import plotly.express as px
import streamlit as st

from src.calculations.project_finance import compute_infra_metrics
from src.calculations.s2_capital import return_on_capital_s2, s2_shock_effective
from src.calculations.verdict_engine import verdict_infra
from src.models.infra_deal import InfraDeal
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

st.set_page_config(page_title="Capital Lens — Infrastructure Debt", layout="wide")
inject_css()
st.title("Infrastructure Debt Deal")

alm = render_alm_banner()

infra_deals = [d for d in load_preset_deals() if d.type == "INFRA"]
preset_id = st.selectbox(
    "Preset deal", options=[d.id for d in infra_deals],
    format_func=lambda x: get_deal_by_id(x).label,
)
preset: InfraDeal = get_deal_by_id(preset_id)

col_in, col_ratios, col_stress, col_s2 = st.columns([1.2, 1, 1, 1])

with col_in:
    section_head("Inputs")
    project_name = st.text_input("Project name", value=preset.spv.project_name)
    sectors = ["Renewable solar", "Renewable wind onshore", "Renewable wind offshore",
               "Renewable hydro", "Data center", "Transport", "Social", "Utility"]
    sector = st.selectbox("Sector", sectors, index=sectors.index(preset.spv.sector))
    country = st.text_input("Country (ISO-2)", value=preset.spv.country, max_chars=2)
    sponsor = st.text_input("Sponsor", value=preset.spv.sponsor)
    currency = st.selectbox(
        "Currency", ["EUR", "USD", "GBP"], index=["EUR", "USD", "GBP"].index(preset.currency)
    )

    st.markdown('<div class="section-head">Offtake</div>', unsafe_allow_html=True)
    offtake_choices = ["PPA fix", "PPA indexed", "CfD", "Take-or-pay", "Availability payment", "Merchant"]
    offtake_type = st.selectbox("Offtake type", offtake_choices, index=offtake_choices.index(preset.offtake.offtake_type))
    strike = st.number_input("Strike price / unit revenue", value=float(preset.offtake.strike_price_eur_mwh), min_value=0.0)
    indexation = st.selectbox(
        "Indexation", ["Fixed", "CPI", "Formula"],
        index=["Fixed", "CPI", "Formula"].index(preset.offtake.indexation),
    )
    cpi = st.number_input("CPI / escalator (%)", value=float(preset.offtake.cpi_pct), min_value=0.0, step=0.25)
    contract_dur = st.number_input("Contract duration (y)", value=float(preset.offtake.contract_duration_years), min_value=1.0)
    capacity = st.number_input("Capacity (MW)", value=float(preset.offtake.capacity_mw), min_value=0.0, step=10.0)
    cap_factor = st.number_input(
        "Capacity factor (%)", value=float(preset.offtake.capacity_factor), min_value=0.0, max_value=100.0, step=1.0
    )

    st.markdown('<div class="section-head">Project</div>', unsafe_allow_html=True)
    capex = st.number_input("Capex total (M)", value=float(preset.project.capex_total_eur_m), min_value=1.0, step=50.0)
    opex = st.number_input("Opex annual (M/y)", value=float(preset.project.opex_annual_eur_m), min_value=0.0, step=1.0)
    hm_freq = st.number_input("Heavy maint frequency (y)", value=int(preset.project.heavy_maint_frequency_years), min_value=0)
    hm_amount = st.number_input("Heavy maint amount (M)", value=float(preset.project.heavy_maint_amount_eur_m), min_value=0.0)
    cod = st.number_input("COD year", value=int(preset.project.cod_year), min_value=2000)
    plife = st.number_input("Project life (y)", value=int(preset.project.project_life_years), min_value=5)

    st.markdown('<div class="section-head">Debt</div>', unsafe_allow_html=True)
    debt_amount = st.number_input("Debt amount (M)", value=float(preset.debt.debt_amount_eur_m), min_value=1.0, step=50.0)
    debt_maturity = st.number_input("Debt maturity (y)", value=int(preset.debt.debt_maturity_years), min_value=1)
    debt_profile = st.selectbox(
        "Debt profile", ["Amortizing sculpté", "Bullet"],
        index=["Amortizing sculpté", "Bullet"].index(preset.debt.debt_profile),
    )
    debt_base = st.selectbox(
        "Debt base rate", ["EURIBOR 3M", "SOFR 3M", "SONIA", "ESTR"],
        index=["EURIBOR 3M", "SOFR 3M", "SONIA", "ESTR"].index(preset.debt.debt_base_rate_type),
    )
    debt_rate = st.number_input("Debt base rate level (%)", value=float(preset.debt.debt_base_rate_level), min_value=0.0, step=0.05)
    debt_margin = st.number_input("Debt margin (bps)", value=float(preset.debt.debt_margin_bps), min_value=0.0, step=25.0)
    dsra = st.number_input("DSRA (months)", value=float(preset.debt.dsra_months), min_value=0.0)

    st.markdown('<div class="section-head">Risk</div>', unsafe_allow_html=True)
    ratings = ["AAA", "AA", "A", "BBB+", "BBB", "BBB-", "BB+", "BB", "BB-", "B+", "B", "B-", "CCC"]
    rating = st.selectbox(
        "Rating estimation", ratings,
        index=ratings.index(preset.risk.rating_estim) if preset.risk.rating_estim in ratings else 4,
    )
    pd_annual = st.number_input("PD annual (%)", value=float(preset.risk.pd_annual), min_value=0.0, step=0.05)
    lgd = st.number_input("LGD (%)", value=float(preset.risk.lgd), min_value=0.0, max_value=100.0, step=5.0)
    qii_eligible = st.checkbox("QII eligible", value=preset.risk.qii_eligible)
    qii_reduction = st.number_input(
        "QII spread reduction (%)", value=float(preset.risk.qii_spread_reduction),
        min_value=0.0, max_value=100.0, step=5.0,
    )

m = compute_infra_metrics(
    capacity_mw=capacity,
    capacity_factor_pct=cap_factor,
    offtake_type=offtake_type,
    strike_price=strike,
    indexation=indexation,
    cpi_pct=cpi,
    opex_annual=opex,
    heavy_maint_frequency=int(hm_freq),
    heavy_maint_amount=hm_amount,
    capex_total=capex,
    project_life=int(plife),
    debt_amount=debt_amount,
    debt_maturity=int(debt_maturity),
    debt_profile=debt_profile,
    base_rate_level=debt_rate,
    margin_bps=debt_margin,
    pd_annual=pd_annual,
    lgd=lgd,
)
shock = s2_shock_effective(rating, debt_maturity, qii_eligible=qii_eligible, qii_reduction_pct=qii_reduction)
roc = return_on_capital_s2(m.yield_net_pct, shock)
v = verdict_infra(m, roc, debt_maturity, alm)

with col_ratios:
    section_head("Project finance")
    st.markdown("".join([
        kpi_row("Min DSCR", safe_fmt(m.min_dscr, "{:.2f}×")),
        kpi_row("Avg DSCR", safe_fmt(m.avg_dscr, "{:.2f}×")),
        kpi_row("LLCR", safe_fmt(m.llcr, "{:.2f}×")),
        kpi_row("PLCR", safe_fmt(m.plcr, "{:.2f}×")),
        kpi_row("Tail", f"{m.tail_years:.0f}y"),
        kpi_row("All-in yield", f"{m.all_in_yield_pct:.2f}%"),
    ]), unsafe_allow_html=True)

with col_stress:
    section_head("Stress tests")
    st.markdown("".join([
        kpi_row("Base", safe_fmt(m.min_dscr, "{:.2f}×")),
        kpi_row("P90 (production −15%)", safe_fmt(m.min_dscr_p90, "{:.2f}×")),
    ]), unsafe_allow_html=True)
    if offtake_type == "Merchant":
        st.markdown(kpi_row("Merchant −25%", safe_fmt(m.min_dscr_merch, "{:.2f}×")), unsafe_allow_html=True)
    else:
        st.markdown(
            '<div style="font-size:0.72rem;color:var(--ink-mute);margin:8px 0 4px;letter-spacing:0.04em">Merchant stress n/a — offtake not merchant.</div>',
            unsafe_allow_html=True,
        )
    st.markdown(kpi_row("Combined", safe_fmt(m.min_dscr_combined, "{:.2f}×")), unsafe_allow_html=True)

with col_s2:
    section_head("Solvency II")
    rows = [kpi_row("Spread shock — Art 176(3)", f"{shock:.1f}%")]
    if qii_eligible:
        rows.append(kpi_row("QII reduction applied", f"−{qii_reduction:.0f}%"))
    rows.extend([
        kpi_row("Expected loss", f"{m.el_annual_pct:.3f}%"),
        kpi_row("Yield net of EL", f"{m.yield_net_pct:.2f}%"),
        kpi_row("Return on capital S2", f"{roc:.1f}%", best=True),
    ])
    st.markdown("".join(rows), unsafe_allow_html=True)

st.markdown("")
section_head("Cashflows year-by-year")
chart_df = m.cashflows.reset_index().rename(columns={"index": "year"})
chart_df["debt_service"] = chart_df["debt_principal"] + chart_df["debt_interest"]
fig = px.bar(
    chart_df,
    x="year",
    y=["cfads", "debt_service"],
    barmode="group",
    labels={"value": f"Cashflow ({currency} M)", "year": "Year (from COD)", "variable": ""},
    color_discrete_map={"cfads": "#003781", "debt_service": "#B68C1E"},
)
fig.update_layout(
    legend_title=None,
    height=360,
    margin=dict(t=10, b=10, l=10, r=10),
    plot_bgcolor="rgba(0,0,0,0)",
    paper_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Public Sans, sans-serif", size=12, color="#1a1a1a"),
    xaxis=dict(showgrid=False, zeroline=False),
    yaxis=dict(gridcolor="rgba(0,0,0,0.06)", zeroline=False),
)
st.plotly_chart(fig, width="stretch")

with st.expander("Year-by-year detail (CFADS + debt service)"):
    st.dataframe(
        m.cashflows[["revenue", "opex", "heavy_maint", "tax", "cfads",
                     "debt_principal", "debt_interest", "debt_service", "dscr"]]
        .style.format("{:.2f}"),
        width="stretch",
    )

st.markdown("")
section_head("Verdict — 3 pillars")
st.markdown(
    pillar_line("Credit", v.credit.status, v.credit.reason or "Min DSCR and LLCR within bounds.")
    + pillar_line("Solvency II", v.s2.status, v.s2.reason or "RoC S2 above 35% threshold.")
    + pillar_line("ALM Mandate Fit", v.alm.status, v.alm.reason or "Duration and liquidity within mandate."),
    unsafe_allow_html=True,
)
st.markdown(
    f'<div style="margin-top:16px;font-size:0.7rem;letter-spacing:0.18em;text-transform:uppercase;color:var(--ink-soft)">Final&nbsp;&nbsp; {verdict_pill_html(v.final)}</div>',
    unsafe_allow_html=True,
)

st.session_state["infra_state"] = {
    "label": f"Deal {preset_id.split('_')[1].upper()} — {sector} — {project_name}",
    "preset_id": preset_id,
    "currency": currency,
    "inputs": {
        "project_name": project_name, "sector": sector, "country": country, "sponsor": sponsor,
        "offtake_type": offtake_type, "strike": strike, "indexation": indexation, "cpi": cpi,
        "contract_dur": contract_dur, "capacity": capacity, "cap_factor": cap_factor,
        "capex": capex, "opex": opex, "hm_freq": int(hm_freq), "hm_amount": hm_amount,
        "cod": int(cod), "plife": int(plife),
        "debt_amount": debt_amount, "debt_maturity": int(debt_maturity), "debt_profile": debt_profile,
        "debt_rate": debt_rate, "debt_margin": debt_margin, "dsra": dsra,
        "rating": rating, "pd_annual": pd_annual, "lgd": lgd,
        "qii_eligible": qii_eligible, "qii_reduction": qii_reduction,
    },
    "metrics_simple": {
        "min_dscr": m.min_dscr, "avg_dscr": m.avg_dscr, "llcr": m.llcr, "plcr": m.plcr,
        "tail_years": m.tail_years, "all_in_yield_pct": m.all_in_yield_pct,
        "el_annual_pct": m.el_annual_pct, "yield_net_pct": m.yield_net_pct,
        "min_dscr_p90": m.min_dscr_p90, "min_dscr_merch": m.min_dscr_merch,
        "min_dscr_combined": m.min_dscr_combined,
    },
    "cashflows": m.cashflows.reset_index().to_dict(orient="list"),
    "shock_s2": shock,
    "roc_s2": roc,
    "verdict": v.model_dump(),
}

render_footer()
