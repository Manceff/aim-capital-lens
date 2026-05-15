"""PowerPoint export — 7 slides, Allianz palette."""

from __future__ import annotations

import datetime as _dt
from io import BytesIO

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.util import Emu, Inches, Pt

from src.calculations.dl_metrics import compute_dl_metrics_from_model
from src.calculations.project_finance import compute_infra_metrics_from_model
from src.calculations.s2_capital import return_on_capital_s2, s2_shock_effective
from src.calculations.verdict_engine import verdict_dl, verdict_infra
from src.models.alm_mandate import ALMMandate
from src.models.dl_deal import DLDeal
from src.models.infra_deal import InfraDeal
from src.utils.presets_loader import load_alm_mandate, load_preset_deals

ALLIANZ_PRIMARY = RGBColor(0x00, 0x37, 0x81)
ALLIANZ_PRIMARY_DARK = RGBColor(0x00, 0x25, 0x58)
ALLIANZ_GOLD = RGBColor(0xB6, 0x8C, 0x1E)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
TEXT = RGBColor(0x1A, 0x1A, 0x1A)
GREEN = RGBColor(0x27, 0xAE, 0x60)
RED = RGBColor(0xC0, 0x39, 0x2B)
ORANGE = RGBColor(0xE6, 0x7E, 0x22)

SLIDE_W = Inches(13.333)
SLIDE_H = Inches(7.5)


def _add_top_band(slide) -> None:
    band = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, SLIDE_W, Inches(0.18))
    band.line.fill.background()
    band.fill.solid()
    band.fill.fore_color.rgb = ALLIANZ_PRIMARY


def _add_text(slide, left, top, width, height, text, *, size=14, bold=False, color=TEXT, align=None):
    tb = slide.shapes.add_textbox(left, top, width, height)
    tf = tb.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    if align is not None:
        p.alignment = align
    run = p.add_run()
    run.text = text
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.color.rgb = color
    return tb


def _add_kpi_tile(slide, left, top, width, height, label, value, *, gold=False):
    rect = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, left, top, width, height)
    rect.line.color.rgb = ALLIANZ_PRIMARY
    rect.line.width = Pt(0.75)
    rect.fill.solid()
    rect.fill.fore_color.rgb = WHITE
    # Left accent bar
    bar = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, left, top, Emu(45720), height)
    bar.line.fill.background()
    bar.fill.solid()
    bar.fill.fore_color.rgb = ALLIANZ_GOLD if gold else ALLIANZ_PRIMARY
    tf = rect.text_frame
    tf.margin_left = Inches(0.18)
    tf.margin_top = Inches(0.12)
    p_label = tf.paragraphs[0]
    r_label = p_label.add_run()
    r_label.text = label.upper()
    r_label.font.size = Pt(9)
    r_label.font.color.rgb = RGBColor(0x59, 0x59, 0x59)
    p_value = tf.add_paragraph()
    r_value = p_value.add_run()
    r_value.text = value
    r_value.font.size = Pt(22)
    r_value.font.bold = True
    r_value.font.color.rgb = ALLIANZ_PRIMARY


def _verdict_color(status: str) -> RGBColor:
    return {"PASS": GREEN, "PROCEED": GREEN, "CONDITIONS": ORANGE, "REJECT": RED}.get(status, ORANGE)


def _add_verdict_pill(slide, left, top, status: str):
    txt = f"   {status}   "
    pill = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, left, top, Inches(2.0), Inches(0.45))
    pill.fill.solid()
    pill.fill.fore_color.rgb = _verdict_color(status)
    pill.line.fill.background()
    tf = pill.text_frame
    p = tf.paragraphs[0]
    p.alignment = 2  # center
    r = p.add_run()
    r.text = txt
    r.font.size = Pt(14)
    r.font.bold = True
    r.font.color.rgb = WHITE


