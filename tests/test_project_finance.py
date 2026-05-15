"""Phase 2 — Infra Debt project finance tests."""

from __future__ import annotations

import math

import numpy as np

from src.calculations.project_finance import compute_infra_metrics, compute_infra_metrics_from_model
from src.utils.presets_loader import get_deal_by_id


def test_deal_b_offshore_wind_basic():
    m = compute_infra_metrics_from_model(get_deal_by_id("deal_b_infra_offshore"))
    # Project life = 25, debt maturity = 18
    assert len(m.cashflows) == 25
    assert m.tail_years == 25 - 18
    # Revenue year 1 = 1400 * 8760 * 50% * 75 / 1e6 = 459.9 M
    expected_rev_y1 = 1400 * 8760 * 0.5 * 75 * (1 + 0.02) / 1_000_000
    assert math.isclose(m.cashflows.loc[1, "revenue"], expected_rev_y1, rel_tol=1e-6)


def test_deal_b_debt_schedule_fully_amortizes():
    m = compute_infra_metrics_from_model(get_deal_by_id("deal_b_infra_offshore"))
    principal_sum = m.cashflows.loc[1:18, "debt_principal"].sum()
    assert math.isclose(principal_sum, 2800, rel_tol=1e-4)
    # No principal payments after maturity
    assert m.cashflows.loc[19:, "debt_principal"].sum() == 0


def test_deal_b_dscr_above_minimum():
    m = compute_infra_metrics_from_model(get_deal_by_id("deal_b_infra_offshore"))
    assert m.min_dscr >= 1.20, f"min DSCR {m.min_dscr} below floor"


def test_deal_b_llcr_plcr_relationship():
    m = compute_infra_metrics_from_model(get_deal_by_id("deal_b_infra_offshore"))
    # PLCR (project life) should be >= LLCR (loan life) because more cashflows
    assert m.plcr >= m.llcr
    assert m.llcr > 1.0  # debt covered by PV of cashflows


def test_deal_b_p90_stress_reduces_dscr():
    m = compute_infra_metrics_from_model(get_deal_by_id("deal_b_infra_offshore"))
    assert m.min_dscr_p90 < m.min_dscr


def test_deal_b_yield_net_positive():
    m = compute_infra_metrics_from_model(get_deal_by_id("deal_b_infra_offshore"))
    # All-in = 3.5 + 250/100 = 6.0%
    assert math.isclose(m.all_in_yield_pct, 3.5 + 2.5, rel_tol=1e-6)
    # EL = 0.20 * 25/100 = 0.05%
    assert math.isclose(m.el_annual_pct, 0.20 * 25 / 100, rel_tol=1e-6)
    assert m.yield_net_pct > 5.5


def test_bullet_schedule():
    m = compute_infra_metrics(
        capacity_mw=100,
        capacity_factor_pct=40,
        offtake_type="PPA fix",
        strike_price=60,
        indexation="Fixed",
        opex_annual=5,
        heavy_maint_frequency=0,
        heavy_maint_amount=0,
        capex_total=400,
        project_life=20,
        debt_amount=250,
        debt_maturity=10,
        debt_profile="Bullet",
        base_rate_level=3.0,
        margin_bps=300,
        pd_annual=0.3,
        lgd=25,
    )
    # Bullet: interest constant for years 1..10, principal only at maturity
    assert (m.cashflows.loc[1:9, "debt_principal"] == 0).all()
    assert math.isclose(m.cashflows.loc[10, "debt_principal"], 250)
    # Interest each year = 250 * (3% + 3%) = 15
    for t in range(1, 11):
        assert math.isclose(m.cashflows.loc[t, "debt_interest"], 250 * 0.06, rel_tol=1e-6)


def test_deal_c_datacenter():
    m = compute_infra_metrics_from_model(get_deal_by_id("deal_c_infra_datacenter"))
    assert len(m.cashflows) == 20
    assert m.tail_years == 20 - 15
    # SOFR 4.3 + 250bps = 6.8%
    assert math.isclose(m.all_in_yield_pct, 4.3 + 2.5, rel_tol=1e-6)
    assert m.min_dscr > 1.0
