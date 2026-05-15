"""Page Comparator — side-by-side DL vs Infra + verdict 3 piliers."""

from __future__ import annotations

import streamlit as st

from src.calculations.dl_metrics import compute_dl_metrics_from_model
from src.calculations.project_finance import compute_infra_metrics_from_model
from src.calculations.s2_capital import return_on_capital_s2, s2_shock_effective
from src.calculations.verdict_engine import verdict_dl, verdict_infra
from src.utils.presets_loader import get_deal_by_id, load_alm_mandate, load_preset_deals
from src.utils.ui_common import (
    inject_css,
    render_alm_banner,
    render_footer,
    safe_fmt,
    section_head,
    verdict_badge_html,
)

st.set_page_config(page_title="Capital Lens — Comparator", page_icon="⚖️", layout="wide")
inject_css()
st.title("⚖️ Side-by-side Comparator")

alm = render_alm_banner()


def _compute_dl_view(deal_id: str):
    d = get_deal_by_id(deal_id)
    m = compute_dl_metrics_from_model(d)
    shock = s2_shock_effective(d.risk.rating_estim, d.loan.maturity_years)
    roc = return_on_capital_s2(m.yield_net, shock)
    v = verdict_dl(m, roc, d.loan.maturity_years, alm)
    return {
        "deal": d,
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
        "deal": d,
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
            ("Tail (project life − debt mat.)", f"{m.tail_years:.0f}y"),
        ],
        "roc_s2": roc,
        "verdict": v,
    }


# Select two deals to compare
all_deals = load_preset_deals()
dl_ids = [d.id for d in all_deals if d.type == "DL"]
infra_ids = [d.id for d in all_deals if d.type == "INFRA"]

col_sel_a, col_sel_b = st.columns(2)
with col_sel_a:
    a_id = st.selectbox(
        "Left deal (DL)", options=dl_ids,
        format_func=lambda x: get_deal_by_id(x).label,
    )
with col_sel_b:
    b_id = st.selectbox(
        "Right deal (Infra Debt)", options=infra_ids,
        format_func=lambda x: get_deal_by_id(x).label,
    )

A = _compute_dl_view(a_id)
B = _compute_infra_view(b_id)

# Build comparator rows. Some metrics differ in name between DL and Infra so we align by index.
metric_labels = [
    "Credit ratio 1", "Credit ratio 2", "Credit ratio 3", "Credit ratio 4",
    "All-in yield", "Expected loss", "Yield net", "Spread shock S2",
    "Return on capital S2", "Duration", "Stress headline", "Tail / combined stress",
]

st.markdown("---")

col_a, col_b = st.columns(2)
with col_a:
    section_head(f"Deal A — {A['label']}")
    st.caption(f"Currency: {A['currency']}")
    for label, value in A["rows"]:
        bold = "**" if label == "Return on capital S2" else ""
        marker = "  ◀ best" if (label == "Return on capital S2" and A["roc_s2"] > B["roc_s2"]) else ""
        st.markdown(f"{bold}{label}{bold} : {bold}{value}{bold}{marker}")

with col_b:
    section_head(f"Deal B — {B['label']}")
    st.caption(f"Currency: {B['currency']}")
    for label, value in B["rows"]:
        bold = "**" if label == "Return on capital S2" else ""
        marker = "  ◀ best" if (label == "Return on capital S2" and B["roc_s2"] > A["roc_s2"]) else ""
        st.markdown(f"{bold}{label}{bold} : {bold}{value}{bold}{marker}")

st.markdown("---")

section_head("Verdict — 3 pillars")
vcol_a, vcol_b = st.columns(2)
with vcol_a:
    st.markdown(f"##### Deal A — {A['label']}")
    st.markdown(
        f"- **Crédit** {verdict_badge_html(A['verdict'].credit.status)} "
        f"<small>{A['verdict'].credit.reason or 'all credit thresholds met'}</small>",
        unsafe_allow_html=True,
    )
    st.markdown(
        f"- **Solvency II** {verdict_badge_html(A['verdict'].s2.status)} "
        f"<small>{A['verdict'].s2.reason or 'RoC S2 ≥ 35%'}</small>",
        unsafe_allow_html=True,
    )
    st.markdown(
        f"- **ALM Mandate Fit** {verdict_badge_html(A['verdict'].alm.status)} "
        f"<small>{A['verdict'].alm.reason or 'within ALM duration & liquidity'}</small>",
        unsafe_allow_html=True,
    )
    st.markdown(
        f"#### Final: {verdict_badge_html(A['verdict'].final)}",
        unsafe_allow_html=True,
    )

with vcol_b:
    st.markdown(f"##### Deal B — {B['label']}")
    st.markdown(
        f"- **Crédit** {verdict_badge_html(B['verdict'].credit.status)} "
        f"<small>{B['verdict'].credit.reason or 'min DSCR & LLCR within bounds'}</small>",
        unsafe_allow_html=True,
    )
    st.markdown(
        f"- **Solvency II** {verdict_badge_html(B['verdict'].s2.status)} "
        f"<small>{B['verdict'].s2.reason or 'RoC S2 ≥ 35%'}</small>",
        unsafe_allow_html=True,
    )
    st.markdown(
        f"- **ALM Mandate Fit** {verdict_badge_html(B['verdict'].alm.status)} "
        f"<small>{B['verdict'].alm.reason or 'within ALM duration & liquidity'}</small>",
        unsafe_allow_html=True,
    )
    st.markdown(
        f"#### Final: {verdict_badge_html(B['verdict'].final)}",
        unsafe_allow_html=True,
    )

st.markdown("---")
section_head("Recommendation")
best_roc = "Deal A" if A["roc_s2"] > B["roc_s2"] else "Deal B"
best_value = max(A["roc_s2"], B["roc_s2"])
st.markdown(
    f"- **Best return on S2 capital**: {best_roc} at {best_value:.1f}%.\n"
    f"- **Deal A — {A['verdict'].final}**: "
    f"{'all 3 pillars green' if A['verdict'].final == 'PROCEED' else 'see pillar reasons above'}.\n"
    f"- **Deal B — {B['verdict'].final}**: "
    f"{'all 3 pillars green' if B['verdict'].final == 'PROCEED' else 'see pillar reasons above'}.\n"
    f"- Where a deal triggers an **ALM REJECT**, the analyst escalates to the Risk & ALM Committee "
    f"(scope ALM, not Alt Investments)."
)

# Persist for exports
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
