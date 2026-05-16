"""Analyzer — single-deal credit analysis with narrative interpretation.

Form on the left (40%): seven essential fields + an Advanced expander.
Analysis on the right (60%): verdict, three pillars, narrative metrics,
stress summary, and Excel + PowerPoint downloads.
"""

from __future__ import annotations

import datetime as _dt

import streamlit as st

from src.analysis.narrative import (
    analyze_dl,
    analyze_infra,
    comment_alm,
    comment_s2,
)
from src.calculations.dl_metrics import compute_dl_metrics
from src.calculations.project_finance import compute_infra_metrics
from src.calculations.s2_capital import return_on_capital_s2, s2_shock_effective
from src.calculations.verdict_engine import verdict_dl, verdict_infra
from src.exports.excel_builder import build_excel_report
from src.exports.pptx_builder import build_pptx_report
from src.models.dl_deal import (
    DLBorrower, DLCovenants, DLDeal, DLLoan, DLRisk,
)
from src.models.infra_deal import (
    InfraDeal, InfraDebt, InfraOfftake, InfraProject, InfraRisk, InfraSPV,
)
from src.utils.presets_loader import get_deal_by_id, load_preset_deals
from src.utils.ui_common import (
    inject_css,
    pillar_line,
    render_alm_banner,
    render_footer,
    section_head,
    verdict_pill_html,
)

st.set_page_config(page_title="Capital Lens — Analyzer", layout="wide")
inject_css()

alm = render_alm_banner()

# --- Template selection ------------------------------------------------------
all_deals = load_preset_deals()
template_id = st.session_state.get("selected_template_id", all_deals[0].id)
if template_id not in [d.id for d in all_deals]:
    template_id = all_deals[0].id

with st.sidebar:
    st.markdown(
        '<div class="section-head" style="margin-top:0">Switch template</div>',
        unsafe_allow_html=True,
    )
    template_id = st.selectbox(
        "Template",
        options=[d.id for d in all_deals],
        index=[d.id for d in all_deals].index(template_id),
        format_func=lambda x: get_deal_by_id(x).label,
        label_visibility="collapsed",
    )
    st.session_state["selected_template_id"] = template_id

preset = get_deal_by_id(template_id)

st.title(f"Analysis — {preset.label}")
st.caption(f"Deal type: {preset.type} · Currency: {preset.currency} · Template id: {template_id}")

col_form, col_analysis = st.columns([2, 3])


# --- helpers ---------------------------------------------------------------
def _commentary_block(commentary_list):
    """Render a list of Commentary records as label · value · sentence rows."""
    items = []
    for c in commentary_list:
        tone_color = {
            "positive": "var(--pass)",
            "neutral":  "var(--allianz)",
            "concern":  "var(--reject)",
        }.get(c.tone, "var(--ink)")
        items.append(
            f"""
            <div class="kpi-row">
              <div class="kpi-label">{c.metric_name}</div>
              <div class="kpi-value" style="color:{tone_color}">{c.value_str}</div>
            </div>
            <div style="margin:-6px 0 12px 0; font-size:0.86rem; color:var(--ink-soft); line-height:1.55;">{c.sentence}</div>
            """
        )
    st.markdown("".join(items), unsafe_allow_html=True)


