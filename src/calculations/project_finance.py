"""Infra Debt — year-by-year cashflow engine + DSCR/LLCR/PLCR + stress tests.

Implements the model spelled out in CAPITAL_LENS_SPEC.md §5.B.
Conventions
-----------
- Year index t = 1..project_life_years (year 0 = COD, ignored for cashflows).
- All amounts in the deal's notional currency unit (M).
- Revenue model: revenue_t = capacity_mw * 8760 * capacity_factor% * price_t / 1_000_000.
- Price evolution depends on offtake_type + indexation, with CPI default 2 %.
- Tax: simplified 25 % on operating profit after straight-line depreciation, floor at 0.
- Debt service: Bullet => interest on constant balance + principal at maturity.
                Amortizing sculpté => principal sized so DSCR_t ≈ target (1.40 default),
                clipped so cumulative principal ≤ debt_amount and last year clears.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import numpy as np
import pandas as pd

SCULPT_TARGET_DSCR = 1.40
HOURS_PER_YEAR = 8760
TAX_RATE = 0.25
DISCOUNT_RATE_DEFAULT = 0.05  # used for LLCR/PLCR present values


@dataclass
class InfraMetrics:
    cashflows: pd.DataFrame      # year-indexed table (base case)
    cashflows_p90: pd.DataFrame  # production -15 % stress
    cashflows_merch: pd.DataFrame  # merchant -25 % stress (= base if not merchant)
    cashflows_combined: pd.DataFrame  # P90 + merchant
    min_dscr: float
    avg_dscr: float
    min_dscr_p90: float
    min_dscr_merch: float
    min_dscr_combined: float
    llcr: float
    plcr: float
    tail_years: float
    all_in_yield_pct: float
    el_annual_pct: float
    yield_net_pct: float


def _price_evolution(offtake_type: str, strike: float, indexation: str, cpi_pct: float, years: int) -> np.ndarray:
    cpi = cpi_pct / 100
    t = np.arange(1, years + 1)
    if offtake_type == "PPA fix":
        return np.full(years, strike, dtype=float)
    if offtake_type == "PPA indexed":
        return strike * (1 + cpi) ** t
    if offtake_type == "CfD":
        # indexation typically CPI (UK CfD framework)
        rate = cpi if indexation in ("CPI", "Formula") else 0.0
        return strike * (1 + rate) ** t
    if offtake_type == "Take-or-pay":
        # contractual escalator if indexation specified, else fixed
        rate = cpi if indexation in ("CPI", "Formula") else 0.0
        return strike * (1 + rate) ** t
    if offtake_type == "Availability payment":
        return np.full(years, strike, dtype=float)
    if offtake_type == "Merchant":
        # merchant exposure — naive flat then risk applied via stress
        return np.full(years, strike, dtype=float)
    return np.full(years, strike, dtype=float)


def _build_base_cashflows(
    *,
    capacity_mw: float,
    capacity_factor_pct: float,
    offtake_type: str,
    strike_price: float,
    indexation: str,
    cpi_pct: float,
    opex_annual: float,
    heavy_maint_frequency: int,
    heavy_maint_amount: float,
    capex_total: float,
    project_life: int,
) -> pd.DataFrame:
    years = np.arange(1, project_life + 1)
    cpi = cpi_pct / 100
    price = _price_evolution(offtake_type, strike_price, indexation, cpi_pct, project_life)
    revenue = capacity_mw * HOURS_PER_YEAR * (capacity_factor_pct / 100) * price / 1_000_000
    opex = opex_annual * (1 + cpi) ** years
    if heavy_maint_frequency > 0:
        heavy_maint = np.where(years % heavy_maint_frequency == 0, heavy_maint_amount, 0.0)
    else:
        heavy_maint = np.zeros(project_life)
    depreciation = np.full(project_life, capex_total / project_life)
    op_profit = revenue - opex - heavy_maint - depreciation
    tax = np.maximum(0.0, TAX_RATE * op_profit)
    op_cf = revenue - opex - heavy_maint - tax
    return pd.DataFrame(
        {
            "year": years,
            "revenue": revenue,
            "opex": opex,
            "heavy_maint": heavy_maint,
            "depreciation": depreciation,
            "op_profit": op_profit,
            "tax": tax,
            "op_cf": op_cf,
            "cfads": op_cf,
        }
    ).set_index("year")


def _sculpt_principal(
    cfads: np.ndarray,
    debt_amount: float,
    coupon_rate: float,
    debt_maturity: int,
    target_dscr: float = SCULPT_TARGET_DSCR,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return (principal_t, interest_t, balance_t) for years 1..debt_maturity."""
    principal = np.zeros(debt_maturity)
    interest = np.zeros(debt_maturity)
    balance = np.zeros(debt_maturity)
    bal = debt_amount
    for i in range(debt_maturity):
        bal_start = bal
        int_t = bal_start * coupon_rate
        # principal sized so CFADS_t / (principal_t + interest_t) = target_dscr
        max_debt_service = cfads[i] / target_dscr
        princ_t = max(0.0, max_debt_service - int_t)
        princ_t = min(princ_t, bal_start)  # cannot prepay more than outstanding
        # On final year force full repayment
        if i == debt_maturity - 1:
            princ_t = bal_start
        principal[i] = princ_t
        interest[i] = int_t
        bal -= princ_t
        balance[i] = bal
    # If sculpting didn't fully pay down (under-stressed CFADS) — final year already forced.
    return principal, interest, balance


