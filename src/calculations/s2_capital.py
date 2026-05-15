"""Solvency II spread shock — Article 176(3) lookup + QII reduction + RoC S2.

Spec: CAPITAL_LENS_SPEC.md §5.C. Linear interpolation between maturity buckets.
"""

from __future__ import annotations

from src.utils.presets_loader import load_article_176_3

# In-memory cache (load once)
_TABLE = None


def _table() -> dict:
    global _TABLE
    if _TABLE is None:
        _TABLE = load_article_176_3()
    return _TABLE


def _resolve_rating(rating: str) -> str:
    table = _table()
    if rating in table["ratings"]:
        return rating
    mapping = table.get("notch_mapping", {})
    if rating in mapping:
        return mapping[rating]
    raise KeyError(f"Rating {rating!r} not found in Article 176(3) table or notch mapping")


def s2_spread_shock(rating: str, maturity_years: float) -> float:
    """Return spread shock in % (haircut to loan exposure) per Article 176(3)."""
    row = _table()["ratings"][_resolve_rating(rating)]
    bands = sorted(row.keys())  # [3, 5, 7, 10, 15, 20]
    if maturity_years <= bands[0]:
        return float(row[bands[0]])
    if maturity_years >= bands[-1]:
        return float(row[bands[-1]])
    for i in range(len(bands) - 1):
        if bands[i] <= maturity_years <= bands[i + 1]:
            x0, x1 = bands[i], bands[i + 1]
            y0, y1 = row[x0], row[x1]
            return float(y0 + (y1 - y0) * (maturity_years - x0) / (x1 - x0))
    raise RuntimeError("unreachable")


def s2_shock_effective(
    rating: str,
    maturity_years: float,
    qii_eligible: bool = False,
    qii_reduction_pct: float = 0.0,
) -> float:
    shock = s2_spread_shock(rating, maturity_years)
    if qii_eligible:
        shock = shock * (1 - qii_reduction_pct / 100)
    return shock


def return_on_capital_s2(yield_net_pct: float, s2_shock_pct: float) -> float:
    """RoC S2 = yield_net / S2 capital intensity. Both inputs in %, output in %.

    Conventional reading: RoC S2 expresses the net spread per unit of S2 capital,
    so a 9 % yield net on a 30 % S2 shock gives a 30 % return on S2 capital."""
    if s2_shock_pct <= 0:
        return float("inf")
    return (yield_net_pct / s2_shock_pct) * 100
