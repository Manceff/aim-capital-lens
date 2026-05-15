"""Display formatting helpers (M€, %, ×)."""

from __future__ import annotations


def fmt_money(value: float, currency: str = "EUR", decimals: int = 1) -> str:
    symbol = {"EUR": "€", "USD": "$", "GBP": "£"}.get(currency, currency + " ")
    return f"{symbol}{value:,.{decimals}f}M"


def fmt_pct(value: float, decimals: int = 1) -> str:
    return f"{value:,.{decimals}f}%"


def fmt_x(value: float, decimals: int = 2) -> str:
    return f"{value:,.{decimals}f}×"


def fmt_bps(value: float) -> str:
    return f"{value:.0f} bps"


def fmt_years(value: float, decimals: int = 0) -> str:
    return f"{value:,.{decimals}f}y"