def _bullet_schedule(
    debt_amount: float, coupon_rate: float, debt_maturity: int
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    principal = np.zeros(debt_maturity)
    interest = np.full(debt_maturity, debt_amount * coupon_rate)
    balance = np.full(debt_maturity, debt_amount)
    principal[-1] = debt_amount
    balance[-1] = 0
    return principal, interest, balance


def _apply_debt_schedule(
    cfads_table: pd.DataFrame,
    *,
    debt_amount: float,
    debt_maturity: int,
    debt_profile: str,
    coupon_rate: float,
) -> pd.DataFrame:
    df = cfads_table.copy()
    project_life = len(df)
    principal = np.zeros(project_life)
    interest = np.zeros(project_life)
    balance = np.zeros(project_life)

    cfads_arr = df["cfads"].to_numpy()[:debt_maturity]
    if debt_profile == "Bullet":
        p, i, b = _bullet_schedule(debt_amount, coupon_rate, debt_maturity)
    else:
        p, i, b = _sculpt_principal(cfads_arr, debt_amount, coupon_rate, debt_maturity)
    principal[:debt_maturity] = p
    interest[:debt_maturity] = i
    balance[:debt_maturity] = b

    debt_service = principal + interest
    with np.errstate(divide="ignore", invalid="ignore"):
        dscr = np.where(debt_service > 0, df["cfads"].to_numpy() / debt_service, np.nan)
    df["debt_principal"] = principal
    df["debt_interest"] = interest
    df["debt_balance"] = balance
    df["debt_service"] = debt_service
    df["dscr"] = dscr
    return df


def _compute_llcr_plcr(
    df: pd.DataFrame, debt_maturity: int, project_life: int, debt_amount: float, discount_rate: float
) -> tuple[float, float]:
    years = df.index.to_numpy()
    discount = (1 + discount_rate) ** years
    cfads = df["cfads"].to_numpy()
    pv_loan = float(np.sum(cfads[:debt_maturity] / discount[:debt_maturity]))
    pv_project = float(np.sum(cfads[:project_life] / discount[:project_life]))
    llcr = pv_loan / debt_amount if debt_amount > 0 else float("inf")
    plcr = pv_project / debt_amount if debt_amount > 0 else float("inf")
    return llcr, plcr


def compute_infra_metrics(
    *,
    capacity_mw: float,
    capacity_factor_pct: float,
    offtake_type: str,
    strike_price: float,
    indexation: str,
    cpi_pct: float = 2.0,
    opex_annual: float,
    heavy_maint_frequency: int,
    heavy_maint_amount: float,
    capex_total: float,
    project_life: int,
    debt_amount: float,
    debt_maturity: int,
    debt_profile: str,
    base_rate_level: float,
    margin_bps: float,
    pd_annual: float,
    lgd: float,
    discount_rate: float = DISCOUNT_RATE_DEFAULT,
) -> InfraMetrics:
    coupon_rate = base_rate_level / 100 + margin_bps / 10_000
    base = _build_base_cashflows(
        capacity_mw=capacity_mw,
        capacity_factor_pct=capacity_factor_pct,
        offtake_type=offtake_type,
        strike_price=strike_price,
        indexation=indexation,
        cpi_pct=cpi_pct,
        opex_annual=opex_annual,
        heavy_maint_frequency=heavy_maint_frequency,
        heavy_maint_amount=heavy_maint_amount,
        capex_total=capex_total,
        project_life=project_life,
    )
    base = _apply_debt_schedule(
        base,
        debt_amount=debt_amount,
        debt_maturity=debt_maturity,
        debt_profile=debt_profile,
        coupon_rate=coupon_rate,
    )

    # Stress 1 — production -15% (P90 yield)
    p90 = base.copy()
    p90["revenue"] = p90["revenue"] * 0.85
    # recompute op_profit/tax/cfads under stress; debt schedule unchanged
    p90["op_profit"] = p90["revenue"] - p90["opex"] - p90["heavy_maint"] - p90["depreciation"]
    p90["tax"] = np.maximum(0.0, TAX_RATE * p90["op_profit"])
    p90["cfads"] = p90["revenue"] - p90["opex"] - p90["heavy_maint"] - p90["tax"]
    with np.errstate(divide="ignore", invalid="ignore"):
        p90["dscr"] = np.where(p90["debt_service"] > 0, p90["cfads"] / p90["debt_service"], np.nan)

    # Stress 2 — merchant -25%. Only meaningful if Merchant offtake.
    merch = base.copy()
    if offtake_type == "Merchant":
        merch["revenue"] = merch["revenue"] * 0.75
        merch["op_profit"] = merch["revenue"] - merch["opex"] - merch["heavy_maint"] - merch["depreciation"]
        merch["tax"] = np.maximum(0.0, TAX_RATE * merch["op_profit"])
        merch["cfads"] = merch["revenue"] - merch["opex"] - merch["heavy_maint"] - merch["tax"]
        with np.errstate(divide="ignore", invalid="ignore"):
            merch["dscr"] = np.where(merch["debt_service"] > 0, merch["cfads"] / merch["debt_service"], np.nan)

    # Stress 3 — combined (P90 + merchant)
    combined = base.copy()
    factor = 0.85 * (0.75 if offtake_type == "Merchant" else 1.0)
    combined["revenue"] = combined["revenue"] * factor
    combined["op_profit"] = (
        combined["revenue"] - combined["opex"] - combined["heavy_maint"] - combined["depreciation"]
    )
    combined["tax"] = np.maximum(0.0, TAX_RATE * combined["op_profit"])
    combined["cfads"] = combined["revenue"] - combined["opex"] - combined["heavy_maint"] - combined["tax"]
    with np.errstate(divide="ignore", invalid="ignore"):
        combined["dscr"] = np.where(
            combined["debt_service"] > 0, combined["cfads"] / combined["debt_service"], np.nan
        )

    def _min_dscr(df: pd.DataFrame) -> float:
        s = df.loc[df.index <= debt_maturity, "dscr"].replace([np.inf, -np.inf], np.nan).dropna()
        return float(s.min()) if not s.empty else float("nan")

    min_dscr = _min_dscr(base)
    min_dscr_p90 = _min_dscr(p90)
    min_dscr_merch = _min_dscr(merch)
    min_dscr_combined = _min_dscr(combined)

    dscr_base = base.loc[base.index <= debt_maturity, "dscr"].replace([np.inf, -np.inf], np.nan).dropna()
    avg_dscr = float(dscr_base.mean()) if not dscr_base.empty else float("nan")

    llcr, plcr = _compute_llcr_plcr(base, debt_maturity, project_life, debt_amount, discount_rate)
    tail_years = float(project_life - debt_maturity)

    # All-in yield / EL / yield net for infra debt
    all_in_yield_pct = base_rate_level + margin_bps / 100
    el_annual_pct = pd_annual * lgd / 100
    yield_net_pct = all_in_yield_pct - el_annual_pct

    return InfraMetrics(
        cashflows=base,
        cashflows_p90=p90,
        cashflows_merch=merch,
        cashflows_combined=combined,
        min_dscr=min_dscr,
        avg_dscr=avg_dscr,
        min_dscr_p90=min_dscr_p90,
        min_dscr_merch=min_dscr_merch,
        min_dscr_combined=min_dscr_combined,
        llcr=llcr,
        plcr=plcr,
        tail_years=tail_years,
        all_in_yield_pct=all_in_yield_pct,
        el_annual_pct=el_annual_pct,
        yield_net_pct=yield_net_pct,
    )


def compute_infra_metrics_from_model(deal) -> InfraMetrics:
    return compute_infra_metrics(
        capacity_mw=deal.offtake.capacity_mw,
        capacity_factor_pct=deal.offtake.capacity_factor,
        offtake_type=deal.offtake.offtake_type,
        strike_price=deal.offtake.strike_price_eur_mwh,
        indexation=deal.offtake.indexation,
        cpi_pct=deal.offtake.cpi_pct,
        opex_annual=deal.project.opex_annual_eur_m,
        heavy_maint_frequency=deal.project.heavy_maint_frequency_years,
        heavy_maint_amount=deal.project.heavy_maint_amount_eur_m,
        capex_total=deal.project.capex_total_eur_m,
        project_life=deal.project.project_life_years,
        debt_amount=deal.debt.debt_amount_eur_m,
        debt_maturity=deal.debt.debt_maturity_years,
        debt_profile=deal.debt.debt_profile,
        base_rate_level=deal.debt.debt_base_rate_level,
        margin_bps=deal.debt.debt_margin_bps,
        pd_annual=deal.risk.pd_annual,
        lgd=deal.risk.lgd,
    )
