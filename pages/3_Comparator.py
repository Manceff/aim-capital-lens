"""Comparator — side-by-side DL vs Infra Debt + 3-pillar verdict."""

from __future__ import annotations

import streamlit as st

from src.calculations.dl_metrics import compute_dl_metrics_from_model
from src.calculations.project_finance import compute_infra_metrics_from_model
from src.calculations.s2_capital import return_on_capital_s2, s2_shock_effective
from src.calculations.verdict_engine import verdict_dl, verdict_infra
from src.utils.presets_loader import get_deal_by_id, load_alm_mandate, load_preset_deals
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

st.set_page_config(page_title="Capital Lens — Comparator", layout="wide")
inject_css()
st.title("Side-by-side Comparator")

alm = render_alm_banner()


def _compute_dl_view(deal_id: str):
    d = get_deal_by_id(deal_id)
    m = compute_dl_metrics_from_model(d)
    shock = s2_shock_effective(d.risk.rating_estim, d.loan.maturity_years)
    roc = return_on_capital_s2(m.yield_net, shock)
    v = verdict_dl(m, roc, d.loan.maturity_years, alm)
    return {
        "label": d.label,
        "currency": d.currency,
        "rows": [
            ("Net leverage", safe_fmt(m.net_leverage, "{:.2f}×")),
            ("Interest coverage", safe_fmt(m.interest_coverage, "{:.2f}×")),
            ("FCCR", safe_fmt(m.fccr, "{:.2f}×")),
            ("Debt yield", safe_fmt(m.debt_yield, "{:.1f}%")),
            ("All-in yield", safe_fmt(m.all_in_yield, "{:.2f}%")),
            ("Expected loss (annual)", safe_fmt(m.el_annual, "{:.2f}%")),
            ("Yield net of EL", safe_fmt(m.yield_net, "{:.2f}%")),
            ("Spread shock — Art 176(3)", safe_fmt(shock, "{:.1f}%")),
            ("Return on capital S2", safe_fmt(roc, "{:.1f}%")),
            ("Duration / tenor", f"{d.loan.maturity_years:.0f}y"),
            ("IC stressed (−20% EBITDA)", safe_fmt(m.ic_stressed, "{:.2f}×")),
            ("FCCR combined (stress)", safe_fmt(m.fccr_combined, "{:.2f}×")),
        ],
        "roc_s2": roc,
        "verdict": v,
    }


def _compute_infra_view(deal_id: str):
    d = get_deal_by_id(deal_id)
    m = compute_infra_metrics_from_model(d)
    shock = s2_shock_effective(
        d.risk.rating_estim, d.debt.debt_maturity_years,
        qii_eligible=d.risk.qii_eligible, qii_reduction_pct=d.risk.qii_spread_reduction,
    )
    roc = return_on_capital_s2(m.yield_net_pct, shock)
    v = verdict_infra(m, roc, d.debt.debt_maturity_years, alm)
    return {
        "label": d.label,
        "currency": d.currency,
        "rows": [
            ("Min DSCR", safe_fmt(m.min_dscr, "{:.2f}×")),
            ("Avg DSCR", safe_fmt(m.avg_dscr, "{:.2f}×")),
            ("LLCR", safe_fmt(m.llcr, "{:.2f}×")),
            ("PLCR", safe_fmt(m.plcr, "{:.2f}×")),
            ("All-in yield", safe_fmt(m.all_in_yield_pct, "{:.2f}%")),
            ("Expected loss (annual)", safe_fmt(m.el_annual_pct, "{:.3f}%")),
            ("Yield net of EL", safe_fmt(m.yield_net_pct, "{:.2f}%")),
            ("Spread shock — effective", safe_fmt(shock, "{:.1f}%")),
            ("Return on capital S2", safe_fmt(roc, "{:.1f}%")),
            ("Duration / tenor", f"{d.debt.debt_maturity_years}y"),
            ("Min DSCR P90 (stress)", safe_fmt(m.min_dscr_p90, "{:.2f}×")),
            ("Tail (project − debt maturity)", f"{m.tail_years:.0f}y"),
        ],
        "roc_s2": roc,
        "verdict": v,
    }


all_deals = load_preset_deals()
dl_ids = [d.id for d in all_deals if d.type == "DL"]
infra_ids = [d.id for d in all_deals if d.type == "INFRA"]

