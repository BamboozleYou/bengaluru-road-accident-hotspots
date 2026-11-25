"""MODULE 2 - Data preprocessing and preparation.                  Author: Member 2

Missing values, duplicates, inconsistent entries, data types, invalid values and
outliers, with a before/after snapshot of every step for the report.
"""
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from scipy import stats

from common import (BLUE, GREY, INK, ORANGE, TABLES, ZONE_COL, ZONE_MARK, ZONE_ORDER, load, record,
                    save, savefig, step, zone_legend)

raw = load("raw")
st = load("stations_raw").copy()
NUM = ["Fatal", "Killed", "Non_Fatal", "Injured", "Total"]
before_shape = st.shape
before_sample = st.head(8).copy()

# ------------------------------------------------------------------ 1. invalid (aggregate) rows
with step("m2_aggregates"):
    is_agg = (st["Station_raw"].fillna("").str.contains("Total", case=False)
              | st["Zone_reported"].isna()
              | st["Zone_reported"].str.strip().eq("Total"))
    agg_rows = st[is_agg]
    print(f"Sub-total / zone-total / grand-total rows found: {len(agg_rows)}")
    print(agg_rows[["Year", "Zone_reported", "Sub_division", "Station_raw", "Total"]].head(10).to_string(index=False))
    grand_totals = agg_rows[agg_rows["Station_raw"].str.contains("Grand", na=False)].copy()
    st = st[~is_agg].copy()
    print("Shape after removing them:", st.shape)

# ------------------------------------------------------------------ 2. missing values (before)
missing_before = pd.DataFrame({"Missing (before)": load("stations_raw")[NUM + ["Sub_division"]].isna().sum()})

# ------------------------------------------------------------------ 3. data types
with step("m2_dtypes"):
    dtypes_before = st.dtypes.astype(str)
    for c in ["Zone_reported", "Sub_division", "Station_raw"]:
        st[c] = st[c].str.strip()
    for c in NUM:   # '7,469' -> 7469 ; ' 45 ' -> 45 ; text -> nullable integer
        st[c] = pd.to_numeric(st[c].str.replace(",", "", regex=False).str.strip(), errors="coerce").astype("Int64")
    st["Year"] = st["Year"].astype("int64")
    dtypes_after = st.dtypes.astype(str)
    dtype_tbl = pd.DataFrame({"Before": dtypes_before, "After": dtypes_after}).loc[
        ["Year", "Fatal", "Killed", "Non_Fatal", "Injured", "Total", "Station_raw"]]
    print(dtype_tbl)
    for g in ("Total", "Fatal"):
        grand_totals[g] = pd.to_numeric(grand_totals[g], errors="coerce")

# ------------------------------------------------------------------ 4. inconsistent entries
NAME_MAP = {
    "Ulsoor": "Halasooru", "K.R.Pura": "K R Puram", "White Field": "Whitefield", "HuliMavu": "Hulimavu",
    "Mico layout": "Micolayout", "K.Swamy Lyt.": "K S Layout", "RT Nagar": "R T Nagar",
    "Yelahanka": "Yalahanka", "Chikjala": "Chikkajala", "Malleswaram": "Malleshwaram",
    "Y.Pura": "Yashawanthapura", "B.Pura": "Bytarayanapura", "Chamarajapet": "Chamarajpet",
    "Int. Aiport": "Int. Airport", "F.Town": "Pulikeshinagar", "Chickpet": "Sheshadripuram/Chickpet",
}
with step("m2_names"):
    st["Station"] = st["Station_raw"].replace(NAME_MAP)
    name_changes = (st.loc[st["Station"] != st["Station_raw"], ["Station_raw", "Station"]]
                    .drop_duplicates().sort_values("Station").reset_index(drop=True))
    print(f"Station spellings harmonised: {len(name_changes)}")
    print(name_changes.to_string(index=False))
    # BTP reorganised zones in 2023 -> map every year to the latest (2025) zone so zones are comparable
    latest = st.sort_values("Year").groupby("Station")[["Zone_reported", "Sub_division"]].last()
    st["Zone"] = st["Station"].map(latest["Zone_reported"])
    st["Sub_division"] = st["Sub_division"].fillna(st["Station"].map(latest["Sub_division"]))
    moved = st.loc[st["Zone"] != st["Zone_reported"], "Station"].nunique()
    print(f"\nStations re-mapped to their 2025 zone: {moved}")
    print("Unique stations before/after harmonising:", st["Station_raw"].nunique(), "->", st["Station"].nunique())

