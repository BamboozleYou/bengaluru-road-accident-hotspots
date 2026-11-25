# Code walkthrough — eda\_bangalore\_accidents.py

The script has 22 chunks (the notebook cells), run top to bottom. Each chunk below shows the code, then what it does line by line and what it produces. Line numbers refer to `eda_bangalore_accidents.py`.

## Setup (lines 10–50)

Loads the libraries, finds the project folders, and sets one chart style used by every figure.

```python
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from scipy import stats

BASE = Path(__file__).resolve().parent if "__file__" in globals() else Path.cwd()
RAW = BASE / "data" / "raw"
PROC = BASE / "data" / "processed"
FIG = BASE / "outputs" / "figures"

INK, MID, LIGHT, ACCENT = "#111111", "#6E6E6E", "#C8C8C8", "#D62828"
PALETTE = {"North": ACCENT, "East": INK, "West": MID, "South": LIGHT}
KEY = {}

def savefig(name):
    plt.tight_layout()
    plt.savefig(FIG / f"{name}.png", dpi=200, bbox_inches="tight")
    plt.close()
```

- **Libraries:** pandas for tables, NumPy for maths, SciPy for z-scores, Matplotlib and seaborn for charts.
- **`matplotlib.use("Agg")`** draws charts to files without opening windows, so the script runs anywhere. (The notebook leaves this out so charts show inline.)
- **`BASE`** is the folder the script sits in, so the paths work wherever you clone the repository. In a notebook there is no `__file__`, so it uses the current folder instead.
- **`RAW`, `PROC`, `FIG`** are the input folder, cleaned-data folder and chart folder; `mkdir(exist_ok=True)` creates them if missing.
- **Colours:** black, two greys and one red accent. `PALETTE` gives each zone a fixed colour, with North in red because it turns out to be the key zone. `MONO` (white → black) and `DIVERGE` (red → white → black) are colour scales for the two heatmaps.
- **`KEY = {}`** is an empty dictionary that collects every number the slides use; it is saved to `key_numbers.json` at the end.
- **`savefig()`** is a small helper: tidy the layout, save as a 200-dpi PNG in `outputs/figures/`, close the figure to free memory.

## Part 1 — Dataset collection & understanding

### 1.1 Load every raw file (lines 57–76)

```python
RAW_FILES = {"btp_2018_2020": "btp_station_2018_2020.csv", ..., "india_cities": "india_large_cities_2024.csv"}
raw = {k: pd.read_csv(RAW / f, encoding="utf-8-sig", dtype=str) for k, f in RAW_FILES.items()}

inventory = pd.DataFrame([{"dataset": k, "file": RAW_FILES[k],
                           "rows": df.shape[0], "columns": df.shape[1]} for k, df in raw.items()])
KEY["inventory"] = inventory.to_dict("records")
```

- `RAW_FILES` gives each of the 8 CSVs a short nickname.
- The dictionary comprehension reads all 8 into `raw`, so `raw["btp_2023"]` is the 2023 table.
- **`encoding="utf-8-sig"`** removes the invisible BOM character at the start of some files; without it the first column would be called `﻿Zone`.
- **`dtype=str`** reads every cell as text, so pandas can't guess wrongly (it would read `"8,426"` as text anyway, and mixed columns unpredictably). Types are fixed deliberately in 2.2.
- `inventory` is a small table of each file's rows × columns (`df.shape`). **Output:** 45×17, 45×12, 63×8, 65×6, 68×6, 19×5, 39×10, 51×14. Used on slides 4 and 7.

### 1.2 Inspect the raw structure (lines 81–92)

```python
for k, df in raw.items():
    print(f"=== {k}: shape {df.shape}")
    print("Columns:", [repr(c) for c in df.columns])
    print(df.head(3).to_string(index=False))

hdr_issues = [(k, c) for k, df in raw.items() for c in df.columns if c != c.strip()]
```

