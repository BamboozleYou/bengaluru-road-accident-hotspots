# Code explained — `hotspot_analysis/` (final AAT project)

The project is split into **4 modules, one per team member**, plus a shared helper file. They run in a fixed order because each module saves its results for the next one.

```
data/raw/*.csv ──► m1_data_acquisition ──► m2_preprocessing ──► m3_univariate_bivariate
                    (load + reshape)        (clean)              (1-2 variable analysis)
                                                     └────────► m4_multivariate_statistics
                                                                 (many variables, tests, index)
```

Run everything with:

```bash
cd hotspot_analysis/src
python run_all.py
```

All numbers quoted below are from the last full run (see `outputs/console/`).

---

## `common.py` — shared setup used by every module

| Part | What it does |
|---|---|
| `PROJECT`, `RAW`, `INTERIM`, `TABLES`, `FIG`, `CONSOLE` | Folder paths. `RAW` points to `../data/raw` (the 8 original CSVs). The other folders are created automatically under `hotspot_analysis/outputs/`. |
| `ZONE_ORDER`, `ZONE_COL`, `ZONE_MARK` | Fixed order, colour **and marker shape** for the 4 zones (North, East, West, South), so every chart uses the same colours and the zones are still distinguishable without colour. |
| `SEQ`, `DIV` | Colour scales for heatmaps: `SEQ` light→dark blue (amounts), `DIV` blue→grey→red (correlations from −1 to +1). |
| `sns.set_theme` / `plt.rcParams` | One chart style for every figure (font, light grid, no top/right borders). |
| `savefig(name)` | Saves the current chart as `outputs/figures/<name>.png` at 200 dpi, then closes it. |
| `step(name)` | A `with step("m2_missing"):` block prints normally **and** saves everything it printed to `outputs/console/m2_missing.txt`. Those text files are the real outputs used for screenshots. It works by temporarily replacing `sys.stdout` with `_Tee`, which writes to two places at once. |
| `save(obj, name)` / `load(name)` | Pass data between modules as pickle files in `outputs/interim/` (e.g. M2 saves the clean table as `st.pkl`, M3 and M4 load it). |
| `record(**kv)` | Adds headline numbers to `outputs/results.json` (one shared file of all key results). |
| `zone_legend(ax)` | Draws the same zone legend (colour + marker) on any chart. |

`run_all.py` deletes the old `results.json`, then runs M1 → M2 → M3 → M4 → `make_screenshots.py` in order with `runpy`.

---

## Module 1 — `m1_data_acquisition.py` (Member 1): load, inspect, reshape

**Goal:** read the raw data exactly as published, understand its structure, and turn five differently-shaped files into one table.

| Step | Code idea | Output |
|---|---|---|
| `m1_load` | `pd.read_csv(..., encoding="utf-8-sig", dtype=str)` for all 8 files. `utf-8-sig` removes the invisible BOM character at the start of some files; `dtype=str` reads everything as text so nothing is silently mis-converted. Builds an inventory of rows × columns per file. | `tables/raw_inventory.csv` |
| `m1_inspect` | Prints the first rows, the last column name with `repr()` (shows the trailing space in `'2020 - Total Cases '`), a city total stored as text (`'8,426'`), the column count of each station file (17, 12, 8, 6, 6) and the sub-total rows at the end of the 2025 file. | evidence of the data problems |
| `tidy_wide()` | Converts one **wide** file (one row per station, one column per year-and-measure) into **long** format (one row per station per year). The inner `pick()` tries each possible spelling of a column (`"2023 - Fatal Cases"`, `"2024-Fatal crashes"`, …) and returns the first that exists, or `NaN` if none does (e.g. Killed in 2024). | — |
| `m1_reshape` | Calls `tidy_wide` on the 5 station files, tags each row with its `Source_file`, and stacks them with `pd.concat`. | 421 rows (371 station rows + 50 total rows) |
| `m1_info` | `stations_raw.info()` — shows every column is still text (`object`). | |

Saves `raw.pkl` and `stations_raw.pkl` for Module 2.

---

## Module 2 — `m2_preprocessing.py` (Member 2): cleaning

**Goal:** fix every data-quality problem and document the before/after state.

