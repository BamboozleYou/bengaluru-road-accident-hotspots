# Road Accident Hotspot Analysis — Bengaluru

Data Exploration and Visualization AAT project. We use official Bengaluru Traffic Police data (2007–2025) to find which police-station areas are road-accident hotspots, how severe they are, and whether they persist over time.

## Start here

| If you want to… | Open |
|---|---|
| Understand the dataset (what every file and column contains) | [`docs/DATASET_AND_PRESENTATION2_GUIDE.md`](docs/DATASET_AND_PRESENTATION2_GUIDE.md) |
| Understand the **final project code** (your module) | [`docs/CODE_EXPLAINED_hotspot_analysis.md`](docs/CODE_EXPLAINED_hotspot_analysis.md) |
| Understand the Presentation 2 notebook/script line by line | [`docs/CODE_EXPLAINED_presentation2.md`](docs/CODE_EXPLAINED_presentation2.md) |
| See every source, paper and library we cite | [`docs/References.md`](docs/References.md) |

## Repository layout

```
├── data/
│   ├── raw/                  8 original CSVs, exactly as downloaded from OpenCity (never edit these)
│   └── processed/            cleaned tables produced by eda_bangalore_accidents.py
├── hotspot_analysis/         FINAL PROJECT — one module per team member
│   ├── src/                  common.py, m1…m4 modules, run_all.py, make_screenshots.py
│   └── outputs/              figures (21), tables (18), console output, screenshots, results.json
├── eda_bangalore_accidents.py        Presentation 2 analysis (script)
├── EDA_Bengaluru_Road_Accidents.ipynb  same code as a notebook, with outputs
├── outputs/                  Presentation 2 charts and key_numbers.json
├── Bengaluru_Road_Accidents_Dataset.xlsx  full raw + clean data with live-formula statistics
└── docs/                     explanations and references
```

## Who owns what (final project)

| Module | Member | Topic |
|---|---|---|
| `hotspot_analysis/src/m1_data_acquisition.py` | Member 1 | Load, inspect and reshape the raw data |
| `hotspot_analysis/src/m2_preprocessing.py` | Member 2 | Cleaning: total rows, types, names, missing values, duplicates, validity, outliers, features |
| `hotspot_analysis/src/m3_univariate_bivariate.py` | Member 3 | Distributions, trends, zones, hotspot ranking, change over time |
| `hotspot_analysis/src/m4_multivariate_statistics.py` | Member 4 | Correlation, persistence, Hotspot Priority Index, statistical tests, Karnataka/India context |

## Run it

Python 3.10+.

```bash
git clone <this repo>
cd <repo folder>
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r hotspot_analysis/requirements.txt

# final project: regenerates everything in hotspot_analysis/outputs/
cd hotspot_analysis/src && python run_all.py && cd ../..

# Presentation 2 analysis: regenerates data/processed/ and outputs/
python eda_bangalore_accidents.py
```

Or open `EDA_Bengaluru_Road_Accidents.ipynb` in Jupyter / VS Code and run the cells in order.

## Data

All data is public domain, from the OpenCity Urban Data Portal:

- Bengaluru Traffic Police — station-wise crashes 2018–2025 and city crashes 2007–2025: https://data.opencity.in/dataset/bengaluru-road-crashes-data
- Karnataka State Police — district-wise crashes 2020–2023: https://data.opencity.in/dataset/road-accidents-in-karnataka
- MoRTH, Govt. of India — Road Accidents in India 2024 (large cities): https://data.opencity.in/dataset/road-accidents-in-india-2024

The data is **counts per police station per year**, not individual crashes. See the dataset guide for every column and every data-quality issue we handled.
