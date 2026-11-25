# %% [markdown]
# # Road Accident Hotspot Analysis – Bengaluru, India
# ## Presentation 2: Dataset Collection & Understanding + Data Preprocessing & EDA
#
# **Primary dataset:** Bengaluru Traffic Police (BTP) – police-station-wise road crashes, 2018–2025
# **Supporting datasets:** Bengaluru city annual crashes 2007–2025, Karnataka district-wise crashes 2020–2023,
# MoRTH large-city road accidents 2023–2024.
# **Source:** OpenCity – Urban Data Portal (data.opencity.in), licence: Public Domain.

# %%
import json
import warnings
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from scipy import stats

warnings.filterwarnings("ignore")
pd.set_option("display.width", 160)
pd.set_option("display.max_columns", 30)

BASE = Path(__file__).resolve().parent if "__file__" in globals() else Path.cwd()
RAW = BASE / "data" / "raw"
PROC = BASE / "data" / "processed"
FIG = BASE / "outputs" / "figures"
for d in (PROC, FIG):
    d.mkdir(parents=True, exist_ok=True)

# Monochrome "Swiss" style: black / greys + one signal-red accent
INK, MID, LIGHT, ACCENT = "#111111", "#6E6E6E", "#C8C8C8", "#D62828"
sns.set_theme(style="white", font="Arial")
plt.rcParams.update({"axes.edgecolor": INK, "axes.labelcolor": INK, "xtick.color": INK, "ytick.color": INK,
                     "axes.titleweight": "bold", "axes.titlesize": 12, "axes.spines.top": False,
                     "axes.spines.right": False, "axes.grid": True, "axes.grid.axis": "y",
                     "grid.color": "#E6E6E6", "grid.linewidth": 0.6})
PALETTE = {"North": ACCENT, "East": INK, "West": MID, "South": LIGHT}
MONO = matplotlib.colors.LinearSegmentedColormap.from_list("mono", ["#FFFFFF", "#BDBDBD", INK])
DIVERGE = matplotlib.colors.LinearSegmentedColormap.from_list("div", [ACCENT, "#FFFFFF", INK])
KEY = {}  # key numbers collected for the presentation


def savefig(name):
    plt.tight_layout()
    plt.savefig(FIG / f"{name}.png", dpi=200, bbox_inches="tight")
    plt.close()


# %% [markdown]
# ## PART 1 – DATASET COLLECTION & UNDERSTANDING
# ### 1.1 Load every raw file exactly as published

# %%
RAW_FILES = {
    "btp_2018_2020": "btp_station_2018_2020.csv",
    "btp_2021_2022": "btp_station_2020_2022.csv",
    "btp_2023": "btp_station_2023.csv",
    "btp_2024": "btp_station_2024.csv",
    "btp_2025": "btp_station_2025.csv",
    "city_annual": "blr_crashes_2007_2025.csv",
    "ka_districts": "ka_district_2020_2023.csv",
    "india_cities": "india_large_cities_2024.csv",
}
# utf-8-sig strips the invisible BOM character some files start with
raw = {k: pd.read_csv(RAW / f, encoding="utf-8-sig", dtype=str) for k, f in RAW_FILES.items()}

inventory = pd.DataFrame(
    [{"dataset": k, "file": RAW_FILES[k], "rows": df.shape[0], "columns": df.shape[1]} for k, df in raw.items()]
)
print("RAW FILE INVENTORY")
print(inventory.to_string(index=False))
KEY["inventory"] = inventory.to_dict("records")

# %% [markdown]
# ### 1.2 Inspect structure: columns, sample rows, dtypes (as loaded)

# %%
for k, df in raw.items():
    print(f"\n=== {k}: shape {df.shape}")
    print("Columns:", [repr(c) for c in df.columns])
    print(df.head(3).to_string(index=False))

# Problems visible already: trailing spaces in headers ('2020 - Fatal '),
# numbers stored as text with thousands separators ('7,469'), subtotal/total rows mixed with data rows,
# different column sets per year, and station names that change spelling across years.
hdr_issues = [(k, c) for k, df in raw.items() for c in df.columns if c != c.strip()]
print("\nHeaders with stray whitespace:", hdr_issues)
KEY["header_issues"] = [f"{k}: '{c}'" for k, c in hdr_issues]

# %% [markdown]
# ### 1.3 Reshape the five BTP station files into ONE tidy long table (station × year)