def _slide_cover(prs, dl_label, infra_label):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _add_top_band(slide)
    _add_text(slide, Inches(0.7), Inches(2.0), Inches(12), Inches(1.2),
              "AIM Capital Lens", size=44, bold=True, color=ALLIANZ_PRIMARY)
    _add_text(slide, Inches(0.7), Inches(3.1), Inches(12), Inches(0.8),
              f"Cross-class private debt comparator — {dl_label} × {infra_label}",
              size=20, color=TEXT)
    date_str = _dt.date.today().strftime("%d %B %Y")
    _add_text(slide, Inches(0.7), Inches(5.6), Inches(12), Inches(0.4),
              f"Date: {date_str}", size=13, color=TEXT)
    _add_text(slide, Inches(0.7), Inches(6.0), Inches(12), Inches(0.4),
              "Author: Mancef Ferrah · M2 Finance Tech & Data · Université Paris 1",
              size=13, color=TEXT)
    _add_text(slide, Inches(0.7), Inches(6.95), Inches(12), Inches(0.4),
              "Disclaimer — projet personnel post-entretien. Aucune donnée propriétaire Allianz.",
              size=10, color=RGBColor(0x59, 0x59, 0x59))


def _slide_dl_summary(prs, dl: DLDeal, alm: ALMMandate):
    m = compute_dl_metrics_from_model(dl)
    shock = s2_shock_effective(dl.risk.rating_estim, dl.loan.maturity_years)
    roc = return_on_capital_s2(m.yield_net, shock)
    v = verdict_dl(m, roc, dl.loan.maturity_years, alm)

    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _add_top_band(slide)
    _add_text(slide, Inches(0.7), Inches(0.4), Inches(12), Inches(0.6),
              f"Deal Summary — {dl.label}", size=26, bold=True, color=ALLIANZ_PRIMARY)
    _add_text(slide, Inches(0.7), Inches(1.0), Inches(12), Inches(0.4),
              f"{dl.loan.tranche_type} · {dl.borrower.sector} · "
              f"{dl.loan.base_rate_type} + {int(dl.loan.margin_bps)} bps · "
              f"{int(dl.loan.maturity_years)}y {dl.loan.profile}",
              size=13, color=TEXT)

    # 4 KPI tiles 2x2
    w, h = Inches(2.9), Inches(1.3)
    tiles = [
        ("Net leverage", f"{m.net_leverage:.2f}×"),
        ("All-in yield", f"{m.all_in_yield:.2f}%"),
        ("Return on capital S2", f"{roc:.1f}%"),
        ("Duration", f"{int(dl.loan.maturity_years)}y"),
    ]
    positions = [(Inches(0.7), Inches(1.9)), (Inches(3.8), Inches(1.9)),
                 (Inches(0.7), Inches(3.4)), (Inches(3.8), Inches(3.4))]
    for (lab, val), (l, t) in zip(tiles, positions):
        _add_kpi_tile(slide, l, t, w, h, lab, val, gold=(lab == "Return on capital S2"))

    # Verdict pill
    _add_text(slide, Inches(7.5), Inches(1.9), Inches(4), Inches(0.4),
              "FINAL VERDICT", size=10, bold=True, color=RGBColor(0x59, 0x59, 0x59))
    _add_verdict_pill(slide, Inches(7.5), Inches(2.3), v.final)

    # 3 key points
    _add_text(slide, Inches(7.5), Inches(3.4), Inches(5), Inches(0.4),
              "KEY POINTS", size=10, bold=True, color=RGBColor(0x59, 0x59, 0x59))
    bullets = [
        f"Crédit: {v.credit.status} — {v.credit.reason or 'all credit ratios above covenant floors'}.",
        f"Solvency II: {v.s2.status} — {v.s2.reason or f'RoC S2 {roc:.1f}% above 35% threshold'}.",
        f"ALM Mandate Fit: {v.alm.status} — {v.alm.reason or 'duration & liquidity within mandate'}.",
    ]
    for i, b in enumerate(bullets):
        _add_text(slide, Inches(7.5), Inches(3.8 + 0.55 * i), Inches(5.2), Inches(0.6), f"• {b}", size=12)


