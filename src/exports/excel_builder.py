"""Excel export — 5 onglets avec formules visibles + mise en forme conditionnelle.

Onglets:
1. Inputs            — DL + Infra + ALM constants (read-only)
2. DL Calculations   — formules Excel visibles (=B5/B6 ...) + verdict crédit
3. Infra Cashflows   — table year-by-year + DSCR + LLCR + PLCR + tail
4. Stress Tests      — matrice 4 scénarios × 2 deals
5. S2 + Comparator + Verdict — table Art 176(3) + comparator + verdict structuré
"""

from __future__ import annotations

from io import BytesIO
from typing import Any

from openpyxl import Workbook
from openpyxl.formatting.rule import CellIsRule
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

from src.calculations.dl_metrics import compute_dl_metrics_from_model
from src.calculations.project_finance import compute_infra_metrics_from_model
from src.calculations.s2_capital import return_on_capital_s2, s2_shock_effective
from src.calculations.verdict_engine import verdict_dl, verdict_infra
from src.models.alm_mandate import ALMMandate
from src.models.dl_deal import DLDeal
from src.models.infra_deal import InfraDeal
from src.utils.presets_loader import load_alm_mandate, load_article_176_3, load_preset_deals

# Allianz palette
PRIMARY = "FF003781"
GOLD = "FFB68C1E"
INPUT_YELLOW = "FFFFF2CC"
ALM_BLUE = "FFD5E3F0"
GREEN = "FFDFF5E5"
ORANGE = "FFFFF0DA"
RED = "FFFBE3E0"

HEADER_FILL = PatternFill("solid", fgColor=PRIMARY)
HEADER_FONT = Font(name="Calibri", size=11, bold=True, color="FFFFFFFF")
INPUT_FILL = PatternFill("solid", fgColor=INPUT_YELLOW)
ALM_FILL = PatternFill("solid", fgColor=ALM_BLUE)
GOLD_FILL = PatternFill("solid", fgColor=GOLD)
THIN = Side(border_style="thin", color="FF999999")
BORDER = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)
CENTER = Alignment(horizontal="center", vertical="center")
BOLD = Font(bold=True)


def _section_header(ws, row: int, col_start: int, col_end: int, text: str) -> int:
    ws.cell(row=row, column=col_start, value=text)
    ws.cell(row=row, column=col_start).font = HEADER_FONT
    ws.cell(row=row, column=col_start).fill = HEADER_FILL
    ws.merge_cells(
        start_row=row, start_column=col_start, end_row=row, end_column=col_end
    )
    ws.cell(row=row, column=col_start).alignment = CENTER
    return row + 1


def _kv_row(ws, row: int, label: str, value: Any, fill: PatternFill | None = None, fmt: str | None = None) -> int:
    ws.cell(row=row, column=1, value=label).font = BOLD
    cell = ws.cell(row=row, column=2, value=value)
    if fill is not None:
        cell.fill = fill
    if fmt is not None:
        cell.number_format = fmt
    cell.border = BORDER
    return row + 1


def _autosize(ws, max_width: int = 38) -> None:
    for col_idx in range(1, ws.max_column + 1):
        letter = get_column_letter(col_idx)
        longest = 0
        for cell in ws[letter]:
            try:
                v = "" if cell.value is None else str(cell.value)
                longest = max(longest, len(v))
            except Exception:
                pass
        ws.column_dimensions[letter].width = min(max(longest + 2, 12), max_width)


def _verdict_block(ws, row: int, verdict) -> int:
    ws.cell(row=row, column=1, value="VERDICT — 3 pillars").font = HEADER_FONT
    ws.cell(row=row, column=1).fill = HEADER_FILL
    ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=4)
    row += 1
    for label, p in [("Crédit", verdict.credit), ("Solvency II", verdict.s2), ("ALM Mandate Fit", verdict.alm)]:
        ws.cell(row=row, column=1, value=label).font = BOLD
        status_cell = ws.cell(row=row, column=2, value=p.status)
        status_cell.alignment = CENTER
        if p.status == "PASS":
            status_cell.fill = PatternFill("solid", fgColor=GREEN)
        elif p.status == "CONDITIONS":
            status_cell.fill = PatternFill("solid", fgColor=ORANGE)
        else:
            status_cell.fill = PatternFill("solid", fgColor=RED)
        ws.cell(row=row, column=3, value=p.reason or "")
        ws.merge_cells(start_row=row, start_column=3, end_row=row, end_column=6)
        row += 1
    ws.cell(row=row, column=1, value="FINAL").font = BOLD
    final_cell = ws.cell(row=row, column=2, value=verdict.final)
    final_cell.font = Font(bold=True, size=12)
    final_cell.alignment = CENTER
    if verdict.final == "PROCEED":
        final_cell.fill = PatternFill("solid", fgColor=GREEN)
    elif verdict.final == "CONDITIONS":
        final_cell.fill = PatternFill("solid", fgColor=ORANGE)
    else:
        final_cell.fill = PatternFill("solid", fgColor=RED)
    return row + 2


