# Dataset & Presentation 2 Guide — Bengaluru Road Accident EDA

## Overview

One Python script turns 8 public CSV files into a clean 371-row table, 11 charts, an Excel workbook and the 21-slide deck. (The slide deck itself is shared separately.)

How the pieces connect, in order:

1. `data/raw/` — the 8 CSV files exactly as downloaded from OpenCity (never edited).
2. `eda_bangalore_accidents.py` (and the same code as `EDA_Bengaluru_Road_Accidents.ipynb`) reads them, cleans them and runs the EDA.
3. The script writes `data/processed/` (9 clean CSVs), `outputs/figures/` (11 PNG charts), `outputs/key_numbers.json` (every number used on the slides) and `outputs/eda_console_output.txt` (all printed output).
4. `Bengaluru_Road_Accidents_Dataset.xlsx` holds the full raw and clean data plus live-formula statistics.
5. `Bengaluru_Accident_EDA_Presentation2.pptx` uses the PNG charts and the numbers from `key_numbers.json`, so every figure on a slide can be traced back to the code.

To re-run: `pip install -r requirements.txt`, then run the notebook from the repository root.

## The dataset, exactly

The data is **counts per police station per year**, not individual crashes. There are no dates, times, GPS points, road names, vehicle types or victim details. All 8 files come from OpenCity (data.opencity.in) under a Public Domain licence, downloaded 26 Oct 2026.

| File (in `data/raw/`) | Publisher | Raw rows | Columns | One row means | Aggregate rows inside |
| --- | --- | --- | --- | --- | --- |
| `btp_station_2018_2020.csv` | Bengaluru Traffic Police | 45 | 17 | 1 station, 3 years side by side | 1 (Grand Total) |
| `btp_station_2020_2022.csv` | Bengaluru Traffic Police | 45 | 12 | 1 station, 2021 + 2022 (despite the name, no 2020) | 1 |
| `btp_station_2023.csv` | Bengaluru Traffic Police | 63 | 8 | 1 station, 2023 | 15 (10 sub-division, 4 zone, 1 grand) |
| `btp_station_2024.csv` | Bengaluru Traffic Police | 65 | 6 | 1 station, 2024 | 15 |
| `btp_station_2025.csv` | Bengaluru Traffic Police | 68 | 6 | 1 station, 2025 | 15 |
| `blr_crashes_2007_2025.csv` | Bengaluru Traffic Police | 19 | 5 | whole city, 1 year | 0 |
| `ka_district_2020_2023.csv` | Karnataka State Police | 39 | 10 | 1 police district, 4 years | 1 (TOTAL) |
| `india_large_cities_2024.csv` | MoRTH, Govt. of India | 51 | 14 | 1 large city, 2023 + 2024 | 1 (Total) |

### Primary data: the 5 station files

Together they hold 371 station-year records (44 stations a year for 2018–2022, then 48, 50 and 53) plus 47 total rows.

- **2018–2020 file columns:** `Zone`, `Station`, then for each year `Fatal`, `Killed`, `Non-Fatal`, `Injured`, `Total Cases` (e.g. `2018 - Fatal`).
- **2021–2022 file:** the same 5 measures for 2021 and 2022.
- **2023 file:** adds `Sub-division`; measures are `Fatal Cases`, `Killed People`, `Non-Fatal`, `Injured People`, `Total Cases`.
- **2024 and 2025 files:** only `Non Fatal`, `Fatal crashes`, `Total crashes`, in that order. **Killed and Injured are no longer published.**

What the measures mean:

- **Fatal** = crashes where at least one person died. **Killed** = number of people who died (can be more than Fatal).
- **Non-Fatal** = injury-only crashes. **Injured** = number of people hurt.
- **Total** = Fatal + Non-Fatal crashes.

Example row (K R Puram, 2018): 42 fatal crashes, 43 killed, 241 non-fatal crashes, 221 injured, 283 total.

Quirks found in these files: trailing spaces in headers (`'2020 - Total Cases '`), an invisible BOM character at the start of the 2024 and 2025 files, sub-total rows mixed with station rows, 16 station names spelled differently across years (`K.R.Pura` vs `K R Puram`), and 22 stations moved to a different zone in 2023.

### Supporting data