# %%
def tidy_wide(df, years, has_subdiv):
    """Convert a 'YYYY - Metric' wide file to long format."""
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
            rows.append({
                "Zone_reported": r["Zone"],
                "Sub_division": r["Sub-division"] if has_subdiv else np.nan,
                "Station_raw": r["Station"],
                "Year": y,
                "Fatal": g(f"{y} - Fatal", f"{y} - Fatal Cases", f"{y}-Fatal crashes"),
                "Killed": g(f"{y} - Killed", f"{y} - Killed People"),
                "Non_Fatal": g(f"{y} - Non-Fatal", f"{y}-Non Fatal"),
                "Injured": g(f"{y} - Injured", f"{y} - Injured People"),
                "Total": g(f"{y} - Total Cases", f"{y}-Total crashes"),
            })
    return pd.DataFrame(rows)


parts = [
    tidy_wide(raw["btp_2018_2020"], [2018, 2019, 2020], False).assign(Source_file=RAW_FILES["btp_2018_2020"]),
    tidy_wide(raw["btp_2021_2022"], [2021, 2022], False).assign(Source_file=RAW_FILES["btp_2021_2022"]),
    tidy_wide(raw["btp_2023"], [2023], True).assign(Source_file=RAW_FILES["btp_2023"]),
    tidy_wide(raw["btp_2024"], [2024], True).assign(Source_file=RAW_FILES["btp_2024"]),
    tidy_wide(raw["btp_2025"], [2025], True).assign(Source_file=RAW_FILES["btp_2025"]),
]
stations_raw = pd.concat(parts, ignore_index=True)
print("Combined long table (before cleaning):", stations_raw.shape)
print(stations_raw.head())

# %% [markdown]
# ### 1.4 Data dictionary – attributes and data types

# %%
data_dictionary = pd.DataFrame([
    ["Zone", "Categorical (nominal)", "BTP traffic zone (East / West / North / South) – 2025 structure"],
    ["Zone_reported", "Categorical (nominal)", "Zone exactly as printed in that year's file (zones were reorganised in 2023)"],
    ["Sub_division", "Categorical (nominal)", "Traffic sub-division (published only from 2023)"],
    ["Station", "Categorical (nominal)", "Traffic police station – the spatial unit for hotspot analysis (harmonised name)"],
    ["Station_raw", "Text", "Station name exactly as published"],
    ["Year", "Integer (ordinal / time)", "Calendar year of the crashes, 2018–2025"],
    ["Fatal", "Integer (count, discrete)", "Number of fatal crashes (≥1 person died)"],
    ["Killed", "Integer (count, discrete)", "Number of persons killed (not published for 2024–2025)"],
    ["Non_Fatal", "Integer (count, discrete)", "Number of non-fatal (injury) crashes"],
    ["Injured", "Integer (count, discrete)", "Number of persons injured (not published for 2024–2025)"],
    ["Total", "Integer (count, discrete)", "Total crashes = Fatal + Non_Fatal"],
    ["Fatality_Rate_pct", "Float (ratio, derived)", "Fatal / Total × 100 – share of crashes that were fatal"],
    ["Severity_Index", "Float (ratio, derived)", "Killed per 100 crashes (2018–2023 only)"],
    ["Source_file", "Text", "Raw file the record came from (lineage)"],
], columns=["Attribute", "Data type", "Description"])
print(data_dictionary.to_string(index=False))

# %% [markdown]
# ## PART 2 – DATA PREPROCESSING
# ### 2.1 Remove aggregate rows (sub-totals / zone totals / grand totals)

# %%
is_agg = (
    stations_raw["Station_raw"].fillna("").str.contains("Total", case=False)
    | stations_raw["Zone_reported"].isna()
    | stations_raw["Zone_reported"].str.strip().eq("Total")
)
agg_rows = stations_raw[is_agg]
print(f"Aggregate rows found: {len(agg_rows)} (removed from the record-level table, kept for validation)")
print(agg_rows[["Year", "Zone_reported", "Sub_division", "Station_raw", "Total"]].to_string(index=False))
KEY["agg_rows_removed"] = int(len(agg_rows))
grand_totals = agg_rows[agg_rows["Station_raw"].str.contains("Grand", na=False)].copy()
st = stations_raw[~is_agg].copy()

# %% [markdown]
# ### 2.2 Data-type correction (text → numeric, strip whitespace, categories)

# %%
NUM = ["Fatal", "Killed", "Non_Fatal", "Injured", "Total"]
print("dtypes BEFORE:\n", st.dtypes.to_string())
for c in ["Zone_reported", "Sub_division", "Station_raw"]:
    st[c] = st[c].str.strip()