# ------------------------------------------------------------------ 5. missing values
with step("m2_missing"):
    miss = pd.DataFrame({"Missing": st[NUM + ["Sub_division"]].isna().sum(),
                         "Missing %": (st[NUM + ["Sub_division"]].isna().mean() * 100).round(2)})
    print(miss)
    print("\nMissing Killed / Injured by year:")
    print(st.groupby("Year")[["Killed", "Injured"]].apply(lambda d: d.isna().sum()).T.to_string())
    # Killed / Injured are structurally missing: BTP stopped publishing them from 2024.
    # They are NOT imputed - inventing victim counts would bias severity results.
    # Fatal, Non_Fatal and Total are complete, so the hotspot analysis uses all 8 years.

fig, ax = plt.subplots(figsize=(9, 3.2))
order = st.sort_values(["Year", "Station"]).reset_index(drop=True)
sns.heatmap(order[NUM + ["Sub_division"]].isna().T.astype(int), cbar=False, cmap=["#eef3fb", ORANGE], ax=ax)
pos = order.groupby("Year").apply(lambda d: d.index.min())
ax.set_xticks(pos.values + 2)
ax.set_xticklabels(pos.index, rotation=0)
ax.set_xlabel("Station records, ordered by year")
ax.set_title("Missing-value map (orange = missing)")
savefig("fig01_missing_map")

# ------------------------------------------------------------------ 6. duplicates
with step("m2_duplicates"):
    exact = st.duplicated(subset=["Station", "Year"] + NUM).sum()
    keyd = st.duplicated(subset=["Station", "Year"]).sum()
    print("Exact duplicate rows            :", exact)
    print("Duplicate (Station, Year) keys  :", keyd)
    print("Records per year:", st["Year"].value_counts().sort_index().to_dict())
    st = st.drop_duplicates(subset=["Station", "Year"], keep="first")

# ------------------------------------------------------------------ 7. invalid values / logic checks
with step("m2_validity"):
    checks = {
        "Negative counts": int((st[NUM] < 0).sum().sum()),
        "Fatal + Non_Fatal != Total": int(((st["Fatal"] + st["Non_Fatal"]) != st["Total"]).sum()),
        "Killed < Fatal (impossible)": int((st["Killed"] < st["Fatal"]).fillna(False).sum()),
        "Total = 0 (empty station)": int((st["Total"] == 0).sum()),
        "Fatal > Total": int((st["Fatal"] > st["Total"]).sum()),
        "Year outside 2018-2025": int((~st["Year"].between(2018, 2025)).sum()),
    }
    validity = pd.DataFrame({"Rule": list(checks), "Violations": list(checks.values())})
    print(validity.to_string(index=False))
    # Cross-check: sum of stations vs BTP Grand Total row vs the separate city-level table
    city = raw["city_annual"].copy()
    for c in city.columns:
        city[c] = pd.to_numeric(city[c].str.replace(",", ""), errors="coerce").astype(int)
    city.columns = ["Year", "Fatal", "Killed", "Non_Fatal", "Total"]
    recon = (st.groupby("Year")["Total"].sum().rename("Sum of stations").to_frame()
             .join(grand_totals.set_index(grand_totals["Year"].astype(int))["Total"].rename("Grand Total row"))
             .join(city.set_index("Year")["Total"].rename("City table")))
    recon["Difference vs city"] = recon["Sum of stations"] - recon["City table"]
    recon["Difference %"] = (recon["Difference vs city"] / recon["City table"] * 100).round(2)
    print("\n", recon.to_string())

# ------------------------------------------------------------------ 8. outliers
def iqr_bounds(s):
    q1, q3 = s.quantile([0.25, 0.75])
    return q1 - 1.5 * (q3 - q1), q3 + 1.5 * (q3 - q1)