- Prints each file's shape, column names and first 3 rows: the "first look" from slide 7.
- `repr(c)` prints names in quotes, so a trailing space is visible: `'2020 - Total Cases '`.
- `hdr_issues` finds every header where `c != c.strip()`, i.e. one with spaces at either end.

### 1.3 Reshape to one tidy table (lines 98–133)

Each station file is **wide**: one row per station, one column per year-and-measure. This chunk makes it **long**: one row per station per year.

```python
def tidy_wide(df, years, has_subdiv):
    df = df.copy()
    df.columns = [c.strip() for c in df.columns]
    rows = []
    for _, r in df.iterrows():
        for y in years:
            def g(*names):
                for n in names:
                    if n in df.columns:
                        return r[n]
                return np.nan
            rows.append({"Zone_reported": r["Zone"],
                         "Sub_division": r["Sub-division"] if has_subdiv else np.nan,
                         "Station_raw": r["Station"], "Year": y,
                         "Fatal": g(f"{y} - Fatal", f"{y} - Fatal Cases", f"{y}-Fatal crashes"),
                         "Killed": g(f"{y} - Killed", f"{y} - Killed People"),
                         ...})
    return pd.DataFrame(rows)

parts = [tidy_wide(raw["btp_2018_2020"], [2018, 2019, 2020], False).assign(Source_file=...), ...]
stations_raw = pd.concat(parts, ignore_index=True)
```

- `df.columns = [c.strip() ...]` removes header spaces first.
- The two loops go through every station row (`iterrows`) and every year in that file, building one new row each time.
- **`g(*names)`** solves the changing column names: it tries each spelling in turn (`"2023 - Fatal Cases"`, `"2024-Fatal crashes"` …) and returns the first that exists. If none exists — e.g. Killed in 2024 — it returns `NaN` (missing).
- `has_subdiv` is False for 2018–22 because those files have no Sub-division column.
- `.assign(Source_file=...)` tags every row with its file, so any number can be traced back.
- `pd.concat` stacks the 5 results. **Output:** 421 rows × 10 columns (371 station rows + 50 total rows, removed next).

### 1.4 Data dictionary (lines 139–155)

```python
data_dictionary = pd.DataFrame([
    ["Zone", "Categorical (nominal)", "BTP traffic zone ... 2025 structure"],
    ["Fatal", "Integer (count, discrete)", "Number of fatal crashes (≥1 person died)"],
    ...], columns=["Attribute", "Data type", "Description"])
```

- A hand-written table of all 14 attributes, their statistical type and meaning. It is pure documentation: nothing is computed.
- Saved later as `data_dictionary.csv` and shown on slide 6.

## Part 2 — Data preprocessing

### 2.1 Remove total rows (lines 162–172)

```python
is_agg = (
    stations_raw["Station_raw"].fillna("").str.contains("Total", case=False)
    | stations_raw["Zone_reported"].isna()
    | stations_raw["Zone_reported"].str.strip().eq("Total")
)
agg_rows = stations_raw[is_agg]
grand_totals = agg_rows[agg_rows["Station_raw"].str.contains("Grand", na=False)].copy()
st = stations_raw[~is_agg].copy()
```

- `is_agg` is a True/False value per row. A row counts as a total if any of three tests is true (`|` means OR):
  1. its station name contains "Total" ("Total", "East Total", "Grand Total");
  2. its zone is blank (sub-division total rows have no zone);
  3. its zone is literally "Total".
- `fillna("")` avoids an error on blank names; `case=False` ignores capitals.
- `grand_totals` keeps the "Grand Total" rows aside, for the reconciliation check in 2.6.
- **`st = stations_raw[~is_agg]`** keeps only real station rows (`~` means NOT). `st` is the main table from here on. **Output:** 50 rows removed, 371 kept.

### 2.2 Fix data types (lines 178–186)