for c in NUM:
    st[c] = pd.to_numeric(st[c].str.replace(",", "", regex=False).str.strip(), errors="coerce").astype("Int64")
st["Year"] = st["Year"].astype(int)
grand_totals["Total"] = pd.to_numeric(grand_totals["Total"], errors="coerce")
grand_totals["Fatal"] = pd.to_numeric(grand_totals["Fatal"], errors="coerce")

# %% [markdown]
# ### 2.3 Harmonise station names (same station, different spellings across years)

# %%
NAME_MAP = {
    "Ulsoor": "Halasooru", "K.R.Pura": "K R Puram", "White Field": "Whitefield", "HuliMavu": "Hulimavu",
    "Mico layout": "Micolayout", "K.Swamy Lyt.": "K S Layout", "RT Nagar": "R T Nagar",
    "Yelahanka": "Yalahanka", "Chikjala": "Chikkajala", "Malleswaram": "Malleshwaram",
    "Y.Pura": "Yashawanthapura", "B.Pura": "Bytarayanapura", "Chamarajapet": "Chamarajpet",
    "Int. Aiport": "Int. Airport", "F.Town": "Pulikeshinagar", "Chickpet": "Sheshadripuram/Chickpet",
}
# Low-confidence links are NOT merged (kept separate, documented):
UNMERGED_NOTES = {
    "Devanahalli": "Likely predecessor of 'Int. Airport' (both cover the KIA corridor) – not merged, unverified",
    "Vijayanagar/Magadi Road": "Continuous names – no change needed",
}
st["Station"] = st["Station_raw"].replace(NAME_MAP)
name_changes = (st.loc[st["Station"] != st["Station_raw"], ["Station_raw", "Station"]]
                .drop_duplicates().sort_values("Station").reset_index(drop=True))
print("Station names harmonised:")
print(name_changes.to_string(index=False))
KEY["names_harmonised"] = int(len(name_changes))

# Zone: use the 2025 zone structure for every year so zones are comparable over time
latest_zone = (st.sort_values("Year").groupby("Station")[["Zone_reported", "Sub_division"]].last())
st["Zone"] = st["Station"].map(latest_zone["Zone_reported"])
st["Sub_division"] = st["Sub_division"].fillna(st["Station"].map(latest_zone["Sub_division"]))
moved = st.loc[st["Zone"] != st["Zone_reported"], ["Station", "Zone_reported", "Zone"]].drop_duplicates()
print(f"\nStations whose zone changed in the 2023 reorganisation: {moved['Station'].nunique()}")
print(moved.to_string(index=False))
KEY["zone_moved"] = int(moved["Station"].nunique())

# %% [markdown]
# ### 2.4 Missing values

# %%
miss = pd.DataFrame({
    "missing_count": st[NUM + ["Sub_division"]].isna().sum(),
    "missing_pct": (st[NUM + ["Sub_division"]].isna().mean() * 100).round(2),
})
print("Missing values per column (station table):\n", miss)
miss_by_year = st.groupby("Year")[NUM].apply(lambda d: d.isna().sum())
print("\nMissing by year:\n", miss_by_year)
KEY["missing_table"] = miss.reset_index().rename(columns={"index": "column"}).to_dict("records")

plt.figure(figsize=(8, 3.6))
sns.heatmap(st.sort_values("Year")[NUM].isna().astype(int).T, cbar=False, cmap=["#EFEFEF", ACCENT])
yr_pos = st.sort_values("Year").reset_index(drop=True).groupby("Year").apply(lambda d: d.index.min())
plt.xticks(yr_pos.values, yr_pos.index, rotation=0)
plt.title("Missing-value map (red = missing) – station records ordered by year")
savefig("01_missing_heatmap")

# Decision: Killed / Injured for 2024-25 are *structurally* missing (BTP stopped publishing them).
# They are NOT imputed – imputing victim counts would invent data. Analyses that need them use 2018-2023.
# Total is complete; Fatal + Non_Fatal are complete.

# %% [markdown]
# ### 2.5 Duplicate records

# %%
exact_dups = st.duplicated().sum()
key_dups = st.duplicated(subset=["Station", "Year"], keep=False)
print("Exact duplicate rows:", exact_dups)
print("Duplicate (Station, Year) keys:", key_dups.sum())
print(st[key_dups].to_string(index=False) if key_dups.any() else "None")
# The two files '2018-2020' and '2020-2022' overlap in name – check 2020 does not appear twice
print("Records per year:\n", st["Year"].value_counts().sort_index().to_string())
KEY["exact_dups"] = int(exact_dups)
KEY["key_dups"] = int(key_dups.sum())
st = st.drop_duplicates(subset=["Station", "Year"], keep="first")