with step("m2_outliers"):
    rows = []
    for y, g in st.groupby("Year"):
        tot = g["Total"].astype(float)
        lo, hi = iqr_bounds(tot)
        z = np.abs(stats.zscore(tot))
        for i, idx in enumerate(g.index):
            if tot[idx] > hi or tot[idx] < lo or z[i] > 2.5:
                rows.append({"Year": y, "Station": g.at[idx, "Station"], "Zone": g.at[idx, "Zone"],
                             "Total": int(tot[idx]), "IQR upper fence": round(hi, 1), "Z-score": round(float(z[i]), 2)})
    outliers = pd.DataFrame(rows)
    print(f"Station-years flagged (IQR or |z| > 2.5): {len(outliers)}")
    print(outliers.to_string(index=False))
    # Sensitivity: how much do the summary statistics move if outliers are capped at the fence?
    capped = st["Total"].astype(float).copy()
    for y, g in st.groupby("Year"):
        lo, hi = iqr_bounds(g["Total"].astype(float))
        capped[g.index] = g["Total"].astype(float).clip(lo, hi)
    sens = pd.DataFrame({"Original": st["Total"].astype(float).describe(), "IQR-capped": capped.describe()}).round(2)
    sens.loc["skew"] = [st["Total"].astype(float).skew().round(2), capped.skew().round(2)]
    print("\nSensitivity of Total to capping:\n", sens.to_string())

fig, ax = plt.subplots(figsize=(10, 4.4))
sns.boxplot(data=st, x="Year", y=st["Total"].astype(float), color="#eef3fb", linecolor=INK, fliersize=0, ax=ax, width=0.55)
key = outliers.set_index(["Year", "Station"]).index
is_out = st.set_index(["Year", "Station"]).index.isin(key)
for z in ZONE_ORDER:
    d = st[(st["Zone"] == z) & ~is_out]
    ax.scatter(d["Year"] - 2018 + np.random.default_rng(1).uniform(-.18, .18, len(d)), d["Total"].astype(float),
               s=14, color=ZONE_COL[z], marker=ZONE_MARK[z], alpha=.7, linewidths=0)
ax.scatter(outliers["Year"] - 2018, outliers["Total"], s=90, facecolors="none", edgecolors="#e34948", lw=1.8, zorder=5)
for _, r in outliers.sort_values("Total").groupby("Year").tail(1).iterrows():
    ax.annotate(r["Station"], (r["Year"] - 2018, r["Total"]), xytext=(0, 8), textcoords="offset points",
                ha="center", fontsize=8, color=INK)
ax.set_ylabel("Crashes per station")
ax.set_title("Crashes per police station by year (red rings = flagged outliers)")
zone_legend(ax, bbox_to_anchor=(1.01, 1), loc="upper left")
savefig("fig02_outlier_boxplot")
# Decision: the flagged values are real high-crash stations (they reconcile with the official
# grand totals), i.e. the very hotspots this project is looking for -> RETAINED, not removed.

# ------------------------------------------------------------------ 9. feature engineering + save
with step("m2_features"):
    st["Fatality_Rate_pct"] = (st["Fatal"] / st["Total"] * 100).astype(float).round(2)
    st["Killed_per_100"] = (st["Killed"] / st["Total"] * 100).astype(float).round(2)
    st["Injured_per_crash"] = (st["Injured"] / st["Total"]).astype(float).round(3)
    st["Period"] = pd.cut(st["Year"], [2017, 2019, 2021, 2025], labels=["Pre-COVID", "COVID", "Post-COVID"])
    st = st[["Year", "Period", "Zone", "Sub_division", "Station", "Station_raw", "Fatal", "Killed", "Non_Fatal",
             "Injured", "Total", "Fatality_Rate_pct", "Killed_per_100", "Injured_per_crash", "Source_file"]] \
        .sort_values(["Year", "Zone", "Station"]).reset_index(drop=True)
    st["Zone"] = pd.Categorical(st["Zone"], ZONE_ORDER)
    print("Clean station table:", st.shape)
    print(st.drop(columns=["Station_raw", "Source_file"]).head(6).to_string(index=False))

