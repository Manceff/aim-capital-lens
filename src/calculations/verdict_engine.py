"""Verdict 3-piliers — credit · S2 · ALM Mandate Fit."""

from __future__ import annotations

from src.models.alm_mandate import ALMMandate
from src.models.verdict import Pillar, Verdict

ROC_S2_REJECT_BELOW_PCT = 25.0
ROC_S2_CONDITIONS_BELOW_PCT = 35.0
EL_CONDITIONS_ABOVE_PCT = 1.5
HEADROOM_CONDITIONS_BELOW = 0.15
IC_REJECT_BELOW = 1.5
FCCR_REJECT_BELOW = 1.2
IC_STRESS_CONDITIONS_BELOW = 1.3
DSCR_REJECT_BELOW = 1.20
LLCR_CONDITIONS_BELOW = 1.30


def _credit_pillar_dl(metrics) -> Pillar:
    if metrics.interest_coverage < IC_REJECT_BELOW or metrics.fccr < FCCR_REJECT_BELOW:
        return Pillar(status="REJECT", reason="IC or FCCR below covenant threshold")
    if metrics.ic_stressed < IC_STRESS_CONDITIONS_BELOW or metrics.headroom_net_lev < HEADROOM_CONDITIONS_BELOW:
        return Pillar(status="CONDITIONS", reason="Stress test fragile or low covenant headroom")
    if metrics.el_annual > EL_CONDITIONS_ABOVE_PCT:
        return Pillar(
            status="CONDITIONS",
            reason=f"Expected loss {metrics.el_annual:.2f}% above 1.5% threshold",
        )
    return Pillar(status="PASS", reason=None)


def _credit_pillar_infra(metrics) -> Pillar:
    if metrics.min_dscr < DSCR_REJECT_BELOW:
        return Pillar(
            status="REJECT",
            reason=f"min DSCR {metrics.min_dscr:.2f}× below {DSCR_REJECT_BELOW:.2f}×",
        )
    if metrics.llcr < LLCR_CONDITIONS_BELOW:
        return Pillar(
            status="CONDITIONS",
            reason=f"LLCR {metrics.llcr:.2f}× below {LLCR_CONDITIONS_BELOW:.2f}×",
        )
    return Pillar(status="PASS", reason=None)


def _s2_pillar(roc_s2_pct: float) -> Pillar:
    if roc_s2_pct < ROC_S2_REJECT_BELOW_PCT:
        return Pillar(status="REJECT", reason=f"RoC S2 {roc_s2_pct:.1f}% below 25% threshold")
    if roc_s2_pct < ROC_S2_CONDITIONS_BELOW_PCT:
        return Pillar(
            status="CONDITIONS",
            reason=f"RoC S2 {roc_s2_pct:.1f}% — negotiate pricing +25 bps",
        )
    return Pillar(status="PASS", reason=None)


def _alm_pillar(deal_type: str, maturity_years: float, alm: ALMMandate) -> Pillar:
    reasons: list[str] = []
    if maturity_years < alm.alm_duration_min_years:
        reasons.append(
            f"Duration {maturity_years:.0f}y below ALM floor {alm.alm_duration_min_years:.0f}y"
        )
    if maturity_years > alm.alm_duration_max_years:
        reasons.append(
            f"Duration {maturity_years:.0f}y above ALM cap {alm.alm_duration_max_years:.0f}y"
        )
    # Liquidity: DL = 1.0 score, Infra = 0.3 score, both as fraction
    liquidity_score = 1.0 if deal_type == "DL" else 0.3
    if liquidity_score < alm.alm_liquidity_floor_5y_pct / 100:
        reasons.append(
            f"Liquidity score {liquidity_score:.2f} below ALM floor "
            f"{alm.alm_liquidity_floor_5y_pct:.0f}%"
        )
    if reasons:
        return Pillar(status="REJECT", reason=" · ".join(reasons))
    return Pillar(status="PASS", reason=None)


def verdict_dl(dl_metrics, roc_s2_pct: float, maturity_years: float, alm: ALMMandate) -> Verdict:
    credit = _credit_pillar_dl(dl_metrics)
    s2 = _s2_pillar(roc_s2_pct)
    alm_p = _alm_pillar("DL", maturity_years, alm)
    return Verdict(credit=credit, s2=s2, alm=alm_p, final=_final_status([credit, s2, alm_p]))


def verdict_infra(infra_metrics, roc_s2_pct: float, debt_maturity: float, alm: ALMMandate) -> Verdict:
    credit = _credit_pillar_infra(infra_metrics)
    s2 = _s2_pillar(roc_s2_pct)
    alm_p = _alm_pillar("INFRA", debt_maturity, alm)
    return Verdict(credit=credit, s2=s2, alm=alm_p, final=_final_status([credit, s2, alm_p]))


def _final_status(pillars) -> str:
    statuses = [p.status for p in pillars]
    if "REJECT" in statuses:
        return "REJECT"
    if "CONDITIONS" in statuses:
        return "CONDITIONS"
    return "PROCEED"