# %% [markdown]
# ### 2.6 Consistency / validity checks

# %%
st["chk_total"] = (st["Fatal"] + st["Non_Fatal"]) == st["Total"]
st["chk_killed_ge_fatal"] = st["Killed"].isna() | (st["Killed"] >= st["Fatal"])
bad_total = st[~st["chk_total"]]
bad_killed = st[~st["chk_killed_ge_fatal"]]
print(f"Rows where Fatal + Non_Fatal != Total: {len(bad_total)}")
print(bad_total[["Year", "Station", "Fatal", "Non_Fatal", "Total"]].to_string(index=False))
print(f"Rows where Killed < Fatal (impossible): {len(bad_killed)}")
KEY["bad_total"] = int(len(bad_total))
KEY["bad_killed"] = int(len(bad_killed))
KEY["bad_total_rows"] = bad_total[["Year", "Station", "Fatal", "Non_Fatal", "Total"]].astype(str).to_dict("records")

# Reconcile sum of stations vs published Grand Total vs city-level annual table
city = raw["city_annual"].copy()
for c in city.columns:
    city[c] = pd.to_numeric(city[c].str.replace(",", ""), errors="coerce").astype(int)
city.columns = ["Year", "Fatal", "Killed", "Non_Fatal", "Total"]
recon = (st.groupby("Year")[["Fatal", "Total"]].sum()
         .join(grand_totals.set_index(grand_totals["Year"].astype(int))[["Fatal", "Total"]].add_suffix("_GrandTotalRow"))
         .join(city.set_index("Year")[["Fatal", "Total"]].add_suffix("_CityTable")))
recon["Total_diff_vs_city"] = recon["Total"] - recon["Total_CityTable"]
print("\nReconciliation of totals:\n", recon)
KEY["recon"] = recon.reset_index().astype(int).to_dict("records")

# %% [markdown]
# ### 2.7 Feature engineering (derived ratios)

# %%
st["Fatality_Rate_pct"] = (st["Fatal"] / st["Total"] * 100).round(2)
st["Severity_Index"] = (st["Killed"] / st["Total"] * 100).round(2)
st = st[["Year", "Zone", "Zone_reported", "Sub_division", "Station", "Station_raw",
         "Fatal", "Killed", "Non_Fatal", "Injured", "Total", "Fatality_Rate_pct", "Severity_Index",
         "chk_total", "chk_killed_ge_fatal", "Source_file"]].sort_values(["Year", "Zone", "Station"]).reset_index(drop=True)
print("dtypes AFTER:\n", st.dtypes.to_string())
st.to_csv(PROC / "bengaluru_station_crashes_2018_2025_clean.csv", index=False)
city["Fatality_Rate_pct"] = (city["Fatal"] / city["Total"] * 100).round(2)
city.to_csv(PROC / "bengaluru_city_annual_2007_2025_clean.csv", index=False)
KEY["clean_shape"] = list(st.shape)
KEY["n_stations"] = int(st["Station"].nunique())
KEY["stations_per_year"] = st.groupby("Year")["Station"].nunique().to_dict()

# %% [markdown]
# ### 2.8 Supporting datasets – clean the same way

# %%
ka = raw["ka_districts"].copy()
ka = ka[ka["District"].notna() & (ka["District"].str.strip() != "")]
ka = ka[~ka["Sl No"].isna()].drop(columns="Sl No")
ka_long = ka.melt(id_vars="District", var_name="metric", value_name="value")
ka_long["Year"] = ka_long["metric"].str.extract(r"(\d{4})").astype(int)
ka_long["metric"] = ka_long["metric"].str.replace(r"\s*\d{4}", "", regex=True)
ka_long["value"] = pd.to_numeric(ka_long["value"], errors="coerce")
ka_clean = ka_long.pivot_table(index=["District", "Year"], columns="metric", values="value").reset_index()
ka_clean.columns.name = None
ka_clean = ka_clean.rename(columns={"Road Crashes": "Crashes"})
print("Karnataka missing values:\n", ka_clean[ka_clean.isna().any(axis=1)])
# Vijayanagara district was carved out of Ballari in 2021 -> 2020/2021 legitimately empty
ka_clean = ka_clean.dropna(subset=["Crashes"])
ka_clean["Deaths_per_100_crashes"] = (ka_clean["Deaths"] / ka_clean["Crashes"] * 100).round(1)
ka_clean.to_csv(PROC / "karnataka_districts_2020_2023_clean.csv", index=False)