- **City annual (2007–2025):** `Year`, `Fatal Road Accidents`, `Killed`, `Non-Fatal Road Accidents`, `Total`. Numbers above 999 are text with commas (`"8,426"`). Used for the long-term trend and to cross-check the station totals.
- **Karnataka districts (2020–2023):** `Sl No`, `District`, then `Road Crashes` and `Deaths` per year for 38 police districts. Vijayanagara is blank for 2020–21 because the district was created in 2021. Used for one number: Bengaluru City = 11.5% of the state's 2023 crashes.
- **India large cities (2023–2024):** `City`, accidents, killed and injured for 2023 and 2024, plus each city's rank. Used for one number: Bengaluru ranks #2 of 50 cities (4,769 accidents, 894 killed in 2024).

## The cleaned dataset

After cleaning, the 5 station files become **one table of 371 rows × 16 columns**: `data/processed/bengaluru_station_crashes_2018_2025_clean.csv` (and the `Station_Crashes_Clean` sheet in the workbook).

| Column | pandas type | What it holds |
| --- | --- | --- |
| `Year` | int64 | 2018–2025 |
| `Zone` | str | Zone under the **2025** boundaries (North, East, West, South), so years compare fairly |
| `Zone_reported` | str | Zone exactly as printed that year (before/after the 2023 redraw) |
| `Sub_division` | str | Sub-division; back-filled for 2018–22 from later years; 5 blanks remain (Devanahalli) |
| `Station` | str | Harmonised station name (54 unique) |
| `Station_raw` | str | Name exactly as published |
| `Fatal`, `Non_Fatal`, `Total` | Int64 | Crash counts, complete for all 371 rows |
| `Killed`, `Injured` | Int64 | Victim counts; blank (`<NA>`) for all 103 rows of 2024–2025 |
| `Fatality_Rate_pct` | Float64 | Fatal ÷ Total × 100 (derived) |
| `Severity_Index` | Float64 | Killed ÷ Total × 100, 2018–2023 only (derived) |
| `chk_total` | boolean | True if Fatal + Non\_Fatal = Total (all 371 are True) |
| `chk_killed_ge_fatal` | boolean | True if Killed ≥ Fatal (all True) |
| `Source_file` | str | Which raw file the row came from |

What changed from raw to clean:

- **Reshaped** from wide (one column per year-measure) to long (one row per station per year).
- **50 aggregate rows removed.** The raw files contain 47 total rows; after reshaping, the 2018–20 grand-total row becomes 3 rows and the 2021–22 one becomes 2, giving 50.
- **Types fixed:** text to numbers, commas and spaces stripped.
- **16 station spellings mapped** to one name each. Devanahalli (2018–22) was *not* merged with Int. Airport (2023+) because the link is unconfirmed.
- **Nothing imputed** and **no rows dropped as duplicates** (there were none).

The other processed files: `bengaluru_city_annual_2007_2025_clean.csv` (19 rows), `karnataka_districts_2020_2023_clean.csv` (150 district-years), `india_large_cities_2023_2024_clean.csv` (50 cities), plus result tables for descriptive statistics, outliers, temporal anomalies, the station ranking and the data dictionary.

## The code, section by section

`eda_bangalore_accidents.py` runs top to bottom in three parts, matching the brief. The notebook has the same cells, with headings, so you can run it live one cell at a time.