```python
NUM = ["Fatal", "Killed", "Non_Fatal", "Injured", "Total"]
for c in ["Zone_reported", "Sub_division", "Station_raw"]:
    st[c] = st[c].str.strip()
for c in NUM:
    st[c] = pd.to_numeric(st[c].str.replace(",", "", regex=False).str.strip(),
                          errors="coerce").astype("Int64")
st["Year"] = st["Year"].astype(int)
```

- `.str.strip()` removes leading and trailing spaces from text, so `"East "` becomes `"East"` and groups correctly.
- For each count column: remove commas (`"7,469"` → `"7469"`), strip spaces, then **`pd.to_numeric`** turns text into numbers.
- **`errors="coerce"`** turns anything that isn't a number into missing instead of crashing.
- **`.astype("Int64")`** (capital I) is pandas' integer type that allows blanks (`<NA>`). Plain `int64` can't hold a blank and would force you to put 0 for unknown deaths.
- The printed `dtypes BEFORE` / `AFTER` is the before/after table on slide 11.

### 2.3 Harmonise station names and zones (lines 192–218)

```python
NAME_MAP = {"Ulsoor": "Halasooru", "K.R.Pura": "K R Puram", "White Field": "Whitefield", ...}
st["Station"] = st["Station_raw"].replace(NAME_MAP)

latest_zone = st.sort_values("Year").groupby("Station")[["Zone_reported", "Sub_division"]].last()
st["Zone"] = st["Station"].map(latest_zone["Zone_reported"])
st["Sub_division"] = st["Sub_division"].fillna(st["Station"].map(latest_zone["Sub_division"]))
moved = st.loc[st["Zone"] != st["Zone_reported"], ["Station", "Zone_reported", "Zone"]].drop_duplicates()
```

- **`NAME_MAP`** is a hand-made lookup of 16 old spellings → one standard name. `.replace(NAME_MAP)` swaps them in a new `Station` column; the original stays in `Station_raw`.
- `UNMERGED_NOTES` (not used in calculations) records the deliberate choice *not* to merge Devanahalli with Int. Airport, because that link is unconfirmed.
- **Zones:** BTP redrew zones in 2023. `sort_values("Year").groupby("Station").last()` finds each station's most recent zone and sub-division.
- `.map(...)` then gives every row, in every year, that 2025 zone, so a zone means the same area across all 8 years.
- `.fillna(...)` back-fills the sub-division for 2018–22 rows, which had none.
- `moved` lists stations whose reported zone differs from their 2025 zone. **Output:** 16 names fixed, 22 stations re-zoned.

### 2.4 Missing values (lines 224–242)

```python
miss = pd.DataFrame({
    "missing_count": st[NUM + ["Sub_division"]].isna().sum(),
    "missing_pct": (st[NUM + ["Sub_division"]].isna().mean() * 100).round(2),
})
miss_by_year = st.groupby("Year")[NUM].apply(lambda d: d.isna().sum())

sns.heatmap(st.sort_values("Year")[NUM].isna().astype(int).T, cbar=False, cmap=["#EFEFEF", ACCENT])
savefig("01_missing_heatmap")
```

- **`.isna()`** marks each cell True if it is missing. `.sum()` counts the Trues per column; `.mean() * 100` gives the percentage (the mean of True/False is the share of Trues).
- `miss_by_year` repeats the count per year, which shows all 103 missing Killed/Injured values are in 2024 and 2025.
- **The heatmap:** each column is one record (sorted by year), each row a variable; `.astype(int)` turns True/False into 1/0, and the two-colour map paints missing cells red. `.T` flips it so variables run down the side.
- The extra `xticks` lines put a year label where each year's records start.
- **No imputation** is done: the comment in the code records the reason (it would invent deaths). **Output:** slide 9 table and `01_missing_heatmap.png`.

### 2.5 Duplicate records (lines 248–257)

```python
exact_dups = st.duplicated().sum()
key_dups = st.duplicated(subset=["Station", "Year"], keep=False)
print(st["Year"].value_counts().sort_index())
st = st.drop_duplicates(subset=["Station", "Year"], keep="first")
```

