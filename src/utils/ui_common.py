"""Streamlit UI helpers shared across pages — ALM banner, palette, footer."""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

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
                <span><b>Duration target</b> {alm.alm_duration_min_years:.0f}–{alm.alm_duration_max_years:.0f}y
                    <small>life liabilities</small></span>
                <span><b>5y liquidity floor</b> {alm.alm_liquidity_floor_5y_pct:.0f}%
                    <small>balance sheet</small></span>
                <span><b>S2 ratio target</b> ≥ {alm.s2_ratio_minimum_pct:.0f}%
                    <small>Comex Allianz Vie</small></span>
                <span><b>Owner</b> {alm.mandate_owner}</span>
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
        <b>AIM Capital Lens</b> — projet personnel post-entretien. Aucune donnée propriétaire Allianz.
        Calculs S2 basés sur Article 176(3) Règlement délégué (UE) 2015/35 (table Milliman 2019) et régime QII Articles 164a / 164b.
        Author Mancef Ferrah · M2 Finance Tech & Data, Université Paris 1.
        </div>
        """,
        unsafe_allow_html=True,
    )


def verdict_badge_html(status: str) -> str:
    cls = {
        "PASS": "verdict-pass",
        "PROCEED": "verdict-pass",
        "CONDITIONS": "verdict-cond",
        "REJECT": "verdict-reject",
    }.get(status, "verdict-cond")
    icon = {"PASS": "✅", "PROCEED": "✅", "CONDITIONS": "⚠️", "REJECT": "❌"}.get(status, "•")
    return f'<span class="verdict-badge {cls}">{icon} {status}</span>'


def kpi_tile(label: str, value: str, best: bool = False) -> str:
    cls = "kpi-tile kpi-best" if best else "kpi-tile"
    return f"""
    <div class="{cls}">
        <div class="kpi-label">{label}</div>
        <div class="kpi-value">{value}</div>
    </div>
    """


def section_head(label: str) -> None:
    st.markdown(f'<div class="section-head">{label}</div>', unsafe_allow_html=True)


def safe_fmt(value: float, fmt: str = "{:.2f}") -> str:
    if value is None or (isinstance(value, float) and (math.isinf(value) or math.isnan(value))):
        return "—"
    return fmt.format(value)