| Section | What it does | Key pandas / library calls | Output |
| --- | --- | --- | --- |
| Setup | Imports, folder paths, monochrome chart style (black/grey + red `#D62828`) | `sns.set_theme`, `plt.rcParams` | — |
| 1.1 Load | Reads all 8 CSVs **as text** so nothing is mis-parsed; strips the BOM | `pd.read_csv(..., encoding="utf-8-sig", dtype=str)` | File inventory (rows × cols) |
| 1.2 Inspect | Prints columns, first rows; finds headers with stray spaces | `df.columns`, `df.head()`, `c != c.strip()` | Issue list |
| 1.3 Reshape | `tidy_wide()` turns each wide file into one row per station per year, mapping the different column names to `Fatal/Killed/Non_Fatal/Injured/Total` | custom function + `pd.concat` | 421 long rows (371 stations + 50 totals) |
| 1.4 Data dictionary | Defines every attribute, type and meaning | `pd.DataFrame` | `data_dictionary.csv` |
| 2.1 Aggregate rows | Flags rows whose station contains "Total" or whose zone is blank, removes them, keeps grand totals aside for checking | `.str.contains("Total")`, `.isna()` | 50 rows removed |
| 2.2 Types | Strips spaces, removes commas, converts counts to nullable integers | `pd.to_numeric(...).astype("Int64")` | dtypes before/after |
| 2.3 Harmonise | Maps 16 spellings to one name; assigns each station its 2025 zone; back-fills sub-division | `.replace(NAME_MAP)`, `groupby().last()` | 22 stations re-zoned |
| 2.4 Missing | Counts blanks per column and per year; draws the missing-value map | `.isna().sum()`, `sns.heatmap` | `01_missing_heatmap.png` |
| 2.5 Duplicates | Exact duplicates and duplicate (Station, Year) keys | `.duplicated()`, `.duplicated(subset=[...])` | 0 and 0 |
| 2.6 Validation | Rule checks (Total = Fatal + Non-fatal; Killed ≥ Fatal) and reconciliation with the city table | boolean columns, `groupby().sum()`, `.join` | 0 failures; reconciliation table |
| 2.7 Features | Adds Fatality\_Rate\_pct and Severity\_Index; saves the clean table | arithmetic on columns, `.to_csv` | clean CSV |
| 2.8 Supporting data | Cleans the Karnataka and India files the same way | `.melt`, `.pivot_table` | 2 clean CSVs |
| 2.9 Outliers | IQR fences and z-scores per year; station-vs-own-median check | `quantile`, `scipy.stats.zscore` | `02_boxplot_outliers.png`, 14 outliers, 2 anomalies |
| 3.1 Descriptive stats | describe() + median, skew, kurtosis, coefficient of variation; summaries by year and zone | `.describe()`, `.skew()`, `.kurt()` | `descriptive_statistics.csv` |
| 3.2–3.4 Trend, distributions, zones | City trend 2007–25, histograms, zone lines | `ax.bar`, `sns.histplot`, `sns.lineplot` | figures 03–05 |
| 3.5 Hotspots | Ranks stations on 2023–25 totals; station × year heatmap; Spearman rank stability | `pivot_table`, `rank`, `corr(method="spearman")` | figures 06–07, ρ = 0.80 |
| 3.6 Correlation | Pearson matrix (2018–23) and fatal-vs-total scatter | `.corr()`, `np.polyfit` | figures 08–09 |
| 3.7 Context | Karnataka and India comparison charts | `plt.barh` | figures 10–11 |
| 3.8 Save | Writes every slide number to JSON | `json.dump` | `key_numbers.json` |

The three lines that do most of the cleaning:

```python
st = stations_raw[~is_agg].copy()                       # drop total rows
st[c] = pd.to_numeric(st[c].str.replace(",", "").str.strip(),
                      errors="coerce").astype("Int64")  # text -> integer
st["Station"] = st["Station_raw"].replace(NAME_MAP)     # one name per station
```

Why two choices matter, in case you're asked:

- **`dtype=str` on load:** pandas would otherwise guess types and silently turn `"8,426"` into text or a wrong number. Reading as text and converting deliberately keeps control.
- **`Int64` (capital I), not `int64`:** the capital-I type allows blanks (`<NA>`). Plain `int64` cannot hold a blank, so you would have to fill missing deaths with 0, which would be false.

The outlier rule in plain words: a station-year is an outlier if it is more than 1.5 × IQR above the 75th percentile for that year, or its z-score is above 2.5.

```latex
\text{upper fence} = Q_3 + 1.5 \times (Q_3 - Q_1) \qquad z = \frac{x - \bar{x}}{s}
```

Every chunk explained line by line: [CODE_EXPLAINED_presentation2.md](CODE_EXPLAINED_presentation2.md)

## The Excel workbook

`Bengaluru_Road_Accidents_Dataset.xlsx` has 22 sheets: the full clean data, the full raw data, and every check and statistic as a live formula. Formulas recalculate when opened in Excel and match the Python output exactly.