def _slide_infra_summary(prs, infra: InfraDeal, alm: ALMMandate):
    m = compute_infra_metrics_from_model(infra)
    shock = s2_shock_effective(
        infra.risk.rating_estim, infra.debt.debt_maturity_years,
        qii_eligible=infra.risk.qii_eligible, qii_reduction_pct=infra.risk.qii_spread_reduction,
    )
    roc = return_on_capital_s2(m.yield_net_pct, shock)
    v = verdict_infra(m, roc, infra.debt.debt_maturity_years, alm)

    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _add_top_band(slide)
    _add_text(slide, Inches(0.7), Inches(0.4), Inches(12), Inches(0.6),
              f"Deal Summary — {infra.label}", size=26, bold=True, color=ALLIANZ_PRIMARY)
    qii_text = (
        f" · QII −{int(infra.risk.qii_spread_reduction)}%"
        if infra.risk.qii_eligible
        else ""
    )
    _add_text(slide, Inches(0.7), Inches(1.0), Inches(12), Inches(0.4),
              f"{infra.spv.sector} · {infra.offtake.offtake_type} {int(infra.offtake.contract_duration_years)}y · "
              f"{int(infra.debt.debt_maturity_years)}y {infra.debt.debt_profile}{qii_text}",
              size=13, color=TEXT)

    w, h = Inches(2.9), Inches(1.3)
    tiles = [
        ("Min DSCR", f"{m.min_dscr:.2f}×"),
        ("All-in yield", f"{m.all_in_yield_pct:.2f}%"),
        ("Return on capital S2", f"{roc:.1f}%"),
        ("Duration", f"{int(infra.debt.debt_maturity_years)}y"),
    ]
    positions = [(Inches(0.7), Inches(1.9)), (Inches(3.8), Inches(1.9)),
                 (Inches(0.7), Inches(3.4)), (Inches(3.8), Inches(3.4))]
    for (lab, val), (l, t) in zip(tiles, positions):
        _add_kpi_tile(slide, l, t, w, h, lab, val, gold=(lab == "Return on capital S2"))

    _add_text(slide, Inches(7.5), Inches(1.9), Inches(4), Inches(0.4),
              "FINAL VERDICT", size=10, bold=True, color=RGBColor(0x59, 0x59, 0x59))
    _add_verdict_pill(slide, Inches(7.5), Inches(2.3), v.final)

    _add_text(slide, Inches(7.5), Inches(3.4), Inches(5), Inches(0.4),
              "KEY POINTS", size=10, bold=True, color=RGBColor(0x59, 0x59, 0x59))
    bullets = [
        f"Crédit: {v.credit.status} — {v.credit.reason or f'min DSCR {m.min_dscr:.2f}× / LLCR {m.llcr:.2f}×'}.",
        f"Solvency II: {v.s2.status} — {v.s2.reason or f'RoC S2 {roc:.1f}% above 35% threshold'}{' · QII regime applied' if infra.risk.qii_eligible else ''}.",
        f"ALM Mandate Fit: {v.alm.status} — {v.alm.reason or 'duration & liquidity within mandate'}.",
    ]
    for i, b in enumerate(bullets):
        _add_text(slide, Inches(7.5), Inches(3.8 + 0.55 * i), Inches(5.2), Inches(0.6), f"• {b}", size=12)