ind = raw["india_cities"].copy()
ind = ind[ind["City"].notna()]
for c in ind.columns.drop("City"):
    ind[c] = pd.to_numeric(ind[c].str.replace(",", ""), errors="coerce")
ind = ind[~ind["City"].str.contains("Total", case=False)]
ind.to_csv(PROC / "india_large_cities_2023_2024_clean.csv", index=False)
print("India cities shape:", ind.shape)

# %% [markdown]
# ### 2.9 Outlier detection – IQR and Z-score on station totals

# %%
def iqr_flags(s):
    q1, q3 = s.quantile([0.25, 0.75])
    iqr = q3 - q1
    return (s < q1 - 1.5 * iqr) | (s > q3 + 1.5 * iqr), q1 - 1.5 * iqr, q3 + 1.5 * iqr


out_rows = []
for y, g in st.groupby("Year"):
    flags, lo, hi = iqr_flags(g["Total"].astype(float))
    z = np.abs(stats.zscore(g["Total"].astype(float)))
    for idx in g.index:
        if flags[idx] or z[g.index.get_loc(idx)] > 2.5:
            out_rows.append({"Year": y, "Station": g.at[idx, "Station"], "Zone": g.at[idx, "Zone"],
                             "Total": int(g.at[idx, "Total"]), "IQR_upper_fence": round(hi, 1),
                             "Z_score": round(float(z[g.index.get_loc(idx)]), 2),
                             "IQR_outlier": bool(flags[idx]), "Z_outlier(>2.5)": bool(z[g.index.get_loc(idx)] > 2.5)})
outliers = pd.DataFrame(out_rows)
print("Outlier station-years:\n", outliers.to_string(index=False))
KEY["outliers"] = outliers.to_dict("records")
KEY["outlier_station_counts"] = outliers["Station"].value_counts().to_dict()
outliers.to_csv(PROC / "outliers_station_year.csv", index=False)

plt.figure(figsize=(11, 4.6))
sns.boxplot(data=st, x="Year", y="Total", color="#F2F2F2", linecolor=INK, fliersize=0)
iqr_out = outliers[outliers["IQR_outlier"]]
is_out = st.set_index(["Year", "Station"]).index.isin(iqr_out.set_index(["Year", "Station"]).index)
sns.stripplot(data=st[~is_out], x="Year", y="Total", hue="Zone", hue_order=list(PALETTE), palette=PALETTE,
              size=4, jitter=0.2, alpha=.9, edgecolor=INK, linewidth=0.3)
plt.scatter(iqr_out["Year"] - 2018, iqr_out["Total"], s=110, facecolors="none", edgecolors=ACCENT,
            lw=2, label="IQR outlier (red ring)", zorder=5)
plt.scatter(iqr_out["Year"] - 2018, iqr_out["Total"], s=22, c=iqr_out["Zone"].map(PALETTE), edgecolors=INK, lw=0.5, zorder=6)
for y, g in st.groupby("Year"):  # label only the highest station each year to keep the chart readable
    r = g.loc[g["Total"].astype(float).idxmax()]
    plt.annotate(r["Station"], (y - 2018, r["Total"]), fontsize=7.5, xytext=(0, 7), textcoords="offset points", ha="center")
plt.ylim(0, 320)
plt.title("Crashes per police station by year – red-ringed points are IQR outliers (highest station labelled)")
plt.ylabel("Total crashes")
plt.legend(title="Zone", fontsize=8, bbox_to_anchor=(1.01, 1), loc="upper left")
savefig("02_boxplot_outliers")

# Temporal anomalies: a station-year far below that station's own median (possible reporting gap)
med = st.groupby("Station")["Total"].transform("median").astype(float)
st_ratio = st["Total"].astype(float) / med
temporal = st.loc[(st_ratio < 0.45) & (med >= 60), ["Year", "Station", "Total"]].assign(
    Station_median=med[(st_ratio < 0.45) & (med >= 60)], Ratio_to_median=st_ratio[(st_ratio < 0.45) & (med >= 60)].round(2))
print("Temporal anomalies (year < 45% of station's own median):\n", temporal.to_string(index=False))
KEY["temporal_anomalies"] = temporal.to_dict("records")
temporal.to_csv(PROC / "temporal_anomalies.csv", index=False)

