# Does Recycling Actually Reduce Material Consumption?

## Research Question

> Does increasing recycling correspond to reduced consumption of virgin materials,
> or can recycling expand while total resource use continues to rise?
> The project distinguishes **recycling performance from genuine resource-use decoupling**.

---

## Motivation

Circular-economy policies promise that improving recycling rates will reduce
pressure on virgin natural resources. However, empirical evidence for this
relationship is limited, and rebound effects and economic growth may offset
efficiency gains. This project investigates the association between recycling
performance (measured by the Circular Material Use Rate) and actual material
consumption and domestic extraction of primary materials.

---

## Data Sources

| # | Source | File | Indicator | Years | Coverage |
|---|--------|------|-----------|-------|----------|
| 1 | **UNEP Global Material Flows Database** | `UNEP.csv` | DMC, DE, DMI, EXP, IMP (total tonnes) | 1970–2024 | 247 countries |
| 2 | **OECD Material Flow Accounts** | `OECD.csv` | DMC per capita (t/person) | 1970–2025 | 232 countries |
| 3 | **Eurostat** | `EUROSTAT.csv` | Circular Material Use Rate – CMUR (%) | 2004–2024 | 27 EU members + EU27 aggregate |
| 4 | **UN SDG Database** | `UN-SDG.csv` | DMC total, DMC/cap, DMC/GDP (Goal 8.4) | 2000–2022 | 240 areas |
| 5 | **World Bank** | `WORLDBANK-GDP.csv`, `WORLDBANK-POPULATION.csv` | GDP (current USD), Population | 1960–2025 | 265 countries |

> **Note:** `UN-SDG.xlsx` in `data/raw/` is an unused backup copy of `UN-SDG.csv`. The pipeline reads only `UN-SDG.csv`.

---

## Key Concepts

| Term | Definition | Source |
|------|-----------|--------|
| **CMUR** | Circular Material Use Rate – share of total material input derived from recycled/recovered materials | Eurostat |
| **DMC** | Domestic Material Consumption = DE + Imports − Exports (total tonnes) | UNEP |
| **DE** | Domestic Extraction – primary raw materials extracted domestically | UNEP |
| **Material intensity** | DMC / GDP (tonnes per USD) – proxy for resource efficiency | Derived |
| **Absolute decoupling** | GDP rises while DMC falls | Derived |
| **Relative decoupling** | GDP rises, DMC rises but DMC/GDP falls | Derived |

---

## Completed Deliverables

### Datasets & Analysis
- **UPDATED_MASTER_DATASET.csv** – Master panel (27 EU countries, 2010–2022)
  - 325 observations integrated from 5 data sources
  - Includes real GDP (World Bank const. 2015 USD)
  
### Figures (19 completed analyses)
- **CMU Trends**: fig1 (trend), fig2 (ranking), fig3 (trajectories)
- **Decoupling Classification**: fig8 (counts), fig18 (quadrant), fig19 (Tapio)
- **GDP & Material Intensity**: fig7, fig10, fig11
- **Core Indicators**: fig4, fig5, fig6, fig9, fig14, fig16, fig17
- **Validation & Case Studies**: fig12, fig13, fig23

### Analysis Outputs
- **Real vs Nominal Comparison** – 5 countries reclassified using real GDP
- **Slope vs Endpoint Sensitivity** – 14/25 countries disagree on classification
- **CMU Formula Documentation** – Mathematical definition + endogeneity assessment
- **Literature Review** – 12 citations, EU-focused material-flow decoupling research
- **Statistical Tables** – Descriptive statistics, correlations, sensitivity analyses
- **Results Tables** – Quadrant classification, decoupling class, case studies, recycling performance

### Project Files
```
final-mid/
├── data/
│   ├── raw/          ← 5 source datasets (UNEP, OECD, Eurostat, UN-SDG, World Bank)
│   └── processed/    ← Cleaned datasets A, B (core analysis)
├── src/
│   ├── run_pipeline.py      ← Generates all figures & tables
│   ├── fetch_wb_gdp.py      ← Downloads real GDP & merges
│   └── phase2_analysis.py   ← CMU formula & slope sensitivity
├── outputs/
│   ├── figures/      ← 19 PNG figures
│   ├── tables/       ← 9 CSV/XLSX results tables
│   ├── statistics/   ← 7 analysis CSV files
│   ├── LITERATURE_REVIEW.md
│   ├── CMU_FORMULA_DOCUMENTATION.json
│   ├── REAL_VS_NOMINAL_DECOUPLING_COMPARISON.csv
│   ├── SLOPE_VS_ENDPOINT_SENSITIVITY.csv
│   ├── UPDATED_MASTER_DATASET.csv
│   └── CHANGELOG.md
├── requirements.txt
└── README.md
```