def _slide_comparator(prs, dl: DLDeal, infra: InfraDeal, alm: ALMMandate):
    dlm = compute_dl_metrics_from_model(dl)
    im = compute_infra_metrics_from_model(infra)
    shock_dl = s2_shock_effective(dl.risk.rating_estim, dl.loan.maturity_years)
    shock_infra = s2_shock_effective(
        infra.risk.rating_estim, infra.debt.debt_maturity_years,
        qii_eligible=infra.risk.qii_eligible, qii_reduction_pct=infra.risk.qii_spread_reduction,
    )
    roc_dl = return_on_capital_s2(dlm.yield_net, shock_dl)
    roc_infra = return_on_capital_s2(im.yield_net_pct, shock_infra)

    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _add_top_band(slide)
    _add_text(slide, Inches(0.7), Inches(0.4), Inches(12), Inches(0.6),
              "Side-by-side Comparator", size=26, bold=True, color=ALLIANZ_PRIMARY)

    rows = [
        ("Metric", dl.label, infra.label),
        ("Leverage / Min DSCR", f"{dlm.net_leverage:.2f}×", f"{im.min_dscr:.2f}×"),
        ("Coverage / Avg DSCR", f"{dlm.interest_coverage:.2f}×", f"{im.avg_dscr:.2f}×"),
        ("FCCR / LLCR", f"{dlm.fccr:.2f}×", f"{im.llcr:.2f}×"),
        ("All-in yield", f"{dlm.all_in_yield:.2f}%", f"{im.all_in_yield_pct:.2f}%"),
        ("Expected loss", f"{dlm.el_annual:.2f}%", f"{im.el_annual_pct:.3f}%"),
        ("Yield net", f"{dlm.yield_net:.2f}%", f"{im.yield_net_pct:.2f}%"),
        ("Spread shock S2", f"{shock_dl:.1f}%", f"{shock_infra:.1f}%"),
        ("Return on capital S2", f"{roc_dl:.1f}%", f"{roc_infra:.1f}%"),
        ("Duration", f"{int(dl.loan.maturity_years)}y", f"{int(infra.debt.debt_maturity_years)}y"),
    ]

    nrows = len(rows)
    table_shape = slide.shapes.add_table(nrows, 3, Inches(0.7), Inches(1.2), Inches(12), Inches(5.6))
    table = table_shape.table
    # Set col widths
    table.columns[0].width = Inches(3.4)
    table.columns[1].width = Inches(4.3)
    table.columns[2].width = Inches(4.3)
    for i, row in enumerate(rows):
        for j, val in enumerate(row):
            cell = table.cell(i, j)
            cell.text = str(val)
            for para in cell.text_frame.paragraphs:
                for run in para.runs:
                    run.font.size = Pt(12 if i > 0 else 13)
                    run.font.bold = (i == 0) or (rows[i][0] == "Return on capital S2")
                    run.font.color.rgb = WHITE if i == 0 else TEXT
            if i == 0:
                cell.fill.solid()
                cell.fill.fore_color.rgb = ALLIANZ_PRIMARY
            elif rows[i][0] == "Return on capital S2":
                cell.fill.solid()
                cell.fill.fore_color.rgb = ALLIANZ_GOLD
                if j > 0:
                    val_dl, val_infra = roc_dl, roc_infra
                    target = val_dl if j == 1 else val_infra
                    other = val_infra if j == 1 else val_dl
                    if target > other:
                        cell.fill.fore_color.rgb = ALLIANZ_GOLD
                    else:
                        cell.fill.solid()
                        cell.fill.fore_color.rgb = WHITE
                    for para in cell.text_frame.paragraphs:
                        for run in para.runs:
                            run.font.color.rgb = WHITE if target > other else ALLIANZ_PRIMARY


def _slide_stress(prs, dl: DLDeal, infra: InfraDeal):
    dlm = compute_dl_metrics_from_model(dl)
    im = compute_infra_metrics_from_model(infra)
    rows = [
        ["Scenario", dl.label, infra.label],
        ["Base case", _icon(dlm.interest_coverage, 1.5, 1.3), _icon(im.min_dscr, 1.4, 1.2)],
        ["Stress 1 (−20% EBITDA / P90 prod)", _icon(dlm.ic_stressed, 1.5, 1.3), _icon(im.min_dscr_p90, 1.4, 1.2)],
        ["Stress 2 (+200 bps / merchant −25%)", _icon(dlm.ic_rate_stressed, 1.5, 1.3), _icon(im.min_dscr_merch, 1.4, 1.2)],
        ["Combined", _icon(dlm.ic_combined, 1.5, 1.3), _icon(im.min_dscr_combined, 1.4, 1.2)],
    ]

    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _add_top_band(slide)
    _add_text(slide, Inches(0.7), Inches(0.4), Inches(12), Inches(0.6),
              "Stress Test Results", size=26, bold=True, color=ALLIANZ_PRIMARY)
    table_shape = slide.shapes.add_table(len(rows), 3, Inches(0.7), Inches(1.4), Inches(12), Inches(4.5))
    table = table_shape.table
    table.columns[0].width = Inches(5.0)
    table.columns[1].width = Inches(3.5)
    table.columns[2].width = Inches(3.5)
    for i, row in enumerate(rows):
        for j, val in enumerate(row):
            cell = table.cell(i, j)
            cell.text = str(val)
            for para in cell.text_frame.paragraphs:
                for run in para.runs:
                    run.font.size = Pt(13 if i > 0 else 14)
                    run.font.bold = (i == 0)
                    run.font.color.rgb = WHITE if i == 0 else TEXT
            if i == 0:
                cell.fill.solid()
                cell.fill.fore_color.rgb = ALLIANZ_PRIMARY
    _add_text(slide, Inches(0.7), Inches(6.3), Inches(12), Inches(0.4),
              "Legend — PASS clears floor · TIGHT within 0.1× of floor · BREACH below floor",
              size=11, color=RGBColor(0x59, 0x59, 0x59))