# City-level time series outliers (year-on-year)
city["Non_Fatal_z"] = stats.zscore(city["Non_Fatal"]).round(2)
city["YoY_change_pct"] = (city["Total"].pct_change() * 100).round(1)
print("\nCity annual series with z-scores and YoY change:\n", city.to_string(index=False))
KEY["city"] = city.to_dict("records")

# Decision: outliers are REAL high-crash stations (they are the hotspots we want to find),
# not data-entry errors -> retained. 2016 city spike (+55% non-fatal) and 2020-21 COVID dip are flagged.

# %% [markdown]
# ## PART 3 – EXPLORATORY DATA ANALYSIS & DESCRIPTIVE STATISTICS
# ### 3.1 Descriptive statistics

# %%
desc = st[["Fatal", "Killed", "Non_Fatal", "Injured", "Total", "Fatality_Rate_pct", "Severity_Index"]].astype(float).describe().T
desc["median"] = st[desc.index].astype(float).median()
desc["skew"] = st[desc.index].astype(float).skew()
desc["kurtosis"] = st[desc.index].astype(float).kurt()
desc["CV_pct"] = desc["std"] / desc["mean"] * 100
desc = desc.round(2)
print("Descriptive statistics – all station-years:\n", desc)
KEY["desc"] = desc.reset_index().rename(columns={"index": "variable"}).to_dict("records")
desc.to_csv(PROC / "descriptive_statistics.csv")

by_year = st.groupby("Year").agg(Stations=("Station", "nunique"), Total=("Total", "sum"), Fatal=("Fatal", "sum"),
                                  Mean_per_station=("Total", "mean"), Median_per_station=("Total", "median"),
                                  Std=("Total", "std"), Max=("Total", "max")).round(1)
by_year["Fatality_Rate_pct"] = (by_year["Fatal"] / by_year["Total"] * 100).round(2)
print("\nBy year:\n", by_year)
KEY["by_year"] = by_year.reset_index().to_dict("records")

by_zone = st.groupby(["Zone", "Year"])[["Total", "Fatal"]].sum().reset_index()
zone_summary = st[st["Year"] >= 2023].groupby("Zone").agg(Total=("Total", "sum"), Fatal=("Fatal", "sum"),
                                                          Stations=("Station", "nunique"),
                                                          Station_years=("Station", "size")).reset_index()
zone_summary["Fatality_Rate_pct"] = (zone_summary["Fatal"] / zone_summary["Total"] * 100).round(2)
zone_summary["Crashes_per_station_per_yr"] = (zone_summary["Total"] / zone_summary["Station_years"]).round(1)
print("\nZone summary 2023–2025:\n", zone_summary)
KEY["zone_summary"] = zone_summary.to_dict("records")
zone_year = by_zone.pivot(index="Zone", columns="Year", values="Total").astype(int)
(BASE / "outputs").mkdir(exist_ok=True)
with open(BASE / "outputs" / "zone_year.json", "w") as f:
    json.dump({z: {str(y): int(v) for y, v in r.items()} for z, r in zone_year.iterrows()}, f, indent=1)

# %% [markdown]
# ### 3.2 Long-term trend – Bengaluru 2007–2025

# %%
fig, ax1 = plt.subplots(figsize=(10, 4.2))
ax1.bar(city["Year"], city["Non_Fatal"], color=LIGHT, label="Non-fatal crashes")
ax1.bar(city["Year"], city["Fatal"], bottom=city["Non_Fatal"], color=INK, label="Fatal crashes")
ax1.set_ylabel("Crashes")
ax2 = ax1.twinx()
ax2.plot(city["Year"], city["Fatality_Rate_pct"], color=ACCENT, marker="o", lw=2.4, label="Fatality rate %")
ax2.set_ylabel("Fatal / total (%)")
ax2.grid(False)
ax1.axvspan(2019.5, 2021.5, color="#EEEEEE", alpha=1, zorder=0)
ax1.text(2020.5, 3500, "COVID", ha="center", fontsize=9)
ax1.annotate("2016 spike", (2016, 7506), xytext=(2016.6, 8400), arrowprops=dict(arrowstyle="->"), fontsize=9)
h1, l1 = ax1.get_legend_handles_labels(); h2, l2 = ax2.get_legend_handles_labels()
ax1.legend(h1 + h2, l1 + l2, loc="upper center", bbox_to_anchor=(0.5, -0.14), ncol=3, fontsize=8, frameon=False)
plt.title("Bengaluru road crashes 2007–2025: totals fall, but fatality share rises")
plt.xticks(city["Year"], rotation=45)
savefig("03_city_trend")
KEY["city_fr_2007"] = float(city.loc[city.Year == 2007, "Fatality_Rate_pct"].iloc[0])
KEY["city_fr_2025"] = float(city.loc[city.Year == 2025, "Fatality_Rate_pct"].iloc[0])

