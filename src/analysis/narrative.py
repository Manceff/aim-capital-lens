"""Narrative engine — turn numeric metrics into one-sentence analyst commentary.

Each metric is read against thresholds tied to the deal type, rating, and
covenant context. The output is a list of Commentary records consumed by the
Analyzer page (and re-usable by exports if needed).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

Tone = Literal["positive", "neutral", "concern"]


@dataclass
class Commentary:
    metric_name: str
    value_str: str
    sentence: str
    tone: Tone


# --------------------------------------------------------------------------- #
# Direct Lending
# --------------------------------------------------------------------------- #
def analyze_dl(metrics, inputs: dict, alm) -> list[Commentary]:
    """`metrics` is a DLMetrics dataclass; `inputs` is the dict held in
    st.session_state so we can read rating, sector, covenant cap, etc."""
    out: list[Commentary] = []

    rating: str = inputs.get("rating", "B")
    sector: str = inputs.get("sector", "Other")
    cov_cap: float = inputs.get("cov_net_lev_cap", 7.0)

    # Net leverage --------------------------------------------------------
    nl = metrics.net_leverage
    headroom_pct = (cov_cap / nl - 1) * 100 if nl > 0 else 0
    if nl < 3.5:
        tone, body = "positive", "conservative leverage for a sponsor-backed unitranche"
    elif nl < 5.0:
        tone, body = "positive", "mid-cap mid-range, sits comfortably below covenant"
    elif nl < 6.0:
        tone, body = "neutral", "upper mid-cap unitranche territory"
    elif nl < 7.0:
        tone, body = "concern", "stretched leverage — limited room before covenant"
    else:
        tone, body = "concern", "above the covenant cap — covenant breach without amend-and-extend"
    out.append(Commentary(
        "Net leverage", f"{nl:.2f}×",
        f"{body}. {headroom_pct:+.0f}% headroom to the {cov_cap:.1f}× covenant. "
        f"Common range for {rating} {sector} borrowers.",
        tone,
    ))

    # Interest coverage ---------------------------------------------------
    ic = metrics.interest_coverage
    ic_stress = metrics.ic_stressed
    rate_stress = metrics.ic_rate_stressed
    if ic >= 2.5:
        tone, body = "positive", "strong interest coverage"
    elif ic >= 1.7:
        tone, body = "positive", "comfortable coverage above the 1.5× floor"
    elif ic >= 1.5:
        tone, body = "neutral", "just above the 1.5× covenant — limited cushion"
    else:
        tone, body = "concern", "below the 1.5× covenant floor"
    out.append(Commentary(
        "Interest coverage", f"{ic:.2f}×",
        f"{body}. Under EBITDA −20% it falls to {ic_stress:.2f}×; "
        f"under +200 bps it lands at {rate_stress:.2f}×.",
        tone,
    ))

    # FCCR ----------------------------------------------------------------
    fccr = metrics.fccr
    if fccr >= 1.5:
        tone, body = "positive", "robust fixed-charge coverage including capex"
    elif fccr >= 1.2:
        tone, body = "neutral", "FCCR above the 1.2× covenant but tighter than IC"
    else:
        tone, body = "concern", "FCCR below 1.2× — capex burden too heavy"
    out.append(Commentary(
        "FCCR", f"{fccr:.2f}×",
        f"{body}. Combined stress (EBITDA −20% and +200 bps) brings it to "
        f"{metrics.fccr_combined:.2f}×.",
        tone,
    ))

    # All-in yield --------------------------------------------------------
    yield_all = metrics.all_in_yield
    if yield_all >= 10:
        tone = "positive"
    elif yield_all >= 8:
        tone = "neutral"
    else:
        tone = "concern"
    out.append(Commentary(
        "All-in yield", f"{yield_all:.2f}%",
        f"Base rate + margin gross-up to {yield_all:.2f}% per annum, "
        f"OID and upfront contribute "
        f"{metrics.oid_per_year + metrics.upfront_per_year:.2f}%/y over the {inputs.get('maturity_years', 7):.0f}y tenor.",
        tone,
    ))

    # Expected loss & yield net ------------------------------------------
    el = metrics.el_annual
    yield_net = metrics.yield_net
    if el <= 0.5:
        tone, body = "positive", "low expected-loss for the rating"
    elif el <= 1.5:
        tone, body = "neutral", "expected loss within typical sub-IG range"
    else:
        tone, body = "concern", "expected loss above the 1.5% comfort line"
    out.append(Commentary(
        "Expected loss (annual)", f"{el:.2f}%",
        f"{body}. PD {inputs.get('pd_annual', 2.5):.1f}% × LGD {inputs.get('lgd', 40):.0f}%. "
        f"Yield net of EL stands at {yield_net:.2f}%.",
        tone,
    ))

    return out


# --------------------------------------------------------------------------- #
# Infrastructure Debt
# --------------------------------------------------------------------------- #
def analyze_infra(metrics, inputs: dict, alm) -> list[Commentary]:
    out: list[Commentary] = []
    rating = inputs.get("rating", "BBB")
    qii = inputs.get("qii_eligible", False)

    # Min DSCR ------------------------------------------------------------
    md = metrics.min_dscr
    if md >= 1.50:
        tone, body = "positive", "strong base-case coverage"
    elif md >= 1.35:
        tone, body = "positive", "comfortably above the 1.20× project-finance floor"
    elif md >= 1.20:
        tone, body = "neutral", "tight but above the 1.20× floor"
    else:
        tone, body = "concern", "min DSCR below the 1.20× floor — credit risk"
    out.append(Commentary(
        "Min DSCR", f"{md:.2f}×",
        f"{body}. Under P90 production stress it falls to {metrics.min_dscr_p90:.2f}×. "
        f"Average DSCR over the loan life is {metrics.avg_dscr:.2f}×.",
        tone,
    ))

    # LLCR / PLCR ---------------------------------------------------------
    llcr = metrics.llcr
    if llcr >= 1.50:
        tone, body = "positive", "loan-life cover well above the 1.30× threshold"
    elif llcr >= 1.30:
        tone, body = "neutral", "loan-life cover at threshold"
    else:
        tone, body = "concern", "LLCR below the 1.30× threshold"
    out.append(Commentary(
        "LLCR", f"{llcr:.2f}×",
        f"{body}. PLCR {metrics.plcr:.2f}× captures the project-life cushion "
        f"({metrics.tail_years:.0f}y tail after debt maturity).",
        tone,
    ))

    # All-in yield --------------------------------------------------------
    out.append(Commentary(
        "All-in yield", f"{metrics.all_in_yield_pct:.2f}%",
        f"Base rate + margin gross-up. Yield net of EL: {metrics.yield_net_pct:.2f}%.",
        "neutral",
    ))

    # Expected loss -------------------------------------------------------
    el = metrics.el_annual_pct
    if el <= 0.10:
        tone, body = "positive", "very low expected loss typical of investment-grade infra"
    elif el <= 0.30:
        tone, body = "neutral", "expected loss in line with sub-IG infra"
    else:
        tone, body = "concern", "expected loss elevated for infrastructure debt"
    out.append(Commentary(
        "Expected loss (annual)", f"{el:.3f}%",
        f"{body}. PD {inputs.get('pd_annual', 0.20):.2f}% × LGD {inputs.get('lgd', 25):.0f}%. "
        f"LGD reflects asset-backed recovery profile.",
        tone,
    ))

    return out


# --------------------------------------------------------------------------- #
# Shared — Solvency II
# --------------------------------------------------------------------------- #
def comment_s2(shock_pct: float, roc_pct: float, qii_eligible: bool,
               qii_reduction_pct: float, rating: str, maturity: float) -> list[Commentary]:
    out: list[Commentary] = []

    shock_str = f"{shock_pct:.1f}%"
    if qii_eligible:
        body = (
            f"Article 176(3) shock reduced by {qii_reduction_pct:.0f}% under the QII regime "
            f"(Articles 164a / 164b) — eligible infrastructure debt."
        )
    else:
        body = (
            f"Article 176(3) shock at {shock_pct:.1f}% for {rating} at {maturity:.0f}y maturity. "
            f"No QII reduction applied."
        )
    out.append(Commentary("Spread shock S2", shock_str, body, "neutral"))

    if roc_pct >= 50:
        tone, lead = "positive", "outstanding return"
    elif roc_pct >= 35:
        tone, lead = "positive", "above the 35% IC comfort line"
    elif roc_pct >= 25:
        tone, lead = "neutral", "above the 25% acceptance floor but below the 35% comfort line"
    else:
        tone, lead = "concern", "below the 25% acceptance floor"
    out.append(Commentary(
        "Return on capital S2", f"{roc_pct:.1f}%",
        f"{lead}. Reads as net spread per unit of S2 capital. "
        + ("Pricing renegotiation likely needed." if roc_pct < 35 else "Adequate compensation for the capital charge."),
        tone,
    ))
    return out


def comment_alm(deal_type: str, maturity: float, alm) -> Commentary:
    if maturity < alm.alm_duration_min_years:
        return Commentary(
            "ALM duration check", f"{maturity:.0f}y",
            f"Tenor of {maturity:.0f}y is below the {alm.alm_duration_min_years:.0f}y "
            f"floor set by the Risk & ALM Committee. Falls outside the operational scope — "
            f"requires committee escalation.",
            "concern",
        )
    if maturity > alm.alm_duration_max_years:
        return Commentary(
            "ALM duration check", f"{maturity:.0f}y",
            f"Tenor of {maturity:.0f}y exceeds the {alm.alm_duration_max_years:.0f}y cap. "
            f"Requires escalation to the Risk & ALM Committee — they own the duration envelope.",
            "concern",
        )
    return Commentary(
        "ALM duration check", f"{maturity:.0f}y",
        f"Tenor of {maturity:.0f}y sits inside the {alm.alm_duration_min_years:.0f}–"
        f"{alm.alm_duration_max_years:.0f}y mandate window.",
        "positive",
    )