def _icon(value: float, pass_threshold: float, warn_threshold: float) -> str:
    if value is None or value != value:
        return "—"
    if value >= pass_threshold:
        return f"PASS — {value:.2f}×"
    if value >= warn_threshold:
        return f"TIGHT — {value:.2f}×"
    return f"BREACH — {value:.2f}×"


def _slide_s2_decomp(prs, dl: DLDeal, infra: InfraDeal):
    dlm = compute_dl_metrics_from_model(dl)
    im = compute_infra_metrics_from_model(infra)
    shock_dl = s2_shock_effective(dl.risk.rating_estim, dl.loan.maturity_years)
    shock_infra = s2_shock_effective(
        infra.risk.rating_estim, infra.debt.debt_maturity_years,
        qii_eligible=infra.risk.qii_eligible, qii_reduction_pct=infra.risk.qii_spread_reduction,
    )
    roc_dl = return_on_capital_s2(dlm.yield_net, shock_dl)
    roc_infra = return_on_capital_s2(im.yield_net_pct, shock_infra)

    # Build a matplotlib chart and embed
    fig, ax = plt.subplots(figsize=(9, 4.2))
    labels = [dl.label, infra.label]
    yields = [dlm.all_in_yield, im.all_in_yield_pct]
    yields_net = [dlm.yield_net, im.yield_net_pct]
    shocks = [shock_dl, shock_infra]
    rocs = [roc_dl, roc_infra]
    x = range(len(labels))
    ax.bar([i - 0.32 for i in x], yields, width=0.16, color="#003781", label="All-in yield (%)")
    ax.bar([i - 0.16 for i in x], yields_net, width=0.16, color="#5b8bce", label="Yield net of EL (%)")
    ax.bar(list(x), shocks, width=0.16, color="#B68C1E", label="Spread shock S2 (%)")
    ax.bar([i + 0.16 for i in x], rocs, width=0.16, color="#27AE60", label="RoC S2 (%)")
    ax.set_xticks(list(x))
    ax.set_xticklabels(labels, fontsize=9)
    ax.set_ylabel("Percent")
    ax.legend(loc="upper right", fontsize=8)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.set_title("S2 Capital Decomposition", color="#003781", fontsize=14, fontweight="bold", pad=10)
    buf = BytesIO()
    fig.tight_layout()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)

    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _add_top_band(slide)
    _add_text(slide, Inches(0.7), Inches(0.4), Inches(12), Inches(0.6),
              "S2 Capital Decomposition", size=26, bold=True, color=ALLIANZ_PRIMARY)
    slide.shapes.add_picture(buf, Inches(0.7), Inches(1.3), width=Inches(11.8))

    if infra.risk.qii_eligible:
        _add_text(slide, Inches(0.7), Inches(6.7), Inches(12), Inches(0.4),
                  f"QII regime applied to {infra.label}: spread shock reduced by "
                  f"{int(infra.risk.qii_spread_reduction)}% — Article 164b.",
                  size=12, color=ALLIANZ_GOLD, bold=True)