- **`st.duplicated()`** flags rows identical to an earlier row in every column; `.sum()` counts them.
- **`subset=["Station", "Year"]`** checks the stricter rule: one station must appear once per year, even if its numbers differ. `keep=False` flags all copies so you could see them.
- `value_counts()` on Year confirms 44 records each for 2018–2022, so 2020 isn't counted twice even though two file names mention 2020.
- `drop_duplicates` is a safety net; it removes nothing here. **Output:** 0 and 0 (slide 10).

### 2.6 Validation and reconciliation (lines 263–284)

```python
st["chk_total"] = (st["Fatal"] + st["Non_Fatal"]) == st["Total"]
st["chk_killed_ge_fatal"] = st["Killed"].isna() | (st["Killed"] >= st["Fatal"])
bad_total = st[~st["chk_total"]]

city = raw["city_annual"].copy()
for c in city.columns:
    city[c] = pd.to_numeric(city[c].str.replace(",", ""), errors="coerce").astype(int)
recon = (st.groupby("Year")[["Fatal", "Total"]].sum()
         .join(grand_totals...[["Fatal", "Total"]].add_suffix("_GrandTotalRow"))
         .join(city.set_index("Year")[["Fatal", "Total"]].add_suffix("_CityTable")))
recon["Total_diff_vs_city"] = recon["Total"] - recon["Total_CityTable"]
```

- **Rule 1:** fatal + non-fatal must equal total. **Rule 2:** people killed can't be fewer than fatal crashes (each fatal crash kills at least one). `Killed.isna() |` lets 2024–25 rows pass, since they have no Killed value to check.
- Each rule becomes a True/False column; `~` selects the failures. **Output:** 0 failures for both.
- **Reconciliation:** the city annual file is cleaned (commas removed, made integer). Then three versions of each year's total are lined up side by side with `.join`:
  1. our sum of the station rows (`groupby("Year").sum()`);
  2. BTP's own Grand Total row;
  3. BTP's separate city-level table.
- `add_suffix` renames columns so they don't clash. The difference column shows (1) and (2) match exactly, while (3) differs slightly (largest gap: 2025, 36 fewer fatal crashes). This is the slide 10 table.

### 2.7 Derived ratios and saving the clean table (lines 290–301)

```python
st["Fatality_Rate_pct"] = (st["Fatal"] / st["Total"] * 100).round(2)
st["Severity_Index"] = (st["Killed"] / st["Total"] * 100).round(2)
st = st[["Year", "Zone", ..., "Source_file"]].sort_values(["Year", "Zone", "Station"]).reset_index(drop=True)
st.to_csv(PROC / "bengaluru_station_crashes_2018_2025_clean.csv", index=False)
KEY["clean_shape"] = list(st.shape)
KEY["n_stations"] = int(st["Station"].nunique())
```

- **Fatality rate** = % of a station's crashes that were fatal. **Severity index** = people killed per 100 crashes; it is blank wherever Killed is blank (2024–25), automatically.
- Ratios let a 250-crash station be compared with a 50-crash one.
- The column list puts the 16 columns in a sensible order; `sort_values` orders rows by year, zone, station.
- **`to_csv`** writes the final clean dataset. The city table gets a fatality-rate column and is saved too.
- `KEY` stores 371 × 16, 54 stations and stations-per-year for slide 5.

### 2.8 Clean the supporting datasets (lines 307–329)

```python
ka = raw["ka_districts"].copy()
ka = ka[~ka["Sl No"].isna()].drop(columns="Sl No")
ka_long = ka.melt(id_vars="District", var_name="metric", value_name="value")
ka_long["Year"] = ka_long["metric"].str.extract(r"(\d{4})").astype(int)
ka_long["metric"] = ka_long["metric"].str.replace(r"\s*\d{4}", "", regex=True)
ka_clean = ka_long.pivot_table(index=["District", "Year"], columns="metric", values="value").reset_index()
ka_clean = ka_clean.dropna(subset=["Crashes"])
```

