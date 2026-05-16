# Single-deal analyzer pivot — design spec

**Status**: validated 2026-05-16 — supersedes the multi-page comparator from v1.
**Owner**: Mancef Ferrah.

## Why

v1 displays ~25 metrics across four dense columns × two deal types × a comparator
page. Even the author finds it hard to grasp. The interview audience (a senior
credit analyst) will not absorb that volume in 30 minutes.

v2 inverts the experience: the user picks a *template* (project type), adjusts
seven essential inputs, and reads an *analysis* (verdict + narrative
interpretation) rather than a numbers dump. The comparator disappears.

## Architecture

Two pages only:

1. **Home** (`streamlit_app.py`) — landing with the ALM banner and four template
   cards. Clicking a card writes the chosen template id into `st.session_state`
   and navigates to the Analyzer.
2. **Analyzer** (`pages/1_Analyzer.py`) — the single work page. Two columns:
   form on the left (40%), analysis on the right (60%). Excel + PowerPoint
   exports live as two buttons at the bottom of the analysis column.

Pages removed: `pages/1_Direct_Lending.py`, `pages/2_Infra_Debt.py`,
`pages/3_Comparator.py`, `pages/4_Exports.py`.

## Form (left column)

Seven essential fields visible by default. The field set depends on the
template's deal type.

| Direct Lending          | Infrastructure Debt        |
|-------------------------|----------------------------|
| Borrower name           | Project name               |
| EBITDA (M)              | Capacity (MW)              |
| Loan amount (M)         | Strike / unit revenue      |
| Margin (bps)            | Capex total (M)            |
| Maturity (years)        | Debt amount (M)            |
| Rating                  | Debt maturity (years)      |
| LGD (%)                 | Rating                     |

An `Advanced` expander (collapsed by default) exposes the rest: base rate,
OID, upfront, capex maintenance, FCF conversion, covenants (DL) — opex, heavy
maintenance, QII eligibility + reduction, indexation, cpi (Infra). Defaults
come from the template.

## Analysis (right column)

Top to bottom:

1. **Verdict pill** in large type — PROCEED / CONDITIONS / REJECT.
2. **Three pillars** with status and reason in clear English (already built).
3. **Key metrics — narrative reading**. Each metric appears once with its
   numeric value AND a sentence interpretation. Example:
   `Net leverage 5.5× — upper mid-cap unitranche, 22% inside covenant cap.
   Common for B+ SaaS borrowers.`
4. **Stress test summary** in three lines for DL (base / EBITDA −20% /
   +200 bps combined) and three for Infra (base / P90 production / combined).
5. **Exports** — Excel + PowerPoint download buttons.

## Narrative engine

New module `src/analysis/narrative.py`. Public entry points:

- `analyze_dl(metrics, deal_inputs, alm) -> list[Commentary]`
- `analyze_infra(metrics, deal_inputs, alm) -> list[Commentary]`

`Commentary` is a small dataclass `(metric_name: str, value_str: str, sentence: str, tone: Literal["positive", "neutral", "concern"])`.

For each metric, the engine reads the value against rating / sector / covenant
thresholds and picks a sentence template. Tone drives the colour cue beside
the metric in the UI.

## Templates

`data/preset_deals.yaml` is reused as-is and renamed conceptually to
"templates". The existing three deals (Unitranche LBO SaaS, Infra Offshore
Wind, Infra Data Center) become three of the four cards on the Home. The
fourth card — *Custom* — loads a minimal Direct-Lending stub the user fills
in.

## What is reused

- All calculation code in `src/calculations/` — untouched.
- All Pydantic models — untouched.
- All export builders — invoked from the Analyzer page.
- 47 existing tests — must remain green.

## What is added

- `src/analysis/narrative.py` — narrative engine.
- `tests/test_narrative.py` — verifies sentences mention the right thresholds
  for representative input values.
- One additional template entry in `preset_deals.yaml` for the Custom card.

## Acceptance

- Home renders the four cards; clicking a card lands on Analyzer with the
  template loaded.
- Analyzer renders without errors for all four templates.
- For each template, the verdict pill, three pillars, and narrative metrics
  appear. Excel and PowerPoint buttons produce valid files.
- `pytest tests/` is green (47 existing + new narrative tests).
