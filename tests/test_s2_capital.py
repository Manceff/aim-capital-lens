"""Phase 2 — Solvency II Article 176(3) tests."""

from __future__ import annotations

import math

import pytest

from src.calculations.s2_capital import (
    return_on_capital_s2,
    s2_shock_effective,
    s2_spread_shock,
)


def test_bbb_at_10y_table_value():
    # Direct table lookup: BBB at 10y = 20%
    assert math.isclose(s2_spread_shock("BBB", 10), 20.0, rel_tol=1e-6)


def test_b_at_7y_table_value():
    assert math.isclose(s2_spread_shock("B", 7), 45.9, rel_tol=1e-6)


def test_linear_interpolation_between_7_and_10():
    # BBB at 8y: 15.5 + (20.0-15.5) * (8-7)/(10-7) = 15.5 + 1.5 = 17
    assert math.isclose(s2_spread_shock("BBB", 8), 17.0, rel_tol=1e-6)


def test_clamp_below_3y():
    # Maturities below 3y => return 3y value
    assert math.isclose(s2_spread_shock("BBB", 1), 7.5, rel_tol=1e-6)


def test_clamp_above_20y():
    assert math.isclose(s2_spread_shock("BBB", 30), 30.0, rel_tol=1e-6)


def test_notch_mapping_bbb_minus_to_bb():
    # BBB- notch-mapped to BB row (conservative)
    assert math.isclose(s2_spread_shock("BBB-", 10), s2_spread_shock("BB", 10), rel_tol=1e-6)


def test_notch_mapping_b_plus_to_b():
    assert math.isclose(s2_spread_shock("B+", 7), s2_spread_shock("B", 7), rel_tol=1e-6)


def test_qii_reduction_applied():
    base = s2_spread_shock("BBB", 18)
    reduced = s2_shock_effective("BBB", 18, qii_eligible=True, qii_reduction_pct=40)
    assert math.isclose(reduced, base * 0.6, rel_tol=1e-6)


def test_qii_inactive_when_flag_off():
    base = s2_spread_shock("BBB", 18)
    same = s2_shock_effective("BBB", 18, qii_eligible=False, qii_reduction_pct=40)
    assert math.isclose(base, same, rel_tol=1e-6)


def test_unknown_rating_raises():
    with pytest.raises(KeyError):
        s2_spread_shock("XYZ", 7)


def test_roc_s2_formula():
    # yield_net 9%, shock 30% => 30%
    assert math.isclose(return_on_capital_s2(9.0, 30.0), 30.0, rel_tol=1e-6)
    # yield_net 6.3%, shock 12% (QII) => 52.5%
    assert math.isclose(return_on_capital_s2(6.3, 12.0), 52.5, rel_tol=1e-6)


def test_roc_s2_infinite_when_no_capital():
    assert math.isinf(return_on_capital_s2(5.0, 0.0))
