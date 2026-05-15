"""Direct Lending credit metrics + EL + stress tests.

All ratios follow the formulas spelled out in CAPITAL_LENS_SPEC.md §5.A.
Inputs are loose floats so the engine works on Pydantic models or dicts indifferently.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class DLMetrics:
    # Base ratios
    net_leverage: float
    senior_leverage: float
    cash_interest: float
    interest_coverage: float
    mandatory_amort: float
    fccr: float
    debt_yield: float
    cash_conversion: float
    # Pricing
    oid_per_year: float
    upfront_per_year: float
    floor_adj: float
    all_in_yield: float
    # Risk
    el_annual: float
    yield_net: float
    # Headroom
    headroom_net_lev: float
    # Stress 1 — EBITDA -20%
    ebitda_stressed: float
    net_lev_stressed: float
    ic_stressed: float
    fccr_stressed: float
    # Stress 2 — +200 bps
    cash_interest_stressed: float
    ic_rate_stressed: float
    # Stress 3 — combined
    ic_combined: float
    fccr_combined: float


def compute_dl_metrics(
    *,
    ebitda: float,
    loan_amount: float,
    rcf_amount: float = 0.0,
    base_rate_level: float,
    margin_bps: float,
    oid_pct: float = 0.0,
    upfront_pct: float = 0.0,
    floor_pct: float = 0.0,
    maturity_years: float,
    profile: str = "Bullet",
    capex_maintenance: float = 0.0,
    fcf_conversion: float = 100.0,
    pd_annual: float,
    lgd: float,
    cov_net_lev_cap: float,
) -> DLMetrics:
    if ebitda <= 0 or loan_amount <= 0 or maturity_years <= 0:
        raise ValueError("ebitda, loan_amount, maturity_years must be > 0")

    # Leverage
    net_leverage = loan_amount / ebitda
    senior_leverage = (loan_amount + rcf_amount) / ebitda

    # Cash interest (annual) = loan * (rate + margin)
    coupon_rate = base_rate_level / 100 + margin_bps / 10_000
    cash_interest = loan_amount * coupon_rate

    interest_coverage = ebitda / cash_interest if cash_interest > 0 else float("inf")

    # Mandatory amortization
    if profile == "Bullet" or profile == "DDTL":
        mandatory_amort = 0.0
    else:
        mandatory_amort = loan_amount / maturity_years

    fccr_denom = cash_interest + mandatory_amort
    fccr = (ebitda - capex_maintenance) / fccr_denom if fccr_denom > 0 else float("inf")

    debt_yield = ebitda / loan_amount * 100  # %
    cash_conversion = fcf_conversion  # already %

    # Pricing
    oid_per_year = oid_pct / maturity_years
    upfront_per_year = upfront_pct / maturity_years
    floor_adj = max(0.0, floor_pct - base_rate_level)
    all_in_yield = (
        base_rate_level + margin_bps / 100 + oid_per_year + upfront_per_year + floor_adj
    )

    # Risk
    el_annual = pd_annual * lgd / 100  # both inputs already %
    yield_net = all_in_yield - el_annual

    headroom_net_lev = (cov_net_lev_cap / net_leverage) - 1 if net_leverage > 0 else float("inf")

    # Stress 1 : EBITDA -20%
    ebitda_stressed = ebitda * 0.80
    net_lev_stressed = loan_amount / ebitda_stressed
    ic_stressed = ebitda_stressed / cash_interest if cash_interest > 0 else float("inf")
    fccr_stressed = (
        (ebitda_stressed - capex_maintenance) / fccr_denom if fccr_denom > 0 else float("inf")
    )

    # Stress 2 : +200 bps base rate
    cash_interest_stressed = loan_amount * (coupon_rate + 0.02)
    ic_rate_stressed = ebitda / cash_interest_stressed if cash_interest_stressed > 0 else float("inf")

    # Stress 3 : combined (EBITDA -20% AND +200 bps)
    fccr_combined_denom = cash_interest_stressed + mandatory_amort
    ic_combined = (
        ebitda_stressed / cash_interest_stressed
        if cash_interest_stressed > 0
        else float("inf")
    )
    fccr_combined = (
        (ebitda_stressed - capex_maintenance) / fccr_combined_denom
        if fccr_combined_denom > 0
        else float("inf")
    )

    return DLMetrics(
        net_leverage=net_leverage,
        senior_leverage=senior_leverage,
        cash_interest=cash_interest,
        interest_coverage=interest_coverage,
        mandatory_amort=mandatory_amort,
        fccr=fccr,
        debt_yield=debt_yield,
        cash_conversion=cash_conversion,
        oid_per_year=oid_per_year,
        upfront_per_year=upfront_per_year,
        floor_adj=floor_adj,
        all_in_yield=all_in_yield,
        el_annual=el_annual,
        yield_net=yield_net,
        headroom_net_lev=headroom_net_lev,
        ebitda_stressed=ebitda_stressed,
        net_lev_stressed=net_lev_stressed,
        ic_stressed=ic_stressed,
        fccr_stressed=fccr_stressed,
        cash_interest_stressed=cash_interest_stressed,
        ic_rate_stressed=ic_rate_stressed,
        ic_combined=ic_combined,
        fccr_combined=fccr_combined,
    )


def compute_dl_metrics_from_model(deal) -> DLMetrics:
    """Convenience wrapper that pulls fields from a DLDeal instance."""
    return compute_dl_metrics(
        ebitda=deal.borrower.ebitda,
        loan_amount=deal.loan.loan_amount,
        rcf_amount=deal.loan.rcf_amount,
        base_rate_level=deal.loan.base_rate_level,
        margin_bps=deal.loan.margin_bps,
        oid_pct=deal.loan.oid_pct,
        upfront_pct=deal.loan.upfront_pct,
        floor_pct=deal.loan.floor_pct,
        maturity_years=deal.loan.maturity_years,
        profile=deal.loan.profile,
        capex_maintenance=deal.borrower.capex_maintenance,
        fcf_conversion=deal.borrower.fcf_conversion,
        pd_annual=deal.risk.pd_annual,
        lgd=deal.risk.lgd,
        cov_net_lev_cap=deal.covenants.cov_net_lev_cap,
    )