# --------------------------------------------------------------------------- #
# Tab 1 — Inputs
# --------------------------------------------------------------------------- #
def _build_inputs_tab(wb: Workbook, dl: DLDeal, infra: InfraDeal, alm: ALMMandate) -> None:
    ws = wb.create_sheet("1. Inputs")
    row = 1
    row = _section_header(ws, row, 1, 4, f"DL DEAL — {dl.label}")
    items = [
        ("Borrower", dl.borrower.name),
        ("Sector", dl.borrower.sector),
        ("EBITDA (M)", dl.borrower.ebitda),
        ("Loan amount (M)", dl.loan.loan_amount),
        ("Base rate type", dl.loan.base_rate_type),
        ("Base rate level (%)", dl.loan.base_rate_level),
        ("Margin (bps)", dl.loan.margin_bps),
        ("OID (%)", dl.loan.oid_pct),
        ("Upfront (%)", dl.loan.upfront_pct),
        ("Maturity (years)", dl.loan.maturity_years),
        ("Profile", dl.loan.profile),
        ("Capex maintenance (M/y)", dl.borrower.capex_maintenance),
        ("FCF conversion (%)", dl.borrower.fcf_conversion),
        ("Covenant Net Lev cap", dl.covenants.cov_net_lev_cap),
        ("Rating", dl.risk.rating_estim),
        ("PD annual (%)", dl.risk.pd_annual),
        ("LGD (%)", dl.risk.lgd),
    ]
    for k, v in items:
        row = _kv_row(ws, row, k, v, fill=INPUT_FILL)
    row += 1

    row = _section_header(ws, row, 1, 4, f"INFRA DEAL — {infra.label}")
    infra_items = [
        ("Project", infra.spv.project_name),
        ("Sector", infra.spv.sector),
        ("Country", infra.spv.country),
        ("Offtake type", infra.offtake.offtake_type),
        ("Strike price", infra.offtake.strike_price_eur_mwh),
        ("Indexation", infra.offtake.indexation),
        ("Capacity (MW)", infra.offtake.capacity_mw),
        ("Capacity factor (%)", infra.offtake.capacity_factor),
        ("Capex total (M)", infra.project.capex_total_eur_m),
        ("Opex annual (M/y)", infra.project.opex_annual_eur_m),
        ("Project life (y)", infra.project.project_life_years),
        ("Debt amount (M)", infra.debt.debt_amount_eur_m),
        ("Debt maturity (y)", infra.debt.debt_maturity_years),
        ("Debt profile", infra.debt.debt_profile),
        ("Debt base rate (%)", infra.debt.debt_base_rate_level),
        ("Debt margin (bps)", infra.debt.debt_margin_bps),
        ("Rating", infra.risk.rating_estim),
        ("QII eligible", "Yes" if infra.risk.qii_eligible else "No"),
        ("QII spread reduction (%)", infra.risk.qii_spread_reduction),
    ]
    for k, v in infra_items:
        row = _kv_row(ws, row, k, v, fill=INPUT_FILL)
    row += 1

    row = _section_header(ws, row, 1, 4, "ALM MANDATE CONSTRAINTS (read-only)")
    alm_items = [
        ("Duration min (years)", alm.alm_duration_min_years),
        ("Duration max (years)", alm.alm_duration_max_years),
        ("Liquidity floor 5y (%)", alm.alm_liquidity_floor_5y_pct),
        ("S2 ratio minimum (%)", alm.s2_ratio_minimum_pct),
        ("Mandate owner", alm.mandate_owner),
    ]
    for k, v in alm_items:
        row = _kv_row(ws, row, k, v, fill=ALM_FILL)
    _autosize(ws)