col_sel_a, col_sel_b = st.columns(2)
with col_sel_a:
    a_id = st.selectbox("Left — Direct Lending", options=dl_ids,
                        format_func=lambda x: get_deal_by_id(x).label)
with col_sel_b:
    b_id = st.selectbox("Right — Infrastructure Debt", options=infra_ids,
                        format_func=lambda x: get_deal_by_id(x).label)

A = _compute_dl_view(a_id)
B = _compute_infra_view(b_id)

st.markdown("")

col_a, col_b = st.columns(2)
with col_a:
    section_head(A["label"])
    st.caption(f"Currency: {A['currency']}")
    html = "".join(
        kpi_row(label, value, best=(label == "Return on capital S2" and A["roc_s2"] > B["roc_s2"]))
        for label, value in A["rows"]
    )
    st.markdown(html, unsafe_allow_html=True)

with col_b:
    section_head(B["label"])
    st.caption(f"Currency: {B['currency']}")
    html = "".join(
        kpi_row(label, value, best=(label == "Return on capital S2" and B["roc_s2"] > A["roc_s2"]))
        for label, value in B["rows"]
    )
    st.markdown(html, unsafe_allow_html=True)

st.markdown("")

section_head("Verdict — 3 pillars")
vcol_a, vcol_b = st.columns(2)
with vcol_a:
    st.markdown(f"##### {A['label']}")
    st.markdown(
        pillar_line("Credit", A["verdict"].credit.status, A["verdict"].credit.reason or "All credit thresholds met.")
        + pillar_line("Solvency II", A["verdict"].s2.status, A["verdict"].s2.reason or "RoC S2 above 35%.")
        + pillar_line("ALM Mandate Fit", A["verdict"].alm.status, A["verdict"].alm.reason or "Within ALM duration and liquidity."),
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<div style="margin-top:14px;font-size:0.7rem;letter-spacing:0.18em;text-transform:uppercase;color:var(--ink-soft)">Final&nbsp;&nbsp; {verdict_pill_html(A["verdict"].final)}</div>',
        unsafe_allow_html=True,
    )

with vcol_b:
    st.markdown(f"##### {B['label']}")
    st.markdown(
        pillar_line("Credit", B["verdict"].credit.status, B["verdict"].credit.reason or "Min DSCR and LLCR within bounds.")
        + pillar_line("Solvency II", B["verdict"].s2.status, B["verdict"].s2.reason or "RoC S2 above 35%.")
        + pillar_line("ALM Mandate Fit", B["verdict"].alm.status, B["verdict"].alm.reason or "Within ALM duration and liquidity."),
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<div style="margin-top:14px;font-size:0.7rem;letter-spacing:0.18em;text-transform:uppercase;color:var(--ink-soft)">Final&nbsp;&nbsp; {verdict_pill_html(B["verdict"].final)}</div>',
        unsafe_allow_html=True,
    )

st.markdown("")
section_head("Recommendation")
best_roc_label = A["label"] if A["roc_s2"] > B["roc_s2"] else B["label"]
best_value = max(A["roc_s2"], B["roc_s2"])
st.markdown(
    f"- Best return on Solvency II capital: **{best_roc_label}** at **{best_value:.1f}%**.  \n"
    f"- {A['label']} — final **{A['verdict'].final}**.  \n"
    f"- {B['label']} — final **{B['verdict'].final}**.  \n"
    f"- Where a deal triggers an ALM REJECT, the analyst escalates to the Risk &amp; ALM Committee — "
    f"the duration and liquidity envelope sits in their scope, not in Alt Investments."
)

st.session_state["comparator_state"] = {
    "deal_a_id": a_id,
    "deal_b_id": b_id,
    "deal_a_rows": A["rows"],
    "deal_b_rows": B["rows"],
    "deal_a_verdict": A["verdict"].model_dump(),
    "deal_b_verdict": B["verdict"].model_dump(),
    "deal_a_roc_s2": A["roc_s2"],
    "deal_b_roc_s2": B["roc_s2"],
    "deal_a_label": A["label"],
    "deal_b_label": B["label"],
    "deal_a_currency": A["currency"],
    "deal_b_currency": B["currency"],
}

render_footer()
