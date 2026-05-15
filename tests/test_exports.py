"""Phase 4 — smoke tests for Excel + PPT exports."""

from __future__ import annotations

from io import BytesIO

from openpyxl import load_workbook
from pptx import Presentation

from src.exports.excel_builder import build_excel_report
from src.exports.pptx_builder import build_pptx_report
from src.utils.presets_loader import load_preset_deals


def _dl_and_infra():
    deals = load_preset_deals()
    dl = next(d for d in deals if d.type == "DL")
    infra = next(d for d in deals if d.type == "INFRA")
    return dl, infra


def test_excel_export_opens_with_5_tabs():
    dl, infra = _dl_and_infra()
    data = build_excel_report(dl=dl, infra=infra)
    assert len(data) > 1000  # non-trivial size
    wb = load_workbook(BytesIO(data))
    assert wb.sheetnames == [
        "1. Inputs",
        "2. DL Calculations",
        "3. Infra Cashflows",
        "4. Stress Tests",
        "5. S2 + Comparator",
    ]


def test_excel_calculations_tab_has_formulas():
    dl, infra = _dl_and_infra()
    data = build_excel_report(dl=dl, infra=infra)
    wb = load_workbook(BytesIO(data))
    ws = wb["2. DL Calculations"]
    # Look for at least one cell starting with "=" (Excel formula)
    formulas = [c.value for col in ws.iter_cols() for c in col if isinstance(c.value, str) and c.value.startswith("=")]
    assert len(formulas) >= 5, f"expected several formulas, found {len(formulas)}"


def test_excel_infra_cashflows_year_count():
    dl, infra = _dl_and_infra()
    data = build_excel_report(dl=dl, infra=infra)
    wb = load_workbook(BytesIO(data))
    ws = wb["3. Infra Cashflows"]
    # First year row is 3, project_life_years rows total
    plife = infra.project.project_life_years
    last_year_cell = ws.cell(row=2 + plife, column=1).value
    assert last_year_cell == plife


def test_pptx_export_has_7_slides():
    dl, infra = _dl_and_infra()
    data = build_pptx_report(dl=dl, infra=infra)
    assert len(data) > 5000
    prs = Presentation(BytesIO(data))
    assert len(prs.slides) == 7


def test_pptx_cover_slide_has_title():
    dl, infra = _dl_and_infra()
    data = build_pptx_report(dl=dl, infra=infra)
    prs = Presentation(BytesIO(data))
    cover_text = " ".join(
        shape.text_frame.text for shape in prs.slides[0].shapes if shape.has_text_frame
    )
    assert "AIM Capital Lens" in cover_text
    assert "Mancef Ferrah" in cover_text