- **Karnataka:** rows with no serial number (the TOTAL row) are dropped.
- **`.melt`** turns the 8 year-columns into rows: (District, `"Road Crashes 2021"`, 1086) and so on.
- **`str.extract(r"(\d{4})")`** pulls the 4-digit year out of the column name using a regular expression; the second regex deletes the year, leaving just `"Road Crashes"` or `"Deaths"`.
- **`pivot_table`** spreads those two measures back into columns: one row per district per year.
- `dropna` removes Vijayanagara 2020–21 (district created in 2021). **Output:** 150 district-years.
- **India cities:** commas removed, text → numbers, the "Total" row dropped. **Output:** 50 cities.

### 2.9 Outlier detection (lines 335–391)

```python
def iqr_flags(s):
    q1, q3 = s.quantile([0.25, 0.75])
    iqr = q3 - q1
    return (s < q1 - 1.5 * iqr) | (s > q3 + 1.5 * iqr), q1 - 1.5 * iqr, q3 + 1.5 * iqr

for y, g in st.groupby("Year"):
    flags, lo, hi = iqr_flags(g["Total"].astype(float))
    z = np.abs(stats.zscore(g["Total"].astype(float)))
    for idx in g.index:
        if flags[idx] or z[g.index.get_loc(idx)] > 2.5:
            out_rows.append({...})
outliers = pd.DataFrame(out_rows)
```