# %% [markdown]
# ### 3.3 Distributions

# %%
fig, axes = plt.subplots(1, 3, figsize=(12, 3.8))
sns.histplot(st["Total"].astype(float), bins=20, kde=True, ax=axes[0], color=INK)
axes[0].set_title(f"Total crashes / station-year\nskew = {st['Total'].astype(float).skew():.2f}")
sns.histplot(st["Fatal"].astype(float), bins=20, kde=True, ax=axes[1], color=MID)
axes[1].set_title(f"Fatal crashes / station-year\nskew = {st['Fatal'].astype(float).skew():.2f}")
sns.histplot(st["Fatality_Rate_pct"].astype(float), bins=20, kde=True, ax=axes[2], color=ACCENT)
axes[2].set_title(f"Fatality rate % / station-year\nskew = {st['Fatality_Rate_pct'].astype(float).skew():.2f}")
savefig("04_distributions")

# %% [markdown]
# ### 3.4 Zone comparison

# %%
plt.figure(figsize=(9, 4))
sns.lineplot(data=by_zone, x="Year", y="Total", hue="Zone", palette=PALETTE, marker="o", lw=2.4, markeredgecolor=INK)
plt.title("Total crashes by zone (zones mapped to 2025 boundaries)")
plt.legend(title="Zone", bbox_to_anchor=(1.01, 1), loc="upper left")
plt.ylabel("Total crashes")
savefig("05_zone_trend")

# %% [markdown]
# ### 3.5 Preliminary hotspots – top stations

# %%
recent = st[st["Year"] >= 2023].groupby(["Station", "Zone"]).agg(
    Total_3yr=("Total", "sum"), Fatal_3yr=("Fatal", "sum")).reset_index()
recent["Fatality_Rate_pct"] = (recent["Fatal_3yr"] / recent["Total_3yr"] * 100).round(1)
recent["Rank_Total"] = recent["Total_3yr"].rank(ascending=False, method="min").astype(int)
recent["Rank_Fatal"] = recent["Fatal_3yr"].rank(ascending=False, method="min").astype(int)
top = recent.sort_values("Total_3yr", ascending=False).head(12)
print("Top 12 stations 2023–2025:\n", top.to_string(index=False))
KEY["top_stations"] = top.to_dict("records")
recent.sort_values("Total_3yr", ascending=False).to_csv(PROC / "station_ranking_2023_2025.csv", index=False)

fig, ax = plt.subplots(figsize=(9, 5))
t = top.sort_values("Total_3yr")
ax.barh(t["Station"], t["Total_3yr"] - t["Fatal_3yr"], color=LIGHT, label="Non-fatal")
ax.barh(t["Station"], t["Fatal_3yr"], left=t["Total_3yr"] - t["Fatal_3yr"], color=INK, label="Fatal")
for i, (v, f) in enumerate(zip(t["Total_3yr"], t["Fatal_3yr"])):
    ax.text(v + 5, i, f"{v}  ({f} fatal)", va="center", fontsize=8)
ax.set_xlabel("Crashes 2023–2025 (3 years combined)")
ax.set_title("Top-12 crash stations, 2023–2025")
ax.legend(loc="lower right")
savefig("06_top_stations")

# Heatmap: stations present in all 8 years
pivot = st.pivot_table(index="Station", columns="Year", values="Total").astype(float)
full = pivot.dropna()
full = full.loc[full.sum(axis=1).sort_values(ascending=False).index].head(20)
plt.figure(figsize=(9, 7))
sns.heatmap(full, annot=True, fmt=".0f", cmap=MONO, linewidths=0.4, linecolor="white", cbar_kws={"label": "Crashes"}, annot_kws={"size": 7})
plt.title("Top-20 stations (reported every year) – crashes by year")
savefig("07_station_heatmap")
KEY["stations_all_years"] = int(len(pivot.dropna()))

# Rank stability – are hotspots persistent?
rank = pivot.dropna().rank(ascending=False)
rho = rank.corr(method="spearman")
print("Spearman rank correlation between years (stations present all years):\n", rho.round(2))
KEY["rank_rho_2018_2025"] = round(float(rho.loc[2018, 2025]), 2)
KEY["rank_rho_mean_adjacent"] = round(float(np.mean([rho.loc[y, y + 1] for y in range(2018, 2025)])), 2)

