# Road Accident Hotspot Analysis — Bengaluru (2007–2025)

AAT project for Data Exploration and Visualization.

Full step-by-step explanation of every module: [`../docs/CODE_EXPLAINED_hotspot_analysis.md`](../docs/CODE_EXPLAINED_hotspot_analysis.md)

**Data (official, public domain, via OpenCity):**
- Bengaluru Traffic Police, station-wise crashes 2018–2025 and city crashes 2007–2025 — https://data.opencity.in/dataset/bengaluru-road-crashes-data
- Karnataka State Police, district-wise crashes 2020–2023 — https://data.opencity.in/dataset/road-accidents-in-karnataka
- MoRTH, Road Accidents in India 2024 (million-plus cities) — https://data.opencity.in/dataset/road-accidents-in-india-2024

Raw CSVs are in `../data/raw` (unchanged downloads).

## Code (one module per team member)
| Module | Member | What it does |
|---|---|---|
| `src/m1_data_acquisition.py` | Member 1 | Load raw files, inspect, reshape 5 year-wise files into one tidy table |
| `src/m2_preprocessing.py` | Member 2 | Total rows, data types, name harmonisation, missing values, duplicates, validity checks, outliers, features |
| `src/m3_univariate_bivariate.py` | Member 3 | Distributions, trends, zone comparison, hotspot ranking, change analysis |
| `src/m4_multivariate_statistics.py` | Member 4 | Correlation, pair plot, persistence, Hotspot Priority Index, statistical summary, state/national context |
| `src/make_screenshots.py` | Member 4 | Renders code + real output screenshots (`outputs/screenshots/`) |

## Run
```bash
pip install -r requirements.txt
cd src && python run_all.py          # figures, tables, screenshots -> outputs/
```