| Sheet | What it shows | Slide it backs |
| --- | --- | --- |
| `README` | Sources, URLs, licence, sheet guide | 4 |
| `Data_Dictionary` | Each attribute, type, meaning | 6 |
| `Station_Crashes_Clean` | **The full 371-row clean dataset**; rate columns are formulas; orange cells = missing | 5, 9–17 |
| `City_Annual_2007_2025` | City totals with fatality-rate and year-on-year formulas | 10, 15 |
| `Karnataka_Districts` | Clean district panel, 150 rows | 5 |
| `India_Large_Cities` | 50 cities, Bengaluru highlighted | 5 |
| `Preprocessing_Log` | 18 steps: issue → rows affected → action → reason | 7, 9–12 |
| `Missing_Values` | COUNTBLANK by column and by year | 9 |
| `Validation_Checks` | Rule-check counts and the reconciliation table | 10 |
| `Outliers` | IQR / z-score outliers and the temporal anomalies | 12 |
| `Descriptive_Stats` | Mean, SD, quartiles, skew, kurtosis, CV, all as formulas | 13 |
| `Year_Summary`, `Zone_Summary` | SUMIFS totals by year and by zone | 5, 15 |
| `Station_Ranking_2023_25` | Station totals, fatality rate, RANK formulas; top 10 highlighted | 15, 16 |
| `Raw_*` (8 sheets) | Every source file exactly as downloaded | 4, 7 |

## Slides 1–8: Dataset collection & understanding

For each slide: the exact data on it, where that data comes from, and what to say. Speaker notes in the .pptx carry a shorter version.

### Slide 1 — Cover

**Data:** none; the credits line names the source (Bengaluru Traffic Police via OpenCity) and the Python libraries.

- Introduce the project: finding road accident hotspots in Bengaluru.
- Today covers exactly two topics from the brief: the dataset, then preprocessing and EDA.
- Everything shown was produced by our Python code on the real data.

### Slide 2 — Agenda

**Data:** none. The 9 bullets are the brief's own items.

- Part 01: source, description, attributes and data types, initial exploration.
- Part 02: missing values, duplicates, data-type correction, outliers, descriptive statistics and EDA.

### Slide 3 — Divider 01

**Data:** none. Transition to the dataset.

### Slide 4 — Where the data comes from

**Data \[1\]\[2\]\[3\]:** the 4 source datasets and raw row counts — station files 286 rows (45 + 45 + 63 + 65 + 68), city annual 19, Karnataka 39, India cities 51. Portal, CKAN API method, Public Domain licence and URL. Backed by the `README` and `Raw_*` sheets.

- We searched open-government portals; the best Bengaluru source is the Traffic Police station-wise data on OpenCity.
- One primary dataset (station-wise) and three supporting ones for city, state and national context.
- Limitation to state upfront: individual crash locations are not public, so the hotspot unit is the police station's area.

### Slide 5 — Dataset at a glance (dashboard)

**Data \[1\]:** 371 station-years, 54 stations, 8 years, 4 zones; 34,229 crashes and 5,941 fatal crashes (sum of `Total` and `Fatal`, 2018–2025, clean table). Stations reporting per year: 44, 44, 44, 44, 44, 48, 50, 53. Records per zone: West 122, South 88, North 86, East 75. **Data \[3\]:** Bengaluru #2 of 50 large cities in 2024, 4,769 accidents, 894 killed. **Data \[2\]:** 11.5% = Bengaluru City's 4,974 crashes ÷ Karnataka's 43,440 in 2023.

- One record = one police station in one year.
- Station count rises from 44 to 53 because BTP split jurisdictions in 2023–25; keep that in mind when comparing years.
- West has the most records because it has the most stations (16), not because it has the most crashes.
- Bengaluru is the 2nd-worst large city in India, so it matters.

### Slide 6 — Attributes and data types

**Data \[1\]:** the 8 attribute groups with statistical type and pandas dtype. Example values are K R Puram: East zone, Whitefield sub-division, 2025 = 34 fatal / 233 non-fatal / 267 total, fatality rate 12.73%; Killed 42 / Injured 217 and Severity Index 16.54 are from 2023 (the last year published).

- 3 nominal categories (where), 1 time variable (when), 5 discrete counts (what), 2 derived ratios.
- Red dtypes (`Int64`, `float64`) are the ones we created; everything loaded as text.
- Why ratios: a station with 250 crashes and one with 50 can't be compared on counts alone.

### Slide 7 — What the first look at the raw files showed

**Data \[1\]:** column counts per file 17, 12, 8, 6, 6 (rows 45, 45, 63, 65, 68). Console lines are real output: the last header of the 2018–20 file is `'2020 - Total Cases '` (trailing space) and the first city total is `'8,426'` (text). Issue counts: 50 total rows, 16 name variants, 22 re-zoned stations.

