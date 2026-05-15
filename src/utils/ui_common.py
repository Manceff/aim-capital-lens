"""Streamlit UI helpers — institutional editorial style. No emoji."""

from __future__ import annotations

import json
import math
from pathlib import Path

import streamlit as st

from src.models.alm_mandate import ALMMandate
from src.utils.presets_loader import load_alm_mandate

ROOT = Path(__file__).resolve().parents[2]
PALETTE_PATH = ROOT / "assets" / "allianz_palette.json"
CSS_PATH = ROOT / "assets" / "style.css"


@st.cache_data
def load_palette() -> dict[str, str]:
    return json.loads(PALETTE_PATH.read_text())


def inject_css() -> None:
    """Inject custom CSS once per page."""
    css = CSS_PATH.read_text()
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)


def render_alm_banner(alm: ALMMandate | None = None) -> ALMMandate:
    """Render the read-only ALM Mandate Constraints banner on top of every page."""
    if alm is None:
        alm = load_alm_mandate()
    st.markdown(
        f"""
        <div class="alm-banner">
            <div class="alm-title">{alm.display_label}</div>
            <div class="alm-row">
                <span><small>Duration target</small><b>{alm.alm_duration_min_years:.0f}–{alm.alm_duration_max_years:.0f}y</b><small>life liabilities</small></span>
                <span><small>5y liquidity floor</small><b>{alm.alm_liquidity_floor_5y_pct:.0f}%</b><small>balance sheet</small></span>
                <span><small>S2 ratio target</small><b>≥ {alm.s2_ratio_minimum_pct:.0f}%</b><small>Comex Allianz Vie</small></span>
                <span><small>Owner</small><b>{alm.mandate_owner}</b></span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    return alm


def render_footer() -> None:
    st.markdown(
        """
        <div class="footer-disclaimer">
        <b>AIM Capital Lens</b> — personal post-interview project. No proprietary Allianz data.
        Solvency II calculations based on Article 176(3) of Règlement délégué (UE) 2015/35
        (Milliman 2019 calibration) and the QII regime under Articles 164a / 164b.
        Author Mancef Ferrah — M2 Finance Tech &amp; Data, Université Paris 1.
        </div>
        """,
        unsafe_allow_html=True,
    )


def verdict_pill_html(status: str) -> str:
    """Uppercase status pill, no emoji."""
    cls = {
        "PASS": "verdict-pass",
        "PROCEED": "verdict-pass",
        "CONDITIONS": "verdict-cond",
        "REJECT": "verdict-reject",
    }.get(status, "verdict-cond")
    return f'<span class="verdict-pill {cls}">{status}</span>'


# Back-compat alias for any caller still using the old name
verdict_badge_html = verdict_pill_html


def kpi_row(label: str, value: str, *, best: bool = False) -> str:
    """Flat KPI row — label left, value right, hairline underneath. No left-stripe."""
    cls = "kpi-row kpi-best" if best else "kpi-row"
    return f'<div class="{cls}"><div class="kpi-label">{label}</div><div class="kpi-value">{value}</div></div>'


def kpi_tile(label: str, value: str, best: bool = False) -> str:
    """Back-compat shim that now renders the flat editorial row."""
    return kpi_row(label, value, best=best)


def pillar_line(name: str, status: str, reason: str | None) -> str:
    return (
        f'<div class="pillar-line">'
        f'  <div class="pillar-name">{name}</div>'
        f'  {verdict_pill_html(status)}'
        f'  <div class="pillar-reason">{reason or ""}</div>'
        f'</div>'
    )


def section_head(label: str) -> None:
    st.markdown(f'<div class="section-head">{label}</div>', unsafe_allow_html=True)


def safe_fmt(value: float, fmt: str = "{:.2f}") -> str:
    if value is None or (isinstance(value, float) and (math.isinf(value) or math.isnan(value))):
        return "—"
    return fmt.format(value)
