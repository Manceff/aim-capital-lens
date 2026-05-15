"""ALM Mandate Constraints — read-only inputs set by Risk & ALM Committee."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ALMMandate(BaseModel):
    alm_duration_min_years: float = Field(ge=0)
    alm_duration_max_years: float = Field(ge=0)
    alm_liquidity_floor_5y_pct: float = Field(ge=0, le=100)
    s2_ratio_minimum_pct: float = Field(ge=0)
    mandate_owner: str = "Risk & ALM Committee — Allianz Vie"
    display_label: str = (
        "ALM Mandate Constraints — set by Risk & ALM Committee "
        "· Not editable in operational view"
    )