---

## Setup & Running Analysis

### 1. Create virtual environment

```bash
python3 -m venv venv
source venv/bin/activate           # Linux/Mac
# OR: venv\Scripts\activate        # Windows
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Regenerate analysis (optional)

```bash
python src/run_pipeline.py    # Generates all figures & tables
python src/fetch_wb_gdp.py    # Downloads & merges real GDP
python src/phase2_analysis.py # Produces CMU documentation & slope sensitivity
```

All outputs already exist in `outputs/`.
5. Export all tables → `outputs/tables/` and `outputs/statistics/`
6. Generate all 13 figures → `outputs/figures/`

### 4. Run individual modules

```bash
python src/data_cleaning.py      # Step 1 only
python src/data_merge.py         # Step 2 only
python src/indicators.py         # Step 3 only
python src/statistics.py         # Step 4 only
python src/analysis.py           # Step 5 only
python src/visualization.py      # Step 6 only
```

---

## Methodology Summary

### Analytical Datasets

- **Dataset A** (Recycling/Material): EU countries, Eurostat CMUR + UNEP DMC/DE, 2004–2024
- **Dataset B** (Decoupling): UNEP DMC + World Bank GDP/Population, all countries, 1970–2024
- **Dataset C** (Validation): UNEP DMC/capita vs OECD DMC/capita vs UN-SDG DMC/capita

### Key Analysis Period

2010–2022 is used for country-level change comparisons (common overlap of all five sources).

### Statistical Methods

- Pearson and Spearman correlations (pooled + country-level)
- OLS with country + year dummies (within estimator approximation)
- Lag analysis: CMUR(t−1) → DMC(t)
- OECD vs UNEP cross-validation
- Sensitivity analysis across DMC, DMC/capita, DMC/GDP, DE

### Decoupling Classification

| GDP change | DMC change | DMC/GDP change | Classification |
|-----------|-----------|---------------|----------------|
| + | − | − | Absolute decoupling |
| + | + | − | Relative decoupling |
| + | + | + | No decoupling |
| − | − | any | Recession-driven DMC decline |

---

## Key Outputs

| File | Description |
|------|-------------|
| `outputs/figures/fig5_cmur_vs_dmc.png` | **Core result**: CMUR change vs DMC change (4-quadrant) |
| `outputs/figures/fig6_cmur_vs_de.png` | CMUR change vs Domestic Extraction change |
| `outputs/figures/fig7_gdp_vs_dmc.png` | GDP vs DMC (decoupling classification) |
| `outputs/tables/final_results_table.xlsx` | Complete country-level summary table |
| `outputs/statistics/regression_results.csv` | Panel regression coefficients |
| `outputs/statistics/correlation_analysis.csv` | Pearson + Spearman correlations |

---

## Important Limitations

1. **DMC ≠ material footprint**: DMC does not capture the virgin materials
   embodied in imports; countries that offshore extraction appear better
   than they are.
2. **DE = domestic extraction only**: Not the global extraction attributable
   to a country's consumption.
3. **CMUR and DMC use different geographic coverage**: CMUR is available
   only for EU-27; UNEP provides global DMC. The core analysis is therefore
   limited to EU countries.
4. **Observational data**: Statistical associations shown here do not
   establish causation.
5. **Data revisions**: UNEP, OECD, and UN-SDG estimates may differ due to
   methodology revisions, coverage, and compilation year.
6. **Country heterogeneity**: EU member states differ substantially in
   economic structure, industrial composition, and natural-resource endowment.

---

## Academic Integrity Note

All results in this project are computed directly from the supplied datasets.
No values have been fabricated or estimated. Where data are absent, this is
explicitly noted. Conclusions use language indicating association, not causality.

---

## Citation

If you use this project, please cite the original data sources:

- UNEP (2024). *Global Material Flows Database*. United Nations Environment Programme.
- OECD (2024). *Material Flow Accounts*. OECD.Stat.
- Eurostat (2024). *Circular Material Use Rate* (CEI_SRM030). European Commission.
- UN Statistics Division (2024). *SDG Global Database*. Goal 8, Indicator 8.4.
- World Bank (2024). *World Development Indicators*. GDP (NY.GDP.MKTP.CD),
  Population (SP.POP.TOTL).