# ============================================================================
# DIRECT LENDING form + analysis
# ============================================================================
if preset.type == "DL":
    with col_form:
        section_head("Essentials")
        name = st.text_input("Borrower name", value=preset.borrower.name)
        ebitda = st.number_input("EBITDA (M)", value=float(preset.borrower.ebitda), min_value=0.1, step=1.0)
        loan_amount = st.number_input("Loan amount (M)", value=float(preset.loan.loan_amount), min_value=1.0, step=5.0)
        margin_bps = st.number_input("Margin (bps)", value=float(preset.loan.margin_bps), min_value=0.0, step=25.0)
        maturity = st.number_input("Maturity (years)", value=float(preset.loan.maturity_years), min_value=1.0, step=1.0)
        rating_choices = ["AAA", "AA", "A", "BBB+", "BBB", "BBB-", "BB+", "BB", "BB-", "B+", "B", "B-", "CCC"]
        rating_default = preset.risk.rating_estim if preset.risk.rating_estim in rating_choices else "B"
        rating = st.selectbox("Rating", rating_choices, index=rating_choices.index(rating_default))
        lgd = st.number_input("LGD (%)", value=float(preset.risk.lgd), min_value=0.0, max_value=100.0, step=5.0)

        with st.expander("Advanced — sector, base rate, fees, covenants, FCF"):
            sectors = ["SaaS", "Healthcare", "Industrials", "Consumer", "TMT", "Other"]
            sector = st.selectbox("Sector", sectors, index=sectors.index(preset.borrower.sector))
            base_rate_type = st.selectbox(
                "Base rate", ["EURIBOR 3M", "SOFR 3M", "SONIA", "ESTR"],
                index=["EURIBOR 3M", "SOFR 3M", "SONIA", "ESTR"].index(preset.loan.base_rate_type),
            )
            base_rate_level = st.number_input(
                "Base rate level (%)", value=float(preset.loan.base_rate_level), min_value=0.0, step=0.05
            )
            oid = st.number_input("OID (%)", value=float(preset.loan.oid_pct), min_value=0.0, step=0.1)
            upfront = st.number_input("Upfront fee (%)", value=float(preset.loan.upfront_pct), min_value=0.0, step=0.1)
            profile = st.selectbox(
                "Profile", ["Bullet", "Amortizing", "DDTL"],
                index=["Bullet", "Amortizing", "DDTL"].index(preset.loan.profile),
            )
            tranche = st.selectbox(
                "Tranche", ["RCF", "1L Term Loan", "Unitranche", "2L", "Mezzanine"],
                index=["RCF", "1L Term Loan", "Unitranche", "2L", "Mezzanine"].index(preset.loan.tranche_type),
            )
            capex_maint = st.number_input(
                "Capex maintenance (M/y)", value=float(preset.borrower.capex_maintenance), min_value=0.0, step=0.5
            )
            fcf_conv = st.number_input(
                "FCF conversion (%)", value=float(preset.borrower.fcf_conversion), min_value=0.0, max_value=100.0, step=1.0
            )
            cov_lev = st.number_input(
                "Covenant Net Lev cap (×)", value=float(preset.covenants.cov_net_lev_cap), min_value=0.5, step=0.25
            )
            pd_annual = st.number_input("PD annual (%)", value=float(preset.risk.pd_annual), min_value=0.0, step=0.1)

    # Compute
    metrics = compute_dl_metrics(
        ebitda=ebitda,
        loan_amount=loan_amount,
        base_rate_level=base_rate_level,
        margin_bps=margin_bps,
        oid_pct=oid,
        upfront_pct=upfront,
        maturity_years=maturity,
        profile=profile,
        capex_maintenance=capex_maint,
        fcf_conversion=fcf_conv,
        pd_annual=pd_annual,
        lgd=lgd,
        cov_net_lev_cap=cov_lev,
    )
    shock = s2_shock_effective(rating, maturity)
    roc = return_on_capital_s2(metrics.yield_net, shock)
    v = verdict_dl(metrics, roc, maturity, alm)

    inputs_dict = {
        "rating": rating, "sector": sector, "cov_net_lev_cap": cov_lev,
        "pd_annual": pd_annual, "lgd": lgd, "maturity_years": maturity,
    }
    commentaries = (
        analyze_dl(metrics, inputs_dict, alm)
        + comment_s2(shock, roc, qii_eligible=False, qii_reduction_pct=0,
                     rating=rating, maturity=maturity)
        + [comment_alm("DL", maturity, alm)]
    )

    # Rebuild a DLDeal for exports
    deal_for_export = DLDeal(
        id=template_id, label=preset.label, currency=preset.currency,
        borrower=DLBorrower(
            name=name, sector=sector, ebitda=ebitda,
            ebitda_growth=preset.borrower.ebitda_growth,
            ebitda_margin=preset.borrower.ebitda_margin,
            capex_maintenance=capex_maint, fcf_conversion=fcf_conv,
            arr_share=preset.borrower.arr_share,
            top10_clients=preset.borrower.top10_clients,
            sponsor_name=preset.borrower.sponsor_name,
            sponsor_tier=preset.borrower.sponsor_tier,
        ),
        loan=DLLoan(
            loan_amount=loan_amount, tranche_type=tranche,
            base_rate_type=base_rate_type, base_rate_level=base_rate_level,
            margin_bps=margin_bps, oid_pct=oid, upfront_pct=upfront,
            floor_pct=preset.loan.floor_pct, maturity_years=maturity,
            profile=profile, rcf_amount=preset.loan.rcf_amount,
        ),
        covenants=DLCovenants(
            cov_net_lev_cap=cov_lev, cov_ic_min=preset.covenants.cov_ic_min,
            cov_fccr_min=preset.covenants.cov_fccr_min,
            cov_lite=preset.covenants.cov_lite,
            dividend_basket_eur_m=preset.covenants.dividend_basket_eur_m,
        ),
        risk=DLRisk(rating_estim=rating, pd_annual=pd_annual, lgd=lgd),
    )