# --------------------------------------------------------------------------- #
# Tab 2 — DL Calculations (formulas visible)
# --------------------------------------------------------------------------- #
def _build_dl_calc_tab(wb: Workbook, dl: DLDeal, alm: ALMMandate) -> None:
    ws = wb.create_sheet("2. DL Calculations")
    m = compute_dl_metrics_from_model(dl)
    shock = s2_shock_effective(dl.risk.rating_estim, dl.loan.maturity_years)
    roc = return_on_capital_s2(m.yield_net, shock)
    v = verdict_dl(m, roc, dl.loan.maturity_years, alm)

    # Inputs in column B (rows 2..)
    ws["A1"] = "DL CALCULATIONS — formulas visible"
    ws["A1"].font = HEADER_FONT
    ws["A1"].fill = HEADER_FILL
    ws.merge_cells("A1:D1")
    ws["A1"].alignment = CENTER

    inputs = [
        ("EBITDA (M)", dl.borrower.ebitda),                # row 2
        ("Loan amount (M)", dl.loan.loan_amount),          # 3
        ("Base rate (%)", dl.loan.base_rate_level),        # 4
        ("Margin (bps)", dl.loan.margin_bps),              # 5
        ("OID (%)", dl.loan.oid_pct),                      # 6
        ("Upfront (%)", dl.loan.upfront_pct),              # 7
        ("Maturity (y)", dl.loan.maturity_years),          # 8
        ("Capex maint (M)", dl.borrower.capex_maintenance),# 9
        ("PD annual (%)", dl.risk.pd_annual),              # 10
        ("LGD (%)", dl.risk.lgd),                          # 11
        ("Cov Net Lev cap", dl.covenants.cov_net_lev_cap), # 12
    ]
    for i, (label, val) in enumerate(inputs):
        ws.cell(row=2 + i, column=1, value=label).font = BOLD
        c = ws.cell(row=2 + i, column=2, value=val)
        c.fill = INPUT_FILL
        c.border = BORDER

    # Calculations using formulas — anchor cells (use absolute refs $B$3 etc.)
    row = 14
    ws.cell(row=row, column=1, value="RATIOS (formulas)").font = HEADER_FONT
    ws.cell(row=row, column=1).fill = HEADER_FILL
    ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=4)
    row += 1
    formulas = [
        ("Net leverage (×)", "=B3/B2", "0.00\\x"),
        ("Cash interest (M)", "=B3*(B4/100+B5/10000)", "0.00"),
        ("Interest coverage (×)", "=B2/(B3*(B4/100+B5/10000))", "0.00\\x"),
        ("FCCR (×)", "=(B2-B9)/(B3*(B4/100+B5/10000))", "0.00\\x"),
        ("Debt yield (%)", "=B2/B3*100", "0.0%"),  # display only — value already a percent
        ("All-in yield (%)", "=B4+B5/100+B6/B8+B7/B8", "0.00%"),
        ("Expected loss (%)", "=B10*B11/100", "0.00%"),
        ("Yield net (%)", "=B4+B5/100+B6/B8+B7/B8-B10*B11/100", "0.00%"),
        ("Headroom Net Lev (%)", "=(B12/(B3/B2))-1", "0.0%"),
        ("Net Lev stressed (×)", "=B3/(B2*0.8)", "0.00\\x"),
        ("IC stressed −20% (×)", "=(B2*0.8)/(B3*(B4/100+B5/10000))", "0.00\\x"),
        ("IC +200bps (×)", "=B2/(B3*(B4/100+B5/10000+0.02))", "0.00\\x"),
        ("IC combined (×)", "=(B2*0.8)/(B3*(B4/100+B5/10000+0.02))", "0.00\\x"),
    ]
    for label, formula, fmt in formulas:
        ws.cell(row=row, column=1, value=label).font = BOLD
        cell = ws.cell(row=row, column=2, value=formula)
        # Most fmts contain \\x for display — openpyxl tolerates plain ones too
        try:
            cell.number_format = fmt.replace("\\x", '"x"')
        except Exception:
            pass
        cell.border = BORDER
        row += 1

    # Conditional formatting on IC stressed row (=22), >=1.3 green, 1.0-1.3 orange, <1.0 red
    ic_stress_cell = ws.cell(row=14 + 1 + 10, column=2)  # IC stressed row (row 25)
    # Use the verdict status to colour-code summary
    row += 1
    row = _verdict_block(ws, row, v)

    ws["D2"] = "Spread shock S2 (%)"
    ws["D2"].font = BOLD
    ws["E2"] = shock
    ws["E2"].number_format = "0.0"
    ws["D3"] = "Return on capital S2 (%)"
    ws["D3"].font = BOLD
    ws["E3"] = roc
    ws["E3"].number_format = "0.0"
    ws["E3"].fill = GOLD_FILL

    _autosize(ws)


