# AIM Capital Lens

> *Cross-class private debt comparator for Allianz Vie balance sheet — Direct Lending × Infrastructure Debt × Solvency II return on capital.*

[![Streamlit](https://img.shields.io/badge/Streamlit-1.36+-FF4B4B?logo=streamlit&logoColor=white)](https://streamlit.io)
[![Python](https://img.shields.io/badge/Python-3.13+-blue?logo=python&logoColor=white)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## What this is

A standalone web app + Excel/PowerPoint exporter that compares two private debt
deals — one **Direct Lending** unitranche and one **Infrastructure Debt**
project-finance — on a unified metric set, against the constraints set by an
insurance ALM mandate. Output: a single **3-pillar verdict** (Credit · S2 · ALM
Mandate Fit) plus a downloadable IC-ready slide deck and a fully-auditable
Excel model.

Built as a companion project to
[allianz-renewables-atlas](https://github.com/Manceff/allianz-renewables-atlas)
to demonstrate operational readiness on the lender side: pricing, credit
ratios, project-finance DSCR/LLCR/PLCR, Solvency II capital intensity under
Article 176(3), and the QII regime under Articles 164a / 164b.

## Live demo

`https://aim-capital-lens.streamlit.app` *(once deployed — see "Deploy" below).*

## Why this tool

For an insurance investor (Allianz Vie life portfolio), private debt is judged
on **return on Solvency II capital**, not on raw yield. The shock weighing on a
deal under Article 176(3) depends on rating × maturity, with material relief
for QII-eligible infrastructure debt. The "right" deal for the balance sheet
is the one that maximises yield net of EL relative to that capital intensity —
*subject to the ALM mandate envelope* (duration target, liquidity floor,
S2 ratio target) which is owned by the Risk & ALM Committee, not by the
Alternative Investments analyst.

Capital Lens makes that arbitrage explicit and auditable.

## 3-pillar verdict

| Pillar | Checks | Owner of the decision |
|---|---|---|
| **Crédit** | IC ≥ 1.5×, FCCR ≥ 1.2×, stress test resilience, EL ≤ 1.5% *(DL)* · min DSCR ≥ 1.20×, LLCR ≥ 1.30× *(Infra)* | Alt Investments analyst |
| **Solvency II** | Return on capital S2 ≥ 25% (REJECT) / ≥ 35% (PASS) | Alt Investments analyst |
| **ALM Mandate Fit** | Duration ∈ [8y, 15y], 5y liquidity floor, S2 ratio target | **Risk & ALM Committee — read-only here** |

Final verdict: **PROCEED** if all 3 pass · **CONDITIONS** if any conditional ·
**REJECT** if any pillar rejects.

## Preloaded deals

1. **Deal A** — Unitranche LBO SaaS B2B EU (£440M, 7y bullet, B+, EURIBOR + 625 bps + 1.5% OID + 1.0% upfront)
2. **Deal B** — Infra Debt offshore wind UK (£2,800M, 18y sculpted, BBB QII −40%, CfD £75/MWh)
3. **Deal C** — Infra Debt data center hyperscale US ($1,300M, 15y sculpted, BBB- QII −30%, Microsoft take-or-pay)

## Run locally

```bash
git clone https://github.com/Manceff/aim-capital-lens.git
cd aim-capital-lens
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
streamlit run streamlit_app.py
```

Open http://localhost:8501. The sidebar exposes the four pages
(Deal DL · Deal Infra · Comparator · Exports).

## Tests

```bash
./venv/bin/python -m pytest tests/ -v
```

47 tests covering:
- YAML config loading and Pydantic validation
- Direct Lending ratios (net leverage, IC, FCCR, all-in yield, EL, stress)
- Project finance year-by-year CFADS, DSCR, LLCR, PLCR, debt schedule sculpting
- Solvency II Article 176(3) lookup with linear interpolation + QII reduction
- 3-pillar verdict engine
- Excel + PowerPoint export integrity

## Methodology notes

### Solvency II spread shock
- **Source**: Article 176(3) Règlement délégué (UE) 2015/35, calibrated using
  the Milliman 2019 standard-formula tables. The 6 main rating buckets (AAA,
  AA, A, BBB, BB, B) × 6 maturity bands (3, 5, 7, 10, 15, 20y) are stored
  verbatim in `data/article_176_3.yaml`.
- **Interpolation**: linear between maturity buckets; clamped at extremes.
- **Notch mapping**: B+ / B- / CCC are conservatively mapped onto the B row.
  BBB+ → BBB row, BBB- → BB row, etc. See `notch_mapping` in
  `data/article_176_3.yaml`.

### QII regime
- Spread shock multiplied by `(1 − qii_reduction/100)` when the deal is
  flagged QII-eligible — proxy for Articles 164a / 164b. The reduction
  percentage is editable per deal (default 30–50% range).

### Debt schedule sculpting
- For `Amortizing sculpté` infra debt, the engine sizes principal each year so
  the year's DSCR matches a target of **1.40×**, clipped to outstanding balance
  and forced to clear in the final year. Bullet schedules pay interest each
  year on a constant balance and the principal at maturity.

### Return on capital S2
- `RoC S2 (%) = (yield_net / spread_shock_effective) × 100`. Both inputs in
  percent. The metric reads as the net spread per unit of S2 capital posted.

### ALM Mandate Constraints
- The Risk & ALM Committee fixes the mandate envelope at `data/alm_mandate.yaml`.
  These values appear read-only in the UI header on every page — they are
  inputs to the verdict, not outputs of this tool.

### Note on illustrative mockups
The preset deal numbers reflect the formulas literally (e.g. Deal A — rating
B+ at 7y → Article 176(3) row B shock = 45.9%). The headline figures in some
of the original spec mockups assume small tweaks (different notch mapping or
rating). The verdict reflects the math, on purpose — which means the
3-pillar engine will sometimes return REJECT on the presets to demonstrate
where the mandate envelope binds. Modify EBITDA, margin, maturity, or QII
flag live in the UI to explore counterfactuals.

## Project structure

```
aim-capital-lens/
├── streamlit_app.py                # Home (3 preloaded deals)
├── pages/
│   ├── 1_📊_Deal_DL.py             # Direct Lending deal page
│   ├── 2_🏗️_Deal_Infra.py          # Infra Debt deal page
│   ├── 3_⚖️_Comparator.py          # Side-by-side + 3-pillar verdict
│   └── 4_📥_Exports.py             # Excel + PPT buttons
├── src/
│   ├── models/                     # Pydantic v2 schemas
│   ├── calculations/               # All metric engines
│   ├── exports/                    # openpyxl + python-pptx builders
│   └── utils/                      # Loaders, formatting, UI helpers
├── data/                           # YAML configs (deals, ALM, Art 176(3), PD)
├── assets/                         # Allianz palette + custom CSS
└── tests/                          # pytest — 47 tests
```

## Deploy on Streamlit Cloud

1. Push to GitHub (`Manceff/aim-capital-lens`, public).
2. Go to https://share.streamlit.io and click **New app**.
3. Connect the repo, branch `main`, main file `streamlit_app.py`,
   Python `3.13`.
4. Click **Deploy**. The first build takes ~3 min while it installs
   requirements; afterwards every push to `main` triggers a redeploy.

## License

MIT — see [LICENSE](LICENSE).

## Disclaimer

Personal post-interview project. No proprietary Allianz data is used; preset
deals are illustrative and modelled on public information (East Anglia THREE,
Microsoft hyperscale DC pattern). All Solvency II references are to the
published Règlement délégué (UE) 2015/35 framework.

---

**Author** · Mancef Ferrah · M2 Finance Tech & Data · Université Paris 1 Magistère
