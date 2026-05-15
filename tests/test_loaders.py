"""Phase 1 — sanity tests for YAML configs and Pydantic loaders."""

from __future__ import annotations

import pytest

from src.models.dl_deal import DLDeal
from src.models.infra_deal import InfraDeal
from src.utils.presets_loader import (
    get_deal_by_id,
    load_alm_mandate,
    load_article_176_3,
    load_preset_deals,
    load_ratings_pd,
)


def test_alm_mandate_loads():
    alm = load_alm_mandate()
    assert alm.alm_duration_min_years == 8
    assert alm.alm_duration_max_years == 15
    assert alm.alm_liquidity_floor_5y_pct == 30
    assert alm.s2_ratio_minimum_pct == 200
    assert "Risk & ALM Committee" in alm.mandate_owner


def test_article_176_3_has_six_ratings():
    art = load_article_176_3()
    expected = {"AAA", "AA", "A", "BBB", "BB", "B"}
    assert set(art["ratings"].keys()) == expected
    # Each rating row has all 6 maturity buckets
    for rating, row in art["ratings"].items():
        assert set(row.keys()) == {3, 5, 7, 10, 15, 20}, rating


def test_article_176_3_monotone_in_rating_and_maturity():
    art = load_article_176_3()["ratings"]
    # For each maturity, shock grows as rating quality declines
    for m in [3, 5, 7, 10, 15, 20]:
        assert art["AAA"][m] < art["AA"][m] < art["A"][m] < art["BBB"][m] < art["BB"][m] < art["B"][m]
    # For each rating, shock grows with maturity
    for r in ["AAA", "AA", "A", "BBB", "BB", "B"]:
        prev = 0
        for m in [3, 5, 7, 10, 15, 20]:
            assert art[r][m] > prev, (r, m)
            prev = art[r][m]


def test_ratings_pd_loads():
    pd = load_ratings_pd()
    assert "pd_annual_pct" in pd
    assert pd["pd_annual_pct"]["B+"] > pd["pd_annual_pct"]["BBB"]
    assert "lgd_pct_by_tranche" in pd
    assert pd["lgd_pct_by_tranche"]["Unitranche"] == 40


def test_preset_deals_load_three():
    deals = load_preset_deals()
    assert len(deals) == 3
    ids = {d.id for d in deals}
    assert ids == {"deal_a_dl_saas", "deal_b_infra_offshore", "deal_c_infra_datacenter"}


def test_deal_a_is_dl():
    d = get_deal_by_id("deal_a_dl_saas")
    assert isinstance(d, DLDeal)
    assert d.borrower.ebitda == 80
    assert d.loan.loan_amount == 440
    assert d.loan.margin_bps == 625


def test_deal_b_is_infra():
    d = get_deal_by_id("deal_b_infra_offshore")
    assert isinstance(d, InfraDeal)
    assert d.offtake.offtake_type == "CfD"
    assert d.risk.qii_eligible is True
    assert d.risk.qii_spread_reduction == 40


def test_deal_c_is_infra_datacenter():
    d = get_deal_by_id("deal_c_infra_datacenter")
    assert isinstance(d, InfraDeal)
    assert d.spv.sector == "Data center"
    assert d.debt.debt_amount_eur_m == 1300


def test_unknown_deal_raises():
    with pytest.raises(KeyError):
        get_deal_by_id("not_a_deal")