# ============================================================================
# INFRA DEBT form + analysis
# ============================================================================
else:
    with col_form:
        section_head("Essentials")
        project_name = st.text_input("Project name", value=preset.spv.project_name)
        capacity = st.number_input(
            "Capacity (MW)", value=float(preset.offtake.capacity_mw), min_value=0.0, step=10.0
        )
        strike = st.number_input(
            "Strike / unit revenue", value=float(preset.offtake.strike_price_eur_mwh), min_value=0.0
        )
        capex = st.number_input(
            "Capex total (M)", value=float(preset.project.capex_total_eur_m), min_value=1.0, step=50.0
        )
        debt_amount = st.number_input(
            "Debt amount (M)", value=float(preset.debt.debt_amount_eur_m), min_value=1.0, step=50.0
        )
        debt_maturity = st.number_input(
            "Debt maturity (years)", value=int(preset.debt.debt_maturity_years), min_value=1, step=1
        )
        rating_choices_i = ["AAA", "AA", "A", "BBB+", "BBB", "BBB-", "BB+", "BB", "BB-", "B+", "B", "B-", "CCC"]
        rating_default_i = preset.risk.rating_estim if preset.risk.rating_estim in rating_choices_i else "BBB"
        rating = st.selectbox("Rating", rating_choices_i, index=rating_choices_i.index(rating_default_i))

        with st.expander("Advanced — offtake, opex, debt structure, QII, risk"):
            sectors = ["Renewable solar", "Renewable wind onshore", "Renewable wind offshore",
                       "Renewable hydro", "Data center", "Transport", "Social", "Utility"]
            sector = st.selectbox("Sector", sectors, index=sectors.index(preset.spv.sector))
            offtake_choices = ["PPA fix", "PPA indexed", "CfD", "Take-or-pay",
                               "Availability payment", "Merchant"]
            offtake_type = st.selectbox(
                "Offtake type", offtake_choices,
                index=offtake_choices.index(preset.offtake.offtake_type),
            )
            indexation = st.selectbox(
                "Indexation", ["Fixed", "CPI", "Formula"],
                index=["Fixed", "CPI", "Formula"].index(preset.offtake.indexation),
            )
            cpi = st.number_input("CPI / escalator (%)", value=float(preset.offtake.cpi_pct), min_value=0.0, step=0.25)
            cap_factor = st.number_input(
                "Capacity factor (%)", value=float(preset.offtake.capacity_factor),
                min_value=0.0, max_value=100.0, step=1.0,
            )
            opex = st.number_input("Opex annual (M/y)", value=float(preset.project.opex_annual_eur_m), min_value=0.0, step=1.0)
            hm_freq = st.number_input(
                "Heavy maint frequency (y)", value=int(preset.project.heavy_maint_frequency_years), min_value=0
            )
            hm_amount = st.number_input(
                "Heavy maint amount (M)", value=float(preset.project.heavy_maint_amount_eur_m), min_value=0.0
            )
            plife = st.number_input("Project life (y)", value=int(preset.project.project_life_years), min_value=5)
            debt_profile = st.selectbox(
                "Debt profile", ["Amortizing sculpté", "Bullet"],
                index=["Amortizing sculpté", "Bullet"].index(preset.debt.debt_profile),
            )
            debt_base = st.selectbox(
                "Debt base rate", ["EURIBOR 3M", "SOFR 3M", "SONIA", "ESTR"],
                index=["EURIBOR 3M", "SOFR 3M", "SONIA", "ESTR"].index(preset.debt.debt_base_rate_type),
            )
            debt_rate = st.number_input(
                "Debt base rate level (%)", value=float(preset.debt.debt_base_rate_level), min_value=0.0, step=0.05
            )
            debt_margin = st.number_input(
                "Debt margin (bps)", value=float(preset.debt.debt_margin_bps), min_value=0.0, step=25.0
            )
            pd_annual = st.number_input("PD annual (%)", value=float(preset.risk.pd_annual), min_value=0.0, step=0.05)
            lgd = st.number_input("LGD (%)", value=float(preset.risk.lgd), min_value=0.0, max_value=100.0, step=5.0)
            qii_eligible = st.checkbox("QII eligible", value=preset.risk.qii_eligible)
            qii_reduction = st.number_input(
                "QII spread reduction (%)", value=float(preset.risk.qii_spread_reduction),
                min_value=0.0, max_value=100.0, step=5.0,
            )

    metrics = compute_infra_metrics(
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
    shock = s2_shock_effective(
        rating, debt_maturity, qii_eligible=qii_eligible, qii_reduction_pct=qii_reduction
    )
    roc = return_on_capital_s2(metrics.yield_net_pct, shock)
    v = verdict_infra(metrics, roc, debt_maturity, alm)

    inputs_dict = {
        "rating": rating, "qii_eligible": qii_eligible,
        "pd_annual": pd_annual, "lgd": lgd,
    }
    commentaries = (
        analyze_infra(metrics, inputs_dict, alm)
        + comment_s2(shock, roc, qii_eligible=qii_eligible,
                     qii_reduction_pct=qii_reduction, rating=rating,
                     maturity=debt_maturity)
        + [comment_alm("INFRA", debt_maturity, alm)]
    )

    deal_for_export = InfraDeal(
        id=template_id, label=preset.label, currency=preset.currency,
        spv=InfraSPV(
            project_name=project_name, sector=sector,
            country=preset.spv.country, sponsor=preset.spv.sponsor,
        ),
        offtake=InfraOfftake(
            offtake_type=offtake_type, strike_price_eur_mwh=strike,
            indexation=indexation, cpi_pct=cpi,
            contract_duration_years=preset.offtake.contract_duration_years,
            capacity_mw=capacity, capacity_factor=cap_factor,
        ),
        project=InfraProject(
            capex_total_eur_m=capex, opex_annual_eur_m=opex,
            heavy_maint_frequency_years=int(hm_freq),
            heavy_maint_amount_eur_m=hm_amount,
            cod_year=preset.project.cod_year, project_life_years=int(plife),
        ),
        debt=InfraDebt(
            debt_amount_eur_m=debt_amount, debt_maturity_years=int(debt_maturity),
            debt_profile=debt_profile, debt_base_rate_type=debt_base,
            debt_base_rate_level=debt_rate, debt_margin_bps=debt_margin,
            dsra_months=preset.debt.dsra_months,
        ),
        risk=InfraRisk(
            rating_estim=rating, pd_annual=pd_annual, lgd=lgd,
            qii_eligible=qii_eligible, qii_spread_reduction=qii_reduction,
        ),
    )


# ============================================================================
# ANALYSIS column — common to DL and Infra
# ============================================================================
with col_analysis:
    section_head("Verdict")
    st.markdown(
        f'<div style="font-size:1.05rem; letter-spacing:0.18em; text-transform:uppercase; '
        f'color:var(--ink-soft); margin-bottom:8px">Recommendation</div>'
        f'<div style="margin-bottom:24px">{verdict_pill_html(v.final)}</div>',
        unsafe_allow_html=True,
    )

    section_head("Three pillars")
    st.markdown(
        pillar_line("Credit", v.credit.status,
                    v.credit.reason or "All credit thresholds met.")
        + pillar_line("Solvency II", v.s2.status,
                      v.s2.reason or "RoC S2 above the 35% comfort line.")
        + pillar_line("ALM Mandate Fit", v.alm.status,
                      v.alm.reason or "Duration and liquidity within mandate."),
        unsafe_allow_html=True,
    )

    section_head("Reading the deal")
    _commentary_block(commentaries)

    # Stress summary — three short lines
    section_head("Stress")
    if preset.type == "DL":
        st.markdown(
            f"""
            <div style="font-size:0.88rem; line-height:1.65; color:var(--ink);">
              <div><b>Base case</b> — IC {metrics.interest_coverage:.2f}× · FCCR {metrics.fccr:.2f}×</div>
              <div><b>EBITDA −20%</b> — IC {metrics.ic_stressed:.2f}× · FCCR {metrics.fccr_stressed:.2f}×</div>
              <div><b>+200 bps and EBITDA −20%</b> — IC {metrics.ic_combined:.2f}× · FCCR {metrics.fccr_combined:.2f}×</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            f"""
            <div style="font-size:0.88rem; line-height:1.65; color:var(--ink);">
              <div><b>Base case</b> — min DSCR {metrics.min_dscr:.2f}× · LLCR {metrics.llcr:.2f}×</div>
              <div><b>P90 (production −15%)</b> — min DSCR {metrics.min_dscr_p90:.2f}×</div>
              <div><b>Combined</b> — min DSCR {metrics.min_dscr_combined:.2f}×</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    section_head("Exports")
    # We need a DL + Infra pair for the existing builders. Use the template
    # itself as the counterpart when only one side is being analysed.
    counterpart = next(
        (d for d in all_deals if d.type != preset.type),
        all_deals[1] if preset.type == "DL" else all_deals[0],
    )
    if preset.type == "DL":
        xlsx_bytes = build_excel_report(dl=deal_for_export, infra=counterpart)
        pptx_bytes = build_pptx_report(dl=deal_for_export, infra=counterpart)
    else:
        xlsx_bytes = build_excel_report(dl=counterpart, infra=deal_for_export)
        pptx_bytes = build_pptx_report(dl=counterpart, infra=deal_for_export)

    today = _dt.date.today().isoformat()
    e_col, p_col = st.columns(2)
    with e_col:
        st.download_button(
            "Download Excel model",
            data=xlsx_bytes,
            file_name=f"capital_lens_{template_id}_{today}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    with p_col:
        st.download_button(
            "Download IC slide deck",
            data=pptx_bytes,
            file_name=f"capital_lens_{template_id}_{today}.pptx",
            mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
        )

render_footer()