# --------------------------------------------------------------------------- #
# Tab 3 — Infra Cashflows
# --------------------------------------------------------------------------- #
def _build_infra_cashflows_tab(wb: Workbook, infra: InfraDeal, alm: ALMMandate) -> None:
    ws = wb.create_sheet("3. Infra Cashflows")
    metrics = compute_infra_metrics_from_model(infra)
    shock = s2_shock_effective(
        infra.risk.rating_estim, infra.debt.debt_maturity_years,
        qii_eligible=infra.risk.qii_eligible, qii_reduction_pct=infra.risk.qii_spread_reduction,
    )
    roc = return_on_capital_s2(metrics.yield_net_pct, shock)
    v = verdict_infra(metrics, roc, infra.debt.debt_maturity_years, alm)

    ws["A1"] = f"INFRA CASHFLOWS — {infra.label}"
    ws["A1"].font = HEADER_FONT
    ws["A1"].fill = HEADER_FILL
    ws.merge_cells("A1:L1")
    ws["A1"].alignment = CENTER

    headers = ["Year", "Revenue", "Opex", "Heavy maint", "Tax", "Op CF", "CFADS",
               "Debt principal", "Debt interest", "Debt service", "DSCR", "Debt balance"]
    for col, h in enumerate(headers, start=1):
        c = ws.cell(row=2, column=col, value=h)
        c.font = HEADER_FONT
        c.fill = HEADER_FILL
        c.alignment = CENTER
        c.border = BORDER

    df = metrics.cashflows
    for i, (yr, r) in enumerate(df.iterrows(), start=3):
        ws.cell(row=i, column=1, value=int(yr))
        ws.cell(row=i, column=2, value=float(r["revenue"]))
        ws.cell(row=i, column=3, value=float(r["opex"]))
        ws.cell(row=i, column=4, value=float(r["heavy_maint"]))
        ws.cell(row=i, column=5, value=float(r["tax"]))
        ws.cell(row=i, column=6, value=float(r["op_cf"]))
        ws.cell(row=i, column=7, value=float(r["cfads"]))
        ws.cell(row=i, column=8, value=float(r["debt_principal"]))
        ws.cell(row=i, column=9, value=float(r["debt_interest"]))
        ws.cell(row=i, column=10, value=float(r["debt_service"]))
        dscr_val = float(r["dscr"]) if r["dscr"] == r["dscr"] else None  # NaN guard
        ws.cell(row=i, column=11, value=dscr_val)
        ws.cell(row=i, column=12, value=float(r["debt_balance"]))
        for col in range(2, 13):
            ws.cell(row=i, column=col).number_format = "#,##0.00"

    last_row = 2 + len(df)
    # Conditional formatting DSCR — green ≥1.4 / orange 1.2-1.4 / red <1.2
    dscr_range = f"K3:K{last_row}"
    ws.conditional_formatting.add(
        dscr_range,
        CellIsRule(operator="greaterThanOrEqual", formula=["1.4"],
                   fill=PatternFill("solid", fgColor=GREEN)),
    )
    ws.conditional_formatting.add(
        dscr_range,
        CellIsRule(operator="between", formula=["1.2", "1.4"],
                   fill=PatternFill("solid", fgColor=ORANGE)),
    )
    ws.conditional_formatting.add(
        dscr_range,
        CellIsRule(operator="lessThan", formula=["1.2"],
                   fill=PatternFill("solid", fgColor=RED)),
    )

    summary_row = last_row + 2
    summary = [
        ("Min DSCR", metrics.min_dscr),
        ("Avg DSCR", metrics.avg_dscr),
        ("LLCR", metrics.llcr),
        ("PLCR", metrics.plcr),
        ("Tail (y)", metrics.tail_years),
        ("All-in yield (%)", metrics.all_in_yield_pct),
        ("Expected loss (%)", metrics.el_annual_pct),
        ("Yield net (%)", metrics.yield_net_pct),
        ("Spread shock S2 (%)", shock),
        ("Return on capital S2 (%)", roc),
    ]
    for label, val in summary:
        ws.cell(row=summary_row, column=1, value=label).font = BOLD
        c = ws.cell(row=summary_row, column=2, value=val)
        c.number_format = "#,##0.00"
        c.fill = GOLD_FILL if "Return on capital" in label else INPUT_FILL
        c.border = BORDER
        summary_row += 1
    summary_row += 1
    _verdict_block(ws, summary_row, v)
    _autosize(ws, max_width=22)


