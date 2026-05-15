"""Pydantic schema for a Direct Lending deal."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

Sector = Literal["SaaS", "Healthcare", "Industrials", "Consumer", "TMT", "Other"]
SponsorTier = Literal["Top-tier", "Mid-tier", "New"]
TrancheType = Literal["RCF", "1L Term Loan", "Unitranche", "2L", "Mezzanine"]
BaseRateType = Literal["EURIBOR 3M", "SOFR 3M", "SONIA", "ESTR"]
Profile = Literal["Bullet", "Amortizing", "DDTL"]
Rating = Literal[
    "AAA", "AA+", "AA", "AA-", "A+", "A", "A-",
    "BBB+", "BBB", "BBB-", "BB+", "BB", "BB-",
    "B+", "B", "B-", "CCC",
]


class DLBorrower(BaseModel):
    name: str
    sector: Sector
    ebitda: float = Field(gt=0)
    ebitda_growth: float = 0
    ebitda_margin: float = Field(ge=0, le=100)
    capex_maintenance: float = Field(ge=0)
    fcf_conversion: float = Field(ge=0, le=100)
    arr_share: float = Field(ge=0, le=100, default=0)
    top10_clients: float = Field(ge=0, le=100, default=0)
    sponsor_name: str = ""
    sponsor_tier: SponsorTier = "Mid-tier"


class DLLoan(BaseModel):
    loan_amount: float = Field(gt=0)
    tranche_type: TrancheType
    base_rate_type: BaseRateType = "EURIBOR 3M"
    base_rate_level: float = Field(ge=0)
    margin_bps: float = Field(ge=0)
    oid_pct: float = Field(ge=0, default=0)
    upfront_pct: float = Field(ge=0, default=0)
    floor_pct: float = Field(ge=0, default=0)
    maturity_years: float = Field(gt=0)
    profile: Profile = "Bullet"
    rcf_amount: float = Field(ge=0, default=0)


class DLCovenants(BaseModel):
    cov_net_lev_cap: float = Field(gt=0)
    cov_ic_min: float = Field(gt=0)
    cov_fccr_min: float = Field(gt=0)
    cov_lite: bool = False
    dividend_basket_eur_m: float = Field(ge=0, default=0)


class DLRisk(BaseModel):
    rating_estim: Rating
    pd_annual: float = Field(ge=0, le=100)
    lgd: float = Field(ge=0, le=100)


class DLDeal(BaseModel):
    id: str
    type: Literal["DL"] = "DL"
    label: str
    currency: str = "EUR"
    borrower: DLBorrower
    loan: DLLoan
    covenants: DLCovenants
    risk: DLRisk