| # | Step | What the code does | Result |
|---|---|---|---|
| 1 | `m2_aggregates` | Builds a True/False mask: station name contains "Total" **or** zone is blank **or** zone is "Total". Those rows are sub-totals, zone totals and grand totals, so they are removed (`st[~is_agg]`). Grand-total rows are kept aside for checking. | 50 rows removed → 371 |
| 2 | (before snapshot) | Counts missing values *before* cleaning for the before/after table. | |
| 3 | `m2_dtypes` | Strips spaces from text columns. For count columns: remove commas, strip, `pd.to_numeric(..., errors="coerce")`, then `.astype("Int64")` — pandas' integer type that **allows blanks**. | text → `Int64` |
| 4 | `m2_names` | `NAME_MAP` maps 16 old spellings to one name (e.g. `K.R.Pura` → `K R Puram`, `Ulsoor` → `Halasooru`). Zones were redrawn in 2023, so each station gets its **2025 zone** for every year (`groupby("Station").last()` then `.map()`); missing sub-divisions are back-filled the same way. | 16 names fixed, 22 stations re-zoned, 54 unique stations |
| 5 | `m2_missing` | `.isna().sum()` and `.isna().mean()*100` per column, and per year. Draws the missing-value map (`fig01`). Killed/Injured are missing for all of 2024–25 because the police stopped publishing them — **not imputed** (filling them would invent deaths). | 103 missing (27.8%) |
| 6 | `m2_duplicates` | Exact duplicates (same station, year and numbers) and duplicate keys (same station + year). | 0 and 0 |
| 7 | `m2_validity` | Six logic rules: no negative counts, Fatal + Non-fatal = Total, Killed ≥ Fatal, no zero-crash station, Fatal ≤ Total, year in range. Then a **reconciliation**: sum of stations vs the police's own Grand Total row vs the separate city table. | 0 violations; largest gap with city table 0.65% (2024) |
| 8 | `iqr_bounds` + `m2_outliers` | For each year: IQR fences (Q1 − 1.5·IQR, Q3 + 1.5·IQR) and z-scores (`scipy.stats.zscore`); a station-year is flagged if outside the fences or \|z\| > 2.5. A **sensitivity check** caps outliers at the fence and shows the mean only moves 92.3 → 91.3, so results are robust. Boxplot `fig02`. | 14 flagged (K R Puram 5×, Yalahanka 4×…), **kept** — they are the real hotspots |
| 9 | `m2_features` | New columns: `Fatality_Rate_pct` = Fatal ÷ Total × 100, `Killed_per_100`, `Injured_per_crash`, and `Period` (Pre-COVID 2018–19, COVID 2020–21, Post-COVID 2022–25) via `pd.cut`. | clean table 371 × 15 |
| — | `m2_supporting` | Cleans the 3 supporting files: city annual (adds fatality rate, year-on-year % change, z-score); Karnataka districts (`melt` → extract year with a regex → `pivot_table`; Vijayanagara 2020–21 dropped because the district didn't exist yet); India cities (commas removed, Total row dropped, killed per 100 accidents). | |

The end of the file writes all before/after tables to `outputs/tables/` and saves `st.pkl`, `city.pkl`, `ka.pkl`, `ind.pkl` for Modules 3 and 4.

---

## Module 3 — `m3_univariate_bivariate.py` (Member 3): one and two variables

**Goal:** describe each variable on its own, then relationships between pairs (year vs crashes, zone vs severity, volume vs deaths).

**Univariate (one variable at a time)**

| Step / figure | What it does | Key result |
|---|---|---|
| `m3_central_tendency` | Mean, median, mode, SD, min, max, skew for Total, Fatal, Non-fatal and fatality rate. | Total: mean 92.3 > median 77 → right-skewed |
| `fig03_hist_total` | Histogram of crashes per station-year with mean/median lines, plus a boxplot underneath. | |
| `fig04_hist_fatality_rate` | Histogram of fatality rate; marks how many station-years exceed 25%. | |
| `fig05_zone_share` | Each zone's % of all crashes and of fatal crashes, 2023–25. | |
| `m3_concentration` + `fig06` | Sorts stations by crashes and draws a **Lorenz/Pareto curve** (cumulative % of crashes vs % of stations). Computes the **Gini coefficient** (0 = all stations equal, 1 = one station has everything). | Top 10 stations = 40.1% of crashes; Gini = 0.35 |

**Bivariate (two variables)**

| Step / figure | What it does | Key result |
|---|---|---|
| `m3_city_trend` + `fig07` | Year vs total crashes 2007–2025. `stats.linregress` fits a straight trend line; `stats.kendalltau` tests for a steady trend without assuming a straight line. | −194 crashes/year, R² = 0.57, p = 0.0002 |
| `m3_severity_trend` + `fig08` | Same for fatality rate and killed per 100 crashes. | +0.46 percentage points/year (11.4% → 17.2%), p < 0.0001 |
| `m3_zone_year` + `fig09` | Crashes per zone per year (`groupby` + `unstack`). | |
| `m3_zone_kruskal` + `fig10` | Does fatality rate differ by zone? **Kruskal-Wallis** test (compares groups without assuming normal data) and a **chi-square** test on the fatal/non-fatal × zone table. | Yes: H = 44.1, p < 0.001; North 19.8% fatal vs West 14.3% |
| `m3_top_stations` + `fig11` | Ranks stations by total crashes 2023–25; stacked bars show the fatal part. | K R Puram 762, Yalahanka 735, Kengeri 656 |
| `m3_fatal_vs_total` + `fig12` | Scatter of fatal vs total crashes per station with a fitted line (`np.polyfit`). `Excess_Fatal` = actual − expected fatal crashes, i.e. stations **deadlier than their volume predicts**. | r = 0.92; Int. Airport +45.5, Yalahanka +29.3, Chikkajala +25.6 |
| `m3_change` + `fig13` | Compares each station's average 2018–19 vs 2024–25: which got better or worse. | 27 improved, 15 worsened; K S Layout −51%, Rajajinagar +51% |

---

## Module 4 — `m4_multivariate_statistics.py` (Member 4): many variables, tests, priority index

**Goal:** statistical summary, relationships among all variables, whether hotspots persist, a single ranking score, and comparison with Karnataka and India.

| Step / figure | What it does | Key result |
|---|---|---|
| `m4_describe` | Full descriptive statistics for 8 variables: count, mean, median, SD, quartiles, IQR, skew, kurtosis, coefficient of variation. | |
| `m4_period_stats` | Averages per period (Pre-COVID / COVID / Post-COVID). **Mann-Whitney U** tests whether post-COVID fatality rates are higher than pre-COVID; **Shapiro-Wilk** tests whether crash counts are normally distributed. | Yes, higher (p = 0.001); counts not normal (p < 0.001) → non-parametric tests are the right choice |
| `m4_correlation` + `fig14` | Pearson correlation matrix (2018–23, when every column exists), shown as a lower-triangle heatmap; Spearman check for fatality rate vs total. | Fatal–Total strong; fatality rate–Total ≈ 0 |
| `fig15_pairplot` | `sns.pairplot`: every pair of Total, Fatal and fatality rate, coloured by zone, with density curves on the diagonal. | |
| `m4_persistence` + `fig16`, `fig17` | Station × year heatmap for the 43 stations reported every year, and a Spearman rank-correlation matrix between years: do the same stations stay on top? Also finds stations in the top 10 **every** year. | ρ = 0.80 (2018 vs 2025), 0.88–0.95 year to year; Electronic City, Kamakshipalya, Peenya, Yalahanka top-10 all 8 years |
| `m4_zone_year_fr` + `fig18` | Fatality rate by zone and year as a heatmap (three variables in one chart). | |
| `m4_priority_index` + `fig19` | **Hotspot Priority Index (HPI)** per station, 2023–25. Each input is min-max scaled to 0–1 (`mm()`), then weighted: fatal crashes 40%, total crashes 30%, fatality rate 20%, recent trend (slope 2021–25) 10%; × 100. Tiers: Critical > 55, High 30–55, Monitor < 30. Robustness check: with equal weights, 9 of the top 10 stay the same. Bubble chart: volume vs fatality rate, bubble size = HPI. | #1 Yalahanka 91.6, #2 Int. Airport 80.7, #3 K R Puram 73.8; 7 Critical stations |
| `m4_karnataka` + `fig20` | Bengaluru vs other Karnataka districts, 2023. | 11.5% of the state's crashes; 18.4 deaths per 100 crashes vs state median 27.5 |
| `m4_india` + `fig21` | Bengaluru vs India's 50 million-plus cities, 2024. | #2 for accidents and deaths; 18.7 killed per 100 accidents vs median 28.1 |

---

## `make_screenshots.py` — code + output images

Creates `outputs/screenshots/ss01…ss32.png`, each showing one code block and the output it printed:

- `block()` uses Python's `ast` module to find the code inside a `with step("name"):` block (or a whole function) in the module file.
- `render()` turns code into a syntax-highlighted image with **pygments**.
- `shot()` stacks an "In [n]" code image above the matching "Out [n]" text from `outputs/console/`, so each screenshot is guaranteed to match the real run.

---

## Output folders

| Folder | Contents |
|---|---|
| `outputs/figures/` | 21 charts (`fig01`–`fig21`) |
| `outputs/tables/` | 18 CSV tables (clean data, statistics, outliers, rankings, HPI…) |
| `outputs/console/` | What each step printed (one `.txt` per step) |
| `outputs/screenshots/` | 32 code-and-output images |
| `outputs/results.json` | Every headline number in one file |
| `outputs/interim/` | Pickles passed between modules (recreated on every run, not in the repo) |