# --------------------------------------------------------------------------- #
# Tab 4 — Stress Tests matrix
# --------------------------------------------------------------------------- #
def _build_stress_tab(wb: Workbook, dl: DLDeal, infra: InfraDeal) -> None:
    ws = wb.create_sheet("4. Stress Tests")
    ws["A1"] = "STRESS TESTS — DL × Infra Debt"
    ws["A1"].font = HEADER_FONT
    ws["A1"].fill = HEADER_FILL
    ws.merge_cells("A1:E1")
    ws["A1"].alignment = CENTER

    dlm = compute_dl_metrics_from_model(dl)
    im = compute_infra_metrics_from_model(infra)

    headers = ["Scenario", f"{dl.label} — metric", "Value", f"{infra.label} — metric", "Value"]
    for col, h in enumerate(headers, start=1):
        c = ws.cell(row=3, column=col, value=h)
        c.font = HEADER_FONT
        c.fill = HEADER_FILL
        c.alignment = CENTER

    rows = [
        ("Base case", "IC", dlm.interest_coverage, "Min DSCR", im.min_dscr),
        ("Stress 1 — EBITDA −20% / Production −15% P90", "IC stressed",
         dlm.ic_stressed, "Min DSCR P90", im.min_dscr_p90),
        ("Stress 2 — +200 bps base / Merchant −25%", "IC +200bps", dlm.ic_rate_stressed,
         "Min DSCR merchant", im.min_dscr_merch),
        ("Stress 3 — Combined", "IC combined", dlm.ic_combined, "Min DSCR combined", im.min_dscr_combined),
    ]
    for i, (scen, dl_label, dl_val, inf_label, inf_val) in enumerate(rows, start=4):
        ws.cell(row=i, column=1, value=scen).font = BOLD
        ws.cell(row=i, column=2, value=dl_label)
        c = ws.cell(row=i, column=3, value=float(dl_val) if dl_val is not None else None)
        c.number_format = "0.00"
        if dl_val is not None and dl_val < 1.2:
            c.fill = PatternFill("solid", fgColor=RED)
        elif dl_val is not None and dl_val < 1.4:
            c.fill = PatternFill("solid", fgColor=ORANGE)
        else:
            c.fill = PatternFill("solid", fgColor=GREEN)
        ws.cell(row=i, column=4, value=inf_label)
        c2 = ws.cell(row=i, column=5, value=float(inf_val) if inf_val is not None else None)
        c2.number_format = "0.00"
        if inf_val is not None and inf_val < 1.2:
            c2.fill = PatternFill("solid", fgColor=RED)
        elif inf_val is not None and inf_val < 1.4:
            c2.fill = PatternFill("solid", fgColor=ORANGE)
        else:
            c2.fill = PatternFill("solid", fgColor=GREEN)

    _autosize(ws, max_width=42)