- This is what `df.shape`, `df.columns`, `df.head()` and `df.dtypes` revealed.
- The schema changes every year, so files can't simply be stacked.
- Each of the 6 issues becomes a preprocessing step in Part 02.

### Slide 8 — Divider 02

**Data:** none. Transition to preprocessing and EDA.

## Slides 9–17: Data preprocessing & EDA

### Slide 9 — Missing values are structural, not random

**Data \[1\]\[2\]:** chart `01_missing_heatmap.png`. Table: Killed 103 missing (27.76%), Injured 103 (27.76%), Sub\_division 5 (1.35%); Fatal, Non\_Fatal, Total 0. All 103 blanks are the 50 rows of 2024 + 53 rows of 2025. Karnataka: Vijayanagara blank for 2020–21. Backed by the `Missing_Values` sheet.

- The red blocks sit exactly on 2024–2025: BTP stopped publishing victim counts, so this is a publishing change, not random gaps.
- We did **not** fill them with averages, because that would invent deaths and injuries.
- Anything that needs Killed/Injured uses 2018–2023 only.

### Slide 10 — No duplicates, and every row passes the logic checks

**Data \[1\]:** four zeros: exact duplicates, duplicate Station–Year keys, rows where Fatal + Non-fatal ≠ Total, rows where Killed < Fatal. Reconciliation (station sum vs city table, Δ crashes / Δ fatal): 2018 0/+2, 2019 −4/+2, 2020 0/0, 2021 −2/−3, 2022 +1/−1, 2023 0/0, **2024 +31/−17**, **2025 −3/−36**. Backed by `Validation_Checks`.

- Checked with `df.duplicated()` on whole rows and on the (Station, Year) key.
- The file named 2020–2022 actually holds only 2021–22, so 2020 isn't counted twice.
- Station sums match BTP's own grand-total rows exactly; BTP's separate city table differs slightly. We documented this rather than silently picking one.

### Slide 11 — From text to typed, tidy data

**Data \[1\]:** the code panel is the real cleaning code; before → after types (`str`/`object` → `Int64`, `'East '` → `'East'`, `'8,426'` → 8426); 4 of the 16 name fixes.

- Read everything as text first, then convert on purpose.
- `Int64` keeps true blanks as `<NA>` instead of 0.
- Name mapping lets one station be followed across all 8 years (Tidy Data principle \[9\]).

### Slide 12 — Outliers are the hotspots, so we keep them

**Data \[1\]:** chart `02_boxplot_outliers.png`. 14 outlier station-years; most frequent K R Puram 5×, Yalahanka 4×, Int. Airport 2×, Whitefield 1× (Kengeri and Kamakshipalya 1× each too). Example: 2025 upper fence 220.5 crashes; K R Puram 267 and Yalahanka 257 exceed it. Temporal anomaly: K R Puram 2021 = 64 vs its 8-year median 247.5. Backed by `Outliers`.

- Two methods: Tukey's 1.5 × IQR rule \[10\] and z-score > 2.5, both within each year.
- These are real busy stations, not typos; removing them would delete the hotspots we are looking for.
- The 2021 K R Puram value is suspicious (a quarter of normal), so it's flagged, not deleted. Indiranagar 2021 (32 vs median 79.5) was flagged the same way.

### Slide 13 — Descriptive statistics per station-year

**Data \[1\]:** all 371 rows (268 for Killed).

| Variable | Mean | Median | SD | Min | Max | Skew | CV % |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Total | 92.3 | 77 | 59.4 | 7 | 283 | 1.01 | 64.4 |
| Fatal | 16.0 | 12 | 12.8 | 0 | 60 | 1.24 | 79.7 |
| Non-fatal | 76.3 | 64 | 48.5 | 5 | 241 | 1.00 | 63.6 |
| Killed | 16.5 | 12 | 13.4 | 1 | 63 | 1.21 | 81.2 |
| Fatality rate % | 17.0 | 16.6 | 7.3 | 0 | 52.6 | 0.92 | 42.9 |

- Mean (92.3) above median (77) = right-skewed: a few stations carry many crashes.
- CV of 64% means stations differ hugely, which is what makes hotspots possible.
- About 1 in 6 crashes is fatal. The 52.6% maximum is Pulikeshinagar (10 of 19), a small-number effect.

