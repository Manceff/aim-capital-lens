"""Phase 2 — DL metrics tests, anchored on Deal A spec values."""

from __future__ import annotations

import math

from src.calculations.dl_metrics import compute_dl_metrics, compute_dl_metrics_from_model
from src.utils.presets_loader import get_deal_by_id


def test_deal_a_net_leverage_5_5x():
    m = compute_dl_metrics_from_model(get_deal_by_id("deal_a_dl_saas"))
    assert math.isclose(m.net_leverage, 440 / 80, rel_tol=1e-6)
    assert math.isclose(m.net_leverage, 5.5, abs_tol=1e-6)


def test_deal_a_cash_interest_and_ic():
    m = compute_dl_metrics_from_model(get_deal_by_id("deal_a_dl_saas"))
    expected_cash_interest = 440 * (0.035 + 625 / 10_000)  # 440 * 0.0975 = 42.9
    assert math.isclose(m.cash_interest, expected_cash_interest, rel_tol=1e-6)
    assert math.isclose(m.interest_coverage, 80 / expected_cash_interest, rel_tol=1e-6)


def test_deal_a_all_in_yield():
    m = compute_dl_metrics_from_model(get_deal_by_id("deal_a_dl_saas"))
    # All-in = base 3.5 + margin 6.25 + OID 1.5/7 + upfront 1.0/7 + floor 0 = 9.75 + 0.2143 + 0.1429
    expected = 3.5 + 6.25 + 1.5 / 7 + 1.0 / 7 + 0
    assert math.isclose(m.all_in_yield, expected, rel_tol=1e-6)


def test_deal_a_el_and_yield_net():
    m = compute_dl_metrics_from_model(get_deal_by_id("deal_a_dl_saas"))
    # PD 2.5% × LGD 40% = 1.0%
    assert math.isclose(m.el_annual, 2.5 * 40 / 100, rel_tol=1e-6)
    assert math.isclose(m.yield_net, m.all_in_yield - m.el_annual, rel_tol=1e-6)


def test_deal_a_headroom_cov():
    m = compute_dl_metrics_from_model(get_deal_by_id("deal_a_dl_saas"))
    # cov_cap 7.0 / lev 5.5 - 1 = 0.2727
    assert math.isclose(m.headroom_net_lev, 7.0 / 5.5 - 1, rel_tol=1e-6)
    assert m.headroom_net_lev > 0.15  # passes our headroom rule


def test_deal_a_stress_ebitda_minus_20():
    m = compute_dl_metrics_from_model(get_deal_by_id("deal_a_dl_saas"))
    assert math.isclose(m.ebitda_stressed, 80 * 0.80, rel_tol=1e-6)
    assert math.isclose(m.net_lev_stressed, 440 / 64, rel_tol=1e-6)


def test_deal_a_stress_plus_200bps():
    m = compute_dl_metrics_from_model(get_deal_by_id("deal_a_dl_saas"))
    expected = 440 * (0.0975 + 0.02)
    assert math.isclose(m.cash_interest_stressed, expected, rel_tol=1e-6)


def test_debt_yield_pct_format():
    m = compute_dl_metrics_from_model(get_deal_by_id("deal_a_dl_saas"))
    # 80 / 440 = 18.18%
    assert math.isclose(m.debt_yield, 80 / 440 * 100, rel_tol=1e-6)
    assert 18 < m.debt_yield < 19


def test_amortizing_profile_mandatory_amort_nonzero():
    m = compute_dl_metrics(
        ebitda=100,
        loan_amount=500,
        base_rate_level=3.0,
        margin_bps=500,
        maturity_years=5,
        profile="Amortizing",
        pd_annual=2.0,
        lgd=35,
        cov_net_lev_cap=6.0,
    )
    assert math.isclose(m.mandatory_amort, 500 / 5)
    assert m.fccr < m.interest_coverage  # FCCR penalized by amort