# %% [markdown]
# ### 3.6 Correlation analysis

# %%
corr_df = st[st["Year"] <= 2023][["Fatal", "Killed", "Non_Fatal", "Injured", "Total", "Fatality_Rate_pct"]].astype(float)
corr = corr_df.corr().round(2)
print("Pearson correlation (2018–2023, all variables available):\n", corr)
KEY["corr_fatal_total"] = float(corr.loc["Fatal", "Total"])
KEY["corr_fr_total"] = float(corr.loc["Fatality_Rate_pct", "Total"])
plt.figure(figsize=(6.4, 5))
sns.heatmap(corr, annot=True, cmap=DIVERGE, vmin=-1, vmax=1, square=True, linewidths=0.6, linecolor="white")
plt.title("Correlation matrix (2018–2023)")
savefig("08_correlation")

# Fatal vs total scatter – which stations are disproportionately deadly?
plt.figure(figsize=(8, 5))
r = recent
sns.scatterplot(data=r, x="Total_3yr", y="Fatal_3yr", hue="Zone", palette=PALETTE, s=60, edgecolor=INK, linewidth=0.5)
m, b = np.polyfit(r["Total_3yr"], r["Fatal_3yr"], 1)
xs = np.linspace(r["Total_3yr"].min(), r["Total_3yr"].max(), 50)
plt.plot(xs, m * xs + b, "--", color=MID, lw=1)
resid = r["Fatal_3yr"] - (m * r["Total_3yr"] + b)
lab_idx = set(resid.abs().sort_values(ascending=False).head(6).index) | set(r["Total_3yr"].nlargest(6).index)
for _, rr in r.loc[sorted(lab_idx)].iterrows():
    plt.annotate(rr["Station"], (rr["Total_3yr"], rr["Fatal_3yr"]), fontsize=7, xytext=(4, 3), textcoords="offset points")
plt.xlabel("Total crashes 2023–2025")
plt.ylabel("Fatal crashes 2023–2025")
plt.title("Fatal vs total crashes per station, 2023–2025 (dashed = linear fit)")
savefig("09_fatal_vs_total")
KEY["deadly_above_trend"] = r.loc[resid.sort_values(ascending=False).head(5).index, "Station"].tolist()

# %% [markdown]
# ### 3.7 Context – Karnataka and India

# %%
ka23 = ka_clean[ka_clean["Year"] == 2023].sort_values("Crashes", ascending=False)
KEY["ka_blr_share_2023"] = round(float(ka23.loc[ka23.District == "Bengaluru City", "Crashes"].iloc[0] / ka23["Crashes"].sum() * 100), 1)
KEY["ka_top"] = ka23.head(8)[["District", "Crashes", "Deaths", "Deaths_per_100_crashes"]].to_dict("records")
plt.figure(figsize=(9, 4.5))
k = ka23.head(12).sort_values("Crashes")
plt.barh(k["District"], k["Crashes"], color=[ACCENT if d == "Bengaluru City" else LIGHT for d in k["District"]])
plt.title("Karnataka – top-12 police districts by road crashes, 2023")
plt.xlabel("Crashes")
savefig("10_karnataka")

top_cities = ind.sort_values("2024 Accidents", ascending=False).head(10)
KEY["india_top"] = top_cities[["City", "2024 Accidents", "2024 Killed", "2024 Ranking Accidents"]].to_dict("records")
plt.figure(figsize=(9, 4.5))
tc = top_cities.sort_values("2024 Accidents")
plt.barh(tc["City"], tc["2024 Accidents"], color=[ACCENT if c == "Bengaluru" else LIGHT for c in tc["City"]])
plt.title("India – top-10 large cities by road accidents, 2024 (MoRTH)")
plt.xlabel("Accidents")
savefig("11_india_cities")

# %% [markdown]
# ### 3.8 Save key numbers for the report

# %%
def _conv(o):
    if isinstance(o, (np.integer,)): return int(o)
    if isinstance(o, (np.floating,)): return float(o)
    if isinstance(o, (pd.Timestamp,)): return str(o)
    return str(o)

(BASE / "outputs").mkdir(exist_ok=True)
with open(BASE / "outputs" / "key_numbers.json", "w") as f:
    json.dump(json.loads(json.dumps(KEY, default=_conv).replace("NaN", "null")), f, indent=2)
data_dictionary.to_csv(PROC / "data_dictionary.csv", index=False)
print("Saved cleaned data, figures and key numbers.")