### Slide 14 — Crash counts are right-skewed

**Data \[1\]:** chart `04_distributions.png`; skew 1.01 (Total), 1.24 (Fatal), 0.92 (fatality rate).

- Half of all station-years fall between 48 and 125 crashes; a long tail goes past 250.
- The fatality rate is roughly bell-shaped around 17%.
- Skewed counts will matter for modelling later (e.g. log transform).

### Slide 15 — EDA dashboard

**Data \[1\]:** tiles −42% (8,426 crashes in 2007 → 4,893 in 2025, city table); 17.2% fatal share in 2025 (11.4% in 2007, peak 19.7% in 2022); top zone North; top station K R Puram. Charts:

- Total crashes per year 2007–2025 (city table, 19 values).
- Fatal % per year 2007–2025.
- Crashes by zone 2023–25: North 4,684 (928 fatal), West 3,687 (527), South 3,414 (580), East 2,879 (506).
- Top-6 stations 2023–25: K R Puram 762 (109 fatal), Yalahanka 735 (168), Kengeri 656 (115), Int. Airport 618 (161), Kamakshipalya 578 (81), Electronic City 552 (120).

Keynotes:

- Crashes fell 42% since 2007, but a bigger share are fatal: fewer crashes, deadlier ones.
- 2016 is a one-off spike and 2020–21 the COVID dip.
- North zone leads on volume and severity (19.8% fatal).
- K R Puram has the most crashes; Yalahanka has the most fatal ones. Volume and deaths give different hotspot lists.

### Slide 16 — The same stations stay on top year after year

**Data \[1\]:** chart `07_station_heatmap.png` (top 20 of the 43 stations reported every year). Spearman ρ = 0.80 between 2018 and 2025 ranks; about 0.92 between consecutive years.

- Darker cell = more crashes; Yalahanka and K R Puram are dark almost every year.
- High ρ means hotspots persist rather than moving around randomly \[11\].
- The single light cell in K R Puram's row is the flagged 2021 anomaly.

### Slide 17 — Severity does not follow volume

**Data \[1\]:** chart `08_correlation.png`, Pearson correlation over 2018–2023 (when every column exists). Fatal vs Total r = 0.89; Non-fatal, Injured and Total r = 0.97–0.99; fatality rate vs Total r = 0.05.

- Busy stations also have more fatal crashes (0.89).
- Non-fatal, Injured and Total are near-copies of each other, so use only one in a model.
- The key finding: how deadly a station's crashes are is **unrelated** to how many crashes it has (0.05). Severity needs its own explanation.

## Slides 18–21: Summary, references, close

### Slide 18 — Summary

**Data \[1\]:** recap numbers already shown: 371 records, 5 files, 54 stations; 50 total rows removed, 16 names harmonised, 0 duplicates; Killed/Injured missing after 2023; 14 outliers kept; crashes −42% since 2007, fatal share 17.2%; North, K R Puram and Yalahanka lead.

- One sentence per part: dataset, preprocessing, missing values and outliers, EDA.
- Close on the main insight: hotspots are stable over time, and severity behaves differently from volume.

### Slide 19 — References 1 of 2: datasets and Python libraries

**Data:** \[1\]–\[3\] the datasets with URLs and access date; \[4\]–\[8\] pandas, NumPy, SciPy, Matplotlib, seaborn. The last column lists the slides that cite each one, and each content slide carries a matching red "Sources: \[n\]" marker at the bottom right.

- Every number in the deck comes from \[1\]–\[3\].
- The Python code was written for this project from the libraries' official documentation; no third-party code was copied.

### Slide 20 — References 2 of 2: methods and literature

**Data:** \[9\] Wickham's Tidy Data (slide 11), \[10\] Tukey's IQR rule (slide 12), \[11\] Spearman correlation (slide 16), \[12\]–\[16\] the five papers from the Presentation 1 literature review, marked "Background\*".

- The papers shaped the project, but no figure here is taken from them, so they have no slide numbers.
- If asked about ML: those papers use K-means, DBSCAN, Random Forest and XGBoost on Indian crash data, which is where this project goes next.

### Slide 21 — Thank you / Q&A

**Data:** none.

- Offer the live demo: open `EDA_Bengaluru_Road_Accidents.ipynb` and run a cell (for example the missing-value or outlier cell).
- Point examiners to the workbook for the full dataset.
