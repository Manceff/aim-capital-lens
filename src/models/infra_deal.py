"""Pydantic schema for an Infrastructure Debt (Project Finance) deal."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

InfraSector = Literal[
    "Renewable solar",
    "Renewable wind onshore",
    "Renewable wind offshore",
    "Renewable hydro",
    "Data center",
    "Transport",
    "Social",
    "Utility",
]
OfftakeType = Literal[
    "PPA fix",
    "PPA indexed",
    "CfD",
    "Take-or-pay",
    "Availability payment",
    "Merchant",
]
Indexation = Literal["Fixed", "CPI", "Formula"]
DebtProfile = Literal["Amortizing sculpté", "Bullet"]
BaseRateType = Literal["EURIBOR 3M", "SOFR 3M", "SONIA", "ESTR"]


class InfraSPV(BaseModel):
    project_name: str
    sector: InfraSector
    country: str = Field(min_length=2, max_length=2)
    sponsor: str = ""


class InfraOfftake(BaseModel):
    offtake_type: OfftakeType
    strike_price_eur_mwh: float = Field(ge=0)
    indexation: Indexation = "Fixed"
    cpi_pct: float = Field(ge=0, default=2.0)
    contract_duration_years: float = Field(gt=0)
    capacity_mw: float = Field(ge=0)
    capacity_factor: float = Field(ge=0, le=100)


class InfraProject(BaseModel):
    capex_total_eur_m: float = Field(gt=0)
    opex_annual_eur_m: float = Field(ge=0)
    heavy_maint_frequency_years: int = Field(ge=0, default=0)
    heavy_maint_amount_eur_m: float = Field(ge=0, default=0)
    cod_year: int = Field(ge=2000)
    project_life_years: int = Field(gt=0)


class InfraDebt(BaseModel):
    debt_amount_eur_m: float = Field(gt=0)
    debt_maturity_years: int = Field(gt=0)
    debt_profile: DebtProfile = "Amortizing sculpté"
    debt_base_rate_type: BaseRateType = "EURIBOR 3M"
    debt_base_rate_level: float = Field(ge=0)
    debt_margin_bps: float = Field(ge=0)
    dsra_months: float = Field(ge=0, default=6)


class InfraRisk(BaseModel):
    rating_estim: str
    pd_annual: float = Field(ge=0, le=100)
    lgd: float = Field(ge=0, le=100)
    qii_eligible: bool = False
    qii_spread_reduction: float = Field(ge=0, le=100, default=0)


class InfraDeal(BaseModel):
    id: str
    type: Literal["INFRA"] = "INFRA"
    label: str
    currency: str = "EUR"
    spv: InfraSPV
    offtake: InfraOfftake
    project: InfraProject
    debt: InfraDebt
    risk: InfraRisk