- **`iqr_flags`** finds Q1 and Q3 (25th and 75th percentiles), IQR = Q3 − Q1, and flags values below Q1 − 1.5·IQR or above Q3 + 1.5·IQR (Tukey's rule). It also returns the fences.
- **`groupby("Year")`** runs the test separately for each year, because 2020–21 (COVID) have lower counts overall.
- **`stats.zscore`** gives how many standard deviations each station is from that year's mean; `np.abs` ignores the sign; > 2.5 is flagged.
- A station-year is recorded if either test flags it. **Output:** 14 outliers, all high (K R Puram 5×, Yalahanka 4× …), saved to `outliers_station_year.csv`.
- **The boxplot** (`sns.boxplot` + `sns.stripplot` dots coloured by zone) draws IQR outliers with red rings, labels each year's top station, and saves `02_boxplot_outliers.png` (slide 12).

```python
med = st.groupby("Station")["Total"].transform("median").astype(float)
st_ratio = st["Total"].astype(float) / med
temporal = st.loc[(st_ratio < 0.45) & (med >= 60), ["Year", "Station", "Total"]]
```

- **Temporal anomaly check:** compares each year with that station's own 8-year median (`transform` puts the median on every row). A year below 45% of normal, for a station that normally has at least 60 crashes, is flagged. **Output:** K R Puram 2021 (64 vs 247.5) and Indiranagar 2021 (32 vs 79.5).
- **City series:** z-score of non-fatal crashes and year-on-year % change (`pct_change`), which picks out the 2016 spike (+55%) and the 2020 COVID drop (−31%).
- Outliers are **kept**: they are the real hotspots, not data errors.

## Part 3 — Exploratory data analysis

### 3.1 Descriptive statistics (lines 398–426)

```python
desc = st[["Fatal", "Killed", "Non_Fatal", "Injured", "Total", "Fatality_Rate_pct", "Severity_Index"]].astype(float).describe().T
desc["median"] = st[desc.index].astype(float).median()
desc["skew"] = st[desc.index].astype(float).skew()
desc["kurtosis"] = st[desc.index].astype(float).kurt()
desc["CV_pct"] = desc["std"] / desc["mean"] * 100

by_year = st.groupby("Year").agg(Stations=("Station", "nunique"), Total=("Total", "sum"), ...)
zone_summary = st[st["Year"] >= 2023].groupby("Zone").agg(Total=("Total", "sum"), Fatal=("Fatal", "sum"), ...)
```

- **`.describe()`** gives count, mean, standard deviation, min, 25%, 50%, 75% and max for each variable; `.T` flips it so variables are rows.
- Four extra columns: **median**, **skew** (positive = long tail to the right), **kurtosis** (how heavy the tails are) and **CV** (SD as a % of the mean, i.e. spread relative to size).
- `.astype(float)` converts the nullable `Int64` columns to ordinary decimals so every statistic function treats them the same way; missing values are skipped automatically, which is why Killed has n = 268. **Output:** the slide 13 table.
- **`by_year`** uses named aggregation, `new_name=(column, function)`, to get stations, totals, mean and max per year.
- **`zone_summary`** totals crashes and fatal crashes per zone for 2023–25 and divides by station-years for a fair per-station rate. Used on the slide 15 dashboard. `zone_year.json` saves zone × year totals.

### 3.2 Long-term trend (lines 432–449)

```python
fig, ax1 = plt.subplots(figsize=(10, 4.2))
ax1.bar(city["Year"], city["Non_Fatal"], color=LIGHT, label="Non-fatal crashes")
ax1.bar(city["Year"], city["Fatal"], bottom=city["Non_Fatal"], color=INK, label="Fatal crashes")
ax2 = ax1.twinx()
ax2.plot(city["Year"], city["Fatality_Rate_pct"], color=ACCENT, marker="o", label="Fatality rate %")
ax1.axvspan(2019.5, 2021.5, color="#EEEEEE")
```

- Stacked bars: non-fatal at the bottom, fatal on top (`bottom=` stacks them).
- **`twinx()`** adds a second y-axis on the right for the red fatality-rate line, since % and counts have different scales.
- `axvspan` shades 2020–21 (COVID); `annotate` points at the 2016 spike.
- `KEY` stores the 2007 and 2025 fatality rates (11.4% → 17.2%). **Output:** `03_city_trend.png`; the same numbers feed the slide 15 dashboard charts.

### 3.3 Distributions (lines 455–462)

```python
fig, axes = plt.subplots(1, 3, figsize=(12, 3.8))
sns.histplot(st["Total"].astype(float), bins=20, kde=True, ax=axes[0], color=INK)
axes[0].set_title(f"Total crashes / station-year\nskew = {st['Total'].astype(float).skew():.2f}")
```

- Three histograms side by side (`subplots(1, 3)`), each with 20 bins.
- **`kde=True`** overlays a smooth density curve.
- The f-string writes each variable's skew into its title (`:.2f` = 2 decimals). **Output:** `04_distributions.png` (slide 14).

### 3.4 Zone comparison (lines 468–473)

```python
sns.lineplot(data=by_zone, x="Year", y="Total", hue="Zone", palette=PALETTE, marker="o")
```

- One line per zone (`hue="Zone"`), coloured by the fixed palette, over 2018–2025. **Output:** `05_zone_trend.png` (supporting chart; zone totals appear on the slide 15 dashboard).

### 3.5 Hotspot ranking, heatmap and rank stability (lines 479–515)

```python
recent = st[st["Year"] >= 2023].groupby(["Station", "Zone"]).agg(
    Total_3yr=("Total", "sum"), Fatal_3yr=("Fatal", "sum")).reset_index()
recent["Rank_Total"] = recent["Total_3yr"].rank(ascending=False, method="min").astype(int)
top = recent.sort_values("Total_3yr", ascending=False).head(12)

pivot = st.pivot_table(index="Station", columns="Year", values="Total").astype(float)
full = pivot.dropna()
full = full.loc[full.sum(axis=1).sort_values(ascending=False).index].head(20)
sns.heatmap(full, annot=True, fmt=".0f", cmap=MONO, ...)

rank = pivot.dropna().rank(ascending=False)
rho = rank.corr(method="spearman")
```

- **Ranking:** adds up each station's crashes and fatal crashes over 2023–25, then ranks them (1 = most). `method="min"` gives tied stations the same rank. Saved as `station_ranking_2023_2025.csv`; the top 6 are on the slide 15 dashboard.
- **Heatmap:** `pivot_table` builds a station × year grid of totals. `dropna()` keeps only the 43 stations reported in all 8 years (new stations would leave holes). The 20 with the highest 8-year sum are drawn, darker = more crashes, numbers printed in each cell (`annot=True`). **Output:** `07_station_heatmap.png` (slide 16).
- **Rank stability:** ranks the stations within each year, then correlates the year columns. A high Spearman ρ means the same stations stay near the top. **Output:** ρ = 0.80 (2018 vs 2025), about 0.92 between consecutive years.

### 3.6 Correlation (lines 521–546)

```python
corr_df = st[st["Year"] <= 2023][["Fatal", "Killed", "Non_Fatal", "Injured", "Total", "Fatality_Rate_pct"]].astype(float)
corr = corr_df.corr().round(2)
sns.heatmap(corr, annot=True, cmap=DIVERGE, vmin=-1, vmax=1, square=True)

m, b = np.polyfit(r["Total_3yr"], r["Fatal_3yr"], 1)
resid = r["Fatal_3yr"] - (m * r["Total_3yr"] + b)
```

- Uses **2018–2023 only**, because Killed and Injured don't exist after that.
- **`.corr()`** is Pearson correlation by default: +1 = move together, 0 = unrelated, −1 = opposite. `vmin=-1, vmax=1` fixes the colour scale so 0 is white. **Output:** `08_correlation.png` (slide 17): Fatal–Total 0.89, fatality rate–Total 0.05.
- **Scatter** of fatal vs total crashes per station: `np.polyfit(..., 1)` fits a straight line; `resid` is how far each station sits above or below it. Stations far above the line (Int. Airport, Yalahanka, Chikkajala) have more deaths than their crash volume predicts. **Output:** `09_fatal_vs_total.png` (in the outputs folder; not on a current slide).

### 3.7 Karnataka and India context (lines 552–569)

```python
ka23 = ka_clean[ka_clean["Year"] == 2023].sort_values("Crashes", ascending=False)
KEY["ka_blr_share_2023"] = round(float(ka23.loc[ka23.District == "Bengaluru City", "Crashes"].iloc[0]
                                       / ka23["Crashes"].sum() * 100), 1)
plt.barh(k["District"], k["Crashes"], color=[ACCENT if d == "Bengaluru City" else LIGHT for d in k["District"]])
```

- Bengaluru City's 2023 crashes divided by the state total → **11.5%** (slide 5).
- The list comprehension colours only Bengaluru red in the bar chart.
- The India block does the same with the 50 cities: top 10 by 2024 accidents, Bengaluru #2. **Output:** `10_karnataka.png`, `11_india_cities.png` (the numbers appear on slide 5).

### 3.8 Save the key numbers (lines 575–585)

```python
def _conv(o):
    if isinstance(o, (np.integer,)): return int(o)
    if isinstance(o, (np.floating,)): return float(o)
    return str(o)

with open(BASE / "outputs" / "key_numbers.json", "w") as f:
    json.dump(json.loads(json.dumps(KEY, default=_conv).replace("NaN", "null")), f, indent=2)
```

- JSON can't store NumPy number types, so **`_conv`** turns them into plain Python numbers.
- JSON also has no `NaN`; it is replaced by `null`.
- **`key_numbers.json`** holds every number on the slides, which is how the deck stays in sync with the code. The data dictionary CSV is saved last.

**Which charts are on the slides:** 01 (slide 9), 02 (12), 04 (14), 07 (16), 08 (17). The slide 5 and 15 dashboards are drawn in PowerPoint from the same numbers. Charts 03, 05, 06, 09, 10 and 11 are extra outputs for the notebook demo.