# --------------------------------------------------------------------------- #
# Tab 5 — S2 + Comparator + Verdict
# --------------------------------------------------------------------------- #
def _build_s2_comparator_tab(wb: Workbook, dl: DLDeal, infra: InfraDeal, alm: ALMMandate) -> None:
    ws = wb.create_sheet("5. S2 + Comparator")
    art = load_article_176_3()["ratings"]
    ws["A1"] = "ARTICLE 176(3) SPREAD SHOCK TABLE — Milliman 2019"
    ws["A1"].font = HEADER_FONT
    ws["A1"].fill = HEADER_FILL
    ws.merge_cells("A1:H1")
    ws["A1"].alignment = CENTER

    buckets = [3, 5, 7, 10, 15, 20]
    ws.cell(row=3, column=1, value="Rating \\ Maturity").font = BOLD
    for col, b in enumerate(buckets, start=2):
        c = ws.cell(row=3, column=col, value=f"{b}y")
        c.font = HEADER_FONT
        c.fill = HEADER_FILL
        c.alignment = CENTER
    for i, rating in enumerate(["AAA", "AA", "A", "BBB", "BB", "B"], start=4):
        ws.cell(row=i, column=1, value=rating).font = BOLD
        for col, b in enumerate(buckets, start=2):
            c = ws.cell(row=i, column=col, value=art[rating][b])
            c.number_format = "0.0"

    row = 12
    ws.cell(row=row, column=1, value="COMPARATOR — DL × Infra Debt").font = HEADER_FONT
    ws.cell(row=row, column=1).fill = HEADER_FILL
    ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=3)
    row += 1
    headers = ["Metric", dl.label, infra.label]
    for col, h in enumerate(headers, start=1):
        c = ws.cell(row=row, column=col, value=h)
        c.font = HEADER_FONT
        c.fill = HEADER_FILL
        c.alignment = CENTER
    row += 1

    dlm = compute_dl_metrics_from_model(dl)
    im = compute_infra_metrics_from_model(infra)
    shock_dl = s2_shock_effective(dl.risk.rating_estim, dl.loan.maturity_years)
    shock_infra = s2_shock_effective(
        infra.risk.rating_estim, infra.debt.debt_maturity_years,
        qii_eligible=infra.risk.qii_eligible, qii_reduction_pct=infra.risk.qii_spread_reduction,
    )
    roc_dl = return_on_capital_s2(dlm.yield_net, shock_dl)
    roc_infra = return_on_capital_s2(im.yield_net_pct, shock_infra)

    rows = [
        ("Leverage / Min DSCR", f"{dlm.net_leverage:.2f}×", f"{im.min_dscr:.2f}×"),
        ("Coverage / Avg DSCR", f"{dlm.interest_coverage:.2f}×", f"{im.avg_dscr:.2f}×"),
        ("FCCR / LLCR", f"{dlm.fccr:.2f}×", f"{im.llcr:.2f}×"),
        ("Debt yield / PLCR", f"{dlm.debt_yield:.1f}%", f"{im.plcr:.2f}×"),
        ("All-in yield", f"{dlm.all_in_yield:.2f}%", f"{im.all_in_yield_pct:.2f}%"),
        ("EL annual", f"{dlm.el_annual:.2f}%", f"{im.el_annual_pct:.3f}%"),
        ("Yield net", f"{dlm.yield_net:.2f}%", f"{im.yield_net_pct:.2f}%"),
        ("Spread shock S2", f"{shock_dl:.1f}%", f"{shock_infra:.1f}%"),
        ("Return on capital S2", f"{roc_dl:.1f}%", f"{roc_infra:.1f}%"),
        ("Duration", f"{dl.loan.maturity_years:.0f}y", f"{infra.debt.debt_maturity_years}y"),
    ]
    for label, dl_val, infra_val in rows:
        ws.cell(row=row, column=1, value=label).font = BOLD if label != "Return on capital S2" else Font(bold=True, color="FFFFFFFF")
        ws.cell(row=row, column=2, value=dl_val)
        ws.cell(row=row, column=3, value=infra_val)
        if label == "Return on capital S2":
            # Highlight max in gold
            if roc_dl > roc_infra:
                ws.cell(row=row, column=2).fill = GOLD_FILL
            else:
                ws.cell(row=row, column=3).fill = GOLD_FILL
            ws.cell(row=row, column=1).fill = HEADER_FILL
            ws.cell(row=row, column=1).font = HEADER_FONT
        row += 1

    row += 1
    v_dl = verdict_dl(dlm, roc_dl, dl.loan.maturity_years, alm)
    v_infra = verdict_infra(im, roc_infra, infra.debt.debt_maturity_years, alm)
    ws.cell(row=row, column=1, value=f"VERDICT — {dl.label}").font = HEADER_FONT
    ws.cell(row=row, column=1).fill = HEADER_FILL
    ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=6)
    row += 1
    row = _verdict_block(ws, row, v_dl)
    ws.cell(row=row, column=1, value=f"VERDICT — {infra.label}").font = HEADER_FONT
    ws.cell(row=row, column=1).fill = HEADER_FILL
    ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=6)
    row += 1
    row = _verdict_block(ws, row, v_infra)
    _autosize(ws)


# --------------------------------------------------------------------------- #
# Public
# --------------------------------------------------------------------------- #
def build_excel_report(
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

    wb = Workbook()
    wb.remove(wb.active)  # drop default sheet
    _build_inputs_tab(wb, dl, infra, alm)
    _build_dl_calc_tab(wb, dl, alm)
    _build_infra_cashflows_tab(wb, infra, alm)
    _build_stress_tab(wb, dl, infra)
    _build_s2_comparator_tab(wb, dl, infra, alm)
    buf = BytesIO()
    wb.save(buf)
    return buf.getvalue()