with step("m2_supporting"):
    city["Fatality_Rate_pct"] = (city["Fatal"] / city["Total"] * 100).round(2)
    city["Killed_per_100"] = (city["Killed"] / city["Total"] * 100).round(2)
    city["YoY_change_pct"] = (city["Total"].pct_change() * 100).round(1)
    city["Total_z"] = stats.zscore(city["Total"]).round(2)

    ka = raw["ka_districts"].copy()
    ka = ka[ka["District"].notna() & ka["Sl No"].notna()].drop(columns="Sl No")
    ka_long = ka.melt(id_vars="District", var_name="metric", value_name="value")
    ka_long["Year"] = ka_long["metric"].str.extract(r"(\d{4})").astype(int)
    ka_long["metric"] = ka_long["metric"].str.replace(r"\s*\d{4}", "", regex=True)
    ka_long["value"] = pd.to_numeric(ka_long["value"].str.replace(",", ""), errors="coerce")
    ka_clean = ka_long.pivot_table(index=["District", "Year"], columns="metric", values="value").reset_index()
    ka_clean.columns.name = None
    ka_clean = ka_clean.rename(columns={"Road Crashes": "Crashes"})
    print("Karnataka rows with missing values (district created in 2021):")
    print(ka_long[ka_long["value"].isna()][["District", "Year", "metric"]].drop_duplicates().to_string(index=False))
    ka_clean = ka_clean.dropna(subset=["Crashes"])
    ka_clean["Deaths_per_100"] = (ka_clean["Deaths"] / ka_clean["Crashes"] * 100).round(1)

    ind = raw["india_cities"].copy()
    ind = ind[ind["City"].notna() & ~ind["City"].str.contains("Total", case=False, na=False)]
    for c in ind.columns.drop("City"):
        ind[c] = pd.to_numeric(ind[c].str.replace(",", ""), errors="coerce")
    ind = ind.drop(columns="Sl No")
    ind["Killed_per_100_2024"] = (ind["2024 Killed"] / ind["2024 Accidents"] * 100).round(1)
    print("\nCity annual:", city.shape, "| Karnataka districts:", ka_clean.shape, "| India cities:", ind.shape)
    print("Missing after cleaning ->", "city:", int(city.isna().sum().sum() - 1), "| KA:",
          int(ka_clean.isna().sum().sum()), "| India:", int(ind.isna().sum().sum()))

# ------------------------------------------------------------------ before/after tables for the report
missing_after = st[NUM + ["Sub_division"]].isna().sum().rename("Missing (after)")
pd.concat([missing_before, missing_after], axis=1).to_csv(TABLES / "missing_before_after.csv")
summary_ba = pd.DataFrame({
    "Metric": ["Rows", "Columns", "Aggregate (total) rows", "Numeric columns stored as text",
               "Distinct station names (data rows)", "Missing Sub_division", "Missing Killed/Injured",
               "Rows failing logic checks", "Derived features"],
    "Before cleaning": [before_shape[0], before_shape[1], len(agg_rows), len(NUM),
                        int(st["Station_raw"].nunique()),
                        int(missing_before.loc["Sub_division"].iloc[0]),
                        int(missing_before.loc["Killed"].iloc[0]), "not checked", 0],
    "After cleaning": [st.shape[0], st.shape[1], 0, 0, st["Station"].nunique(),
                       int(st["Sub_division"].isna().sum()), int(st["Killed"].isna().sum()),
                       int(validity["Violations"].sum()), 4],
})
summary_ba.to_csv(TABLES / "cleaning_summary_before_after.csv", index=False)
before_sample.drop(columns="Source_file").to_csv(TABLES / "sample_before.csv", index=False)
st[st["Station_raw"].isin(before_sample["Station_raw"]) & st["Year"].isin(before_sample["Year"])].sort_values(["Station", "Year"]).head(8)[["Year", "Zone", "Sub_division", "Station", "Fatal", "Killed", "Non_Fatal",
                                "Injured", "Total", "Fatality_Rate_pct"]].to_csv(TABLES / "sample_after.csv", index=False)
dtype_tbl.to_csv(TABLES / "dtypes_before_after.csv")
name_changes.to_csv(TABLES / "name_changes.csv", index=False)
validity.to_csv(TABLES / "validity_checks.csv", index=False)
recon.to_csv(TABLES / "reconciliation.csv")
outliers.to_csv(TABLES / "outliers.csv", index=False)
sens.to_csv(TABLES / "outlier_sensitivity.csv")
st.to_csv(TABLES / "bengaluru_station_crashes_clean.csv", index=False)

save(st, "st"); save(city, "city"); save(ka_clean, "ka"); save(ind, "ind")
record(agg_rows=len(agg_rows), names_harmonised=len(name_changes), zone_moved=int(moved),
       clean_shape=list(st.shape), n_stations=st["Station"].nunique(), n_outliers=len(outliers),
       outlier_counts=outliers["Station"].value_counts().to_dict(),
       missing_killed=int(st["Killed"].isna().sum()), missing_killed_pct=round(st["Killed"].isna().mean() * 100, 2),
       max_recon_diff_pct=float(recon["Difference %"].abs().max()), exact_dups=int(exact), key_dups=int(keyd),
       total_crashes_stations=int(st["Total"].sum()), total_fatal_stations=int(st["Fatal"].sum()))