def _slide_recommendation(prs, dl: DLDeal, infra: InfraDeal, alm: ALMMandate):
    dlm = compute_dl_metrics_from_model(dl)
    im = compute_infra_metrics_from_model(infra)
    shock_dl = s2_shock_effective(dl.risk.rating_estim, dl.loan.maturity_years)
    shock_infra = s2_shock_effective(
        infra.risk.rating_estim, infra.debt.debt_maturity_years,
        qii_eligible=infra.risk.qii_eligible, qii_reduction_pct=infra.risk.qii_spread_reduction,
    )
    roc_dl = return_on_capital_s2(dlm.yield_net, shock_dl)
    roc_infra = return_on_capital_s2(im.yield_net_pct, shock_infra)
    v_dl = verdict_dl(dlm, roc_dl, dl.loan.maturity_years, alm)
    v_infra = verdict_infra(im, roc_infra, infra.debt.debt_maturity_years, alm)

    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _add_top_band(slide)
    _add_text(slide, Inches(0.7), Inches(0.4), Inches(12), Inches(0.6),
              "Recommendation — Allianz Vie", size=26, bold=True, color=ALLIANZ_PRIMARY)

    # Two columns of verdicts
    for col_idx, (label, v, final, roc) in enumerate(
        [(dl.label, v_dl, v_dl.final, roc_dl), (infra.label, v_infra, v_infra.final, roc_infra)]
    ):
        x = Inches(0.7) + Inches(6.3) * col_idx
        _add_text(slide, x, Inches(1.2), Inches(6.0), Inches(0.4), label,
                  size=15, bold=True, color=ALLIANZ_PRIMARY)
        bullets = [
            ("Crédit", v.credit.status, v.credit.reason or "all credit thresholds met"),
            ("Solvency II", v.s2.status, v.s2.reason or f"RoC S2 {roc:.1f}% above 35% threshold"),
            ("ALM Mandate Fit", v.alm.status, v.alm.reason or "duration & liquidity within mandate"),
        ]
        for i, (pillar, status, reason) in enumerate(bullets):
            _add_text(slide, x, Inches(1.7 + 0.7 * i), Inches(6.0), Inches(0.4),
                      f"{pillar} — {status}", size=13, bold=True,
                      color=_verdict_color(status))
            _add_text(slide, x, Inches(1.95 + 0.7 * i), Inches(6.0), Inches(0.4),
                      reason, size=11, color=TEXT)
        _add_text(slide, x, Inches(4.0), Inches(2.5), Inches(0.4),
                  f"FINAL: {final}", size=14, bold=True, color=_verdict_color(final))

    # Next steps DD
    _add_text(slide, Inches(0.7), Inches(5.2), Inches(12), Inches(0.4),
              "Next steps DD", size=14, bold=True, color=ALLIANZ_PRIMARY)
    next_steps = [
        "• Reference calls — sponsor track record, project execution history.",
        "• Side letter — MFN, transparency, fee tail, key-person, no-fault divorce.",
        "• LPAC validation — alignment with Allianz Vie investment policy.",
        "• If ALM REJECT: escalate to Risk & ALM Committee — they own the duration / liquidity envelope.",
    ]
    for i, line in enumerate(next_steps):
        _add_text(slide, Inches(0.7), Inches(5.55 + 0.4 * i), Inches(12), Inches(0.4),
                  line, size=12, color=TEXT)


def build_pptx_report(
    dl: DLDeal | None = None,
    infra: InfraDeal | None = None,
    alm: ALMMandate | None = None,
) -> bytes:
    if alm is None:
        alm = load_alm_mandate()
    if dl is None or infra is None:
        presets = load_preset_deals()
        if dl is None:
            dl = next(d for d in presets if d.type == "DL")
        if infra is None:
            infra = next(d for d in presets if d.type == "INFRA")

    prs = Presentation()
    prs.slide_width = SLIDE_W
    prs.slide_height = SLIDE_H
    _slide_cover(prs, dl.label, infra.label)
    _slide_dl_summary(prs, dl, alm)
    _slide_infra_summary(prs, infra, alm)
    _slide_comparator(prs, dl, infra, alm)
    _slide_stress(prs, dl, infra)
    _slide_s2_decomp(prs, dl, infra)
    _slide_recommendation(prs, dl, infra, alm)
    buf = BytesIO()
    prs.save(buf)
    return buf.getvalue()
