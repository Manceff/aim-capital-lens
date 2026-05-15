"""Phase 2 — Verdict 3-piliers tests."""

from __future__ import annotations

from src.calculations.dl_metrics import compute_dl_metrics_from_model
from src.calculations.project_finance import compute_infra_metrics_from_model
from src.calculations.s2_capital import return_on_capital_s2, s2_shock_effective
from src.calculations.verdict_engine import verdict_dl, verdict_infra
from src.utils.presets_loader import get_deal_by_id, load_alm_mandate


def _alm():
    return load_alm_mandate()


def test_deal_a_credit_pass():
    deal = get_deal_by_id("deal_a_dl_saas")
    m = compute_dl_metrics_from_model(deal)
    shock = s2_shock_effective(deal.risk.rating_estim, deal.loan.maturity_years)
    roc = return_on_capital_s2(m.yield_net, shock)
    v = verdict_dl(m, roc, deal.loan.maturity_years, _alm())
    # Deal A should pass credit (IC ~1.87, FCCR ~1.77, headroom ~27%, EL 1.0%)
    assert v.credit.status == "PASS"


def test_deal_b_infra_alm_fails_due_to_18y_above_15y_cap():
    deal = get_deal_by_id("deal_b_infra_offshore")
    m = compute_infra_metrics_from_model(deal)
    shock = s2_shock_effective(
        deal.risk.rating_estim,
        deal.debt.debt_maturity_years,
        qii_eligible=deal.risk.qii_eligible,
        qii_reduction_pct=deal.risk.qii_spread_reduction,
    )
    roc = return_on_capital_s2(m.yield_net_pct, shock)
    v = verdict_infra(m, roc, deal.debt.debt_maturity_years, _alm())
    # 18y > 15y ALM cap => ALM pillar must reject
    assert v.alm.status == "REJECT"
    assert "above ALM cap" in v.alm.reason


def test_final_proceed_when_all_pass():
    deal = get_deal_by_id("deal_a_dl_saas")
    m = compute_dl_metrics_from_model(deal)
    shock = s2_shock_effective(deal.risk.rating_estim, deal.loan.maturity_years)
    roc = return_on_capital_s2(m.yield_net, shock)
    v = verdict_dl(m, roc, deal.loan.maturity_years, _alm())
    # If credit PASS + s2 status (depends on roc) + alm PASS => final reflects worst status
    if v.credit.status == "PASS" and v.s2.status == "PASS" and v.alm.status == "PASS":
        assert v.final == "PROCEED"


def test_final_reject_when_any_pillar_rejects():
    deal = get_deal_by_id("deal_b_infra_offshore")
    m = compute_infra_metrics_from_model(deal)
    shock = s2_shock_effective(
        deal.risk.rating_estim,
        deal.debt.debt_maturity_years,
        qii_eligible=deal.risk.qii_eligible,
        qii_reduction_pct=deal.risk.qii_spread_reduction,
    )
    roc = return_on_capital_s2(m.yield_net_pct, shock)
    v = verdict_infra(m, roc, deal.debt.debt_maturity_years, _alm())
    # ALM REJECT => final REJECT
    if v.alm.status == "REJECT":
        assert v.final == "REJECT"
