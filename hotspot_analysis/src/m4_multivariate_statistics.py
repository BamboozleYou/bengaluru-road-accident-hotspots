"""MODULE 4 - Multivariate analysis, statistical summary and context.   Author: Member 4

Objectives answered here: O7 (persistence of hotspots), O8 (relationships among variables),
O10 (Bengaluru vs Karnataka and India), plus the composite Hotspot Priority Index.
"""
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from scipy import stats

from common import (BLUE, DIV, GREY, INK, INK2, MUTED, ORANGE, SEQ, TABLES, ZONE_COL, ZONE_MARK, ZONE_ORDER,
                    load, record, savefig, step, zone_legend)

st, city, ka, ind = load("st"), load("city"), load("ka"), load("ind")
recent = st[st["Year"] >= 2023]

# =========================================================== STATISTICAL SUMMARY
with step("m4_describe"):
    cols = ["Fatal", "Killed", "Non_Fatal", "Injured", "Total", "Fatality_Rate_pct", "Killed_per_100", "Injured_per_crash"]
    d = st[cols].astype(float)
    desc = d.describe().T
    desc["median"] = d.median()
    desc["IQR"] = desc["75%"] - desc["25%"]
    desc["skew"] = d.skew()
    desc["kurtosis"] = d.kurt()
    desc["CV %"] = desc["std"] / desc["mean"] * 100
    desc = desc.round(2)
    print(desc[["count", "mean", "median", "std", "min", "25%", "75%", "max", "skew", "kurtosis", "CV %"]].to_string())
desc.to_csv(TABLES / "descriptive_statistics.csv")

with step("m4_period_stats"):
    per = st.groupby("Period", observed=True).agg(Station_years=("Total", "size"), Mean_total=("Total", "mean"),
                                                  Median_total=("Total", "median"), Mean_fatality_rate=("Fatality_Rate_pct", "mean"))
    per = per.astype(float).round(2)
    print(per.to_string())
    pre = st.loc[st["Period"] == "Pre-COVID", "Fatality_Rate_pct"]
    post = st.loc[st["Period"] == "Post-COVID", "Fatality_Rate_pct"]
    mw = stats.mannwhitneyu(post, pre, alternative="greater")
    print(f"\nMann-Whitney U (post-COVID fatality rate > pre-COVID): U = {mw.statistic:.0f}, p = {mw.pvalue:.4f}")
    sw = stats.shapiro(st["Total"].astype(float))
    print(f"Shapiro-Wilk normality test on Total: W = {sw.statistic:.3f}, p = {sw.pvalue:.2e}  -> not normal")
per.to_csv(TABLES / "period_stats.csv")

# =========================================================== MULTIVARIATE
# Fig 14 - O8: correlation heatmap (2018-2023, all variables published)
with step("m4_correlation"):
    cdf = st[st["Year"] <= 2023][["Fatal", "Killed", "Non_Fatal", "Injured", "Total", "Fatality_Rate_pct", "Injured_per_crash"]].astype(float)
    pear = cdf.corr().round(2)
    spear = cdf.corr(method="spearman").round(2)
    print("Pearson correlation (2018-2023):\n", pear.to_string())
    print("\nSpearman: Fatality_Rate_pct vs Total =", spear.loc["Fatality_Rate_pct", "Total"])
fig, ax = plt.subplots(figsize=(7.4, 6))
labels = ["Fatal", "Killed", "Non-fatal", "Injured", "Total", "Fatality\nrate %", "Injured\nper crash"]
mask = np.triu(np.ones_like(pear, dtype=bool), k=1)
sns.heatmap(pear, mask=mask, annot=True, fmt=".2f", cmap=DIV, vmin=-1, vmax=1, square=True, linewidths=2,
            linecolor="white", cbar_kws={"label": "Pearson r", "shrink": .75}, xticklabels=labels, yticklabels=labels,
            annot_kws={"size": 9.5}, ax=ax)
ax.set_title("Correlation matrix of crash variables, 2018-2023")
ax.tick_params(axis="x", rotation=0)
savefig("fig14_correlation_heatmap")

# Fig 15 - O8: pair plot coloured by zone
pp = recent[["Total", "Fatal", "Fatality_Rate_pct", "Zone"]].copy()
pp[["Total", "Fatal"]] = pp[["Total", "Fatal"]].astype(float)
pp["Zone"] = pp["Zone"].astype(str)
g = sns.pairplot(pp, hue="Zone", hue_order=ZONE_ORDER, palette=ZONE_COL, markers=[ZONE_MARK[z] for z in ZONE_ORDER],
                 diag_kind="kde", height=2.3, plot_kws=dict(s=28, edgecolor="white", linewidth=.6, alpha=.9),
                 diag_kws=dict(common_norm=False, fill=False, linewidth=1.8))
g.figure.suptitle("Pair plot of volume, fatal crashes and fatality rate by zone, 2023-2025", y=1.03, fontweight="bold")
savefig("fig15_pairplot")

# Fig 16 - O7: station x year heatmap (persistence)
pivot = st.pivot_table(index="Station", columns="Year", values="Total", aggfunc="sum").astype(float)
full = pivot.dropna()
with step("m4_persistence"):
    rho = full.corr(method="spearman")
    adj = [rho.loc[y, y + 1] for y in range(2018, 2025)]
    print(f"Stations reported in all 8 years: {len(full)}")
    print("Spearman rank correlation between consecutive years:", [round(float(a), 2) for a in adj])
    print(f"2018 vs 2025: rho = {rho.loc[2018, 2025]:.2f}")
    top10_each = {y: set(full[y].nlargest(10).index) for y in full.columns}
    always = set.intersection(*top10_each.values())
    print("Stations in the top 10 in EVERY year 2018-2025:", sorted(always))
    freq = pd.Series([s for v in top10_each.values() for s in v]).value_counts()
    print("Years in top-10 (of 8):\n", freq.head(12).to_string())
top = full.loc[full.sum(axis=1).sort_values(ascending=False).index].head(20)
fig, ax = plt.subplots(figsize=(9, 7.2))
sns.heatmap(top, annot=True, fmt=".0f", cmap=SEQ, linewidths=1.5, linecolor="white",
            cbar_kws={"label": "Crashes in year", "shrink": .7}, annot_kws={"size": 8.5}, ax=ax)
ax.set_ylabel(""); ax.set_xlabel("")
ax.set_title("Top-20 stations (reported every year): crashes by year")
savefig("fig16_station_year_heatmap")

# Fig 17 - O7: rank-correlation matrix between years
fig, ax = plt.subplots(figsize=(6.6, 5.4))
sns.heatmap(rho.round(2), annot=True, fmt=".2f", cmap=SEQ, vmin=0.5, vmax=1, square=True, linewidths=1.5,
            linecolor="white", cbar_kws={"label": "Spearman rho", "shrink": .75}, annot_kws={"size": 9}, ax=ax)
ax.set_xlabel(""); ax.set_ylabel("")
ax.set_title(f"Do the same stations stay on top? Rank correlation of\nstation crash counts between years ({len(full)} stations)")
savefig("fig17_rank_correlation")

# Fig 18 - zone x year fatality-rate heatmap (three variables)
zfr = st.groupby(["Zone", "Year"], observed=True)[["Fatal", "Total"]].sum()
zfr = (zfr["Fatal"] / zfr["Total"] * 100).unstack().reindex(ZONE_ORDER).astype(float)
with step("m4_zone_year_fr"):
    print(zfr.round(1).to_string())
fig, ax = plt.subplots(figsize=(9, 3.4))
sns.heatmap(zfr, annot=True, fmt=".1f", cmap=SEQ, linewidths=1.5, linecolor="white",
            cbar_kws={"label": "Fatality rate %"}, annot_kws={"size": 9.5}, ax=ax)
ax.set_ylabel(""); ax.set_xlabel("")
ax.set_title("Fatality rate (%) by zone and year")
savefig("fig18_zone_year_fatality")

# Fig 19 - composite Hotspot Priority Index (volume + severity + trend)
with step("m4_priority_index"):
    r = recent.groupby(["Station", "Zone"], observed=True).agg(Total=("Total", "sum"), Fatal=("Fatal", "sum")).reset_index()
    r["Fatality_Rate_pct"] = r["Fatal"] / r["Total"] * 100
    trend = (st[st["Year"] >= 2021].groupby("Station")
             .apply(lambda g: stats.linregress(g["Year"], g["Total"].astype(float)).slope if len(g) >= 3 else 0.0))
    r["Trend_per_yr"] = r["Station"].map(trend).fillna(0)

    def mm(s):
        return (s - s.min()) / (s.max() - s.min())

    # weights: fatal crashes 40% (lives), all crashes 30% (exposure), fatality rate 20%, recent trend 10%
    r["HPI"] = (0.4 * mm(r["Fatal"]) + 0.3 * mm(r["Total"]) + 0.2 * mm(r["Fatality_Rate_pct"])
                + 0.1 * mm(r["Trend_per_yr"])) * 100
    r = r.sort_values("HPI", ascending=False).reset_index(drop=True)
    r.index += 1
    r["Tier"] = pd.cut(r["HPI"], [-1, 30, 55, 101], labels=["Monitor", "High", "Critical"])
    print(r.head(12).round(1).to_string())
    print("\nTier counts:", r["Tier"].value_counts().to_dict())
    # robustness: does the top-10 change under equal weights?
    eq = (mm(r["Fatal"]) + mm(r["Total"]) + mm(r["Fatality_Rate_pct"]) + mm(r["Trend_per_yr"])) / 4
    overlap = len(set(r.head(10)["Station"]) & set(r.loc[eq.sort_values(ascending=False).index[:10], "Station"]))
    print(f"Top-10 overlap with equal weights: {overlap}/10")
r.round(2).to_csv(TABLES / "hotspot_priority_index.csv", index_label="Rank")
fig, ax = plt.subplots(figsize=(9.8, 5.6))
for z in ZONE_ORDER:
    dz = r[r["Zone"] == z]
    ax.scatter(dz["Total"], dz["Fatality_Rate_pct"], s=dz["HPI"] * 6 + 15, color=ZONE_COL[z], marker=ZONE_MARK[z],
               alpha=.75, edgecolor="white", linewidth=1)
ax.axhline(r["Fatality_Rate_pct"].median(), color=MUTED, ls=":", lw=1)
ax.axvline(r["Total"].median(), color=MUTED, ls=":", lw=1)
ax.text(r["Total"].max(), r["Fatality_Rate_pct"].median() + .4, "median", fontsize=8, color=MUTED, ha="right")
for i, rr in r.head(8).iterrows():
    ax.annotate(f"{i}. {rr['Station']}", (rr["Total"], rr["Fatality_Rate_pct"]), xytext=(7, 4), textcoords="offset points", fontsize=8.5)
ax.set_xlabel("All crashes, 2023-2025")
ax.set_ylabel("Fatality rate 2023-2025 (%)")
ax.set_title("Hotspot Priority Index: crash volume vs fatality rate (bubble size = index score)")
zone_legend(ax, loc="upper left", bbox_to_anchor=(1.01, 1))
savefig("fig19_priority_bubble")

# =========================================================== CONTEXT (O10)
ka23 = ka[ka["Year"] == 2023].sort_values("Crashes", ascending=False)
with step("m4_karnataka"):
    blr = ka23[ka23["District"] == "Bengaluru City"].iloc[0]
    share = blr["Crashes"] / ka23["Crashes"].sum() * 100
    print(ka23.head(8)[["District", "Crashes", "Deaths", "Deaths_per_100"]].to_string(index=False))
    print(f"\nBengaluru City share of Karnataka crashes 2023: {share:.1f}%")
    print(f"Bengaluru deaths per 100 crashes: {blr['Deaths_per_100']} vs state median {ka23['Deaths_per_100'].median()}")
fig, ax = plt.subplots(figsize=(9.5, 4.8))
k = ka23.head(12).iloc[::-1]
ax.barh(k["District"], k["Crashes"], color=[BLUE if dname == "Bengaluru City" else GREY for dname in k["District"]])
for i, (c, dpc) in enumerate(zip(k["Crashes"], k["Deaths_per_100"])):
    ax.text(c + 60, i, f"{int(c):,}  |  {dpc:.0f} deaths per 100 crashes", va="center", fontsize=8.5)
ax.set_xlim(0, k["Crashes"].max() * 1.45)
ax.grid(axis="x"); ax.grid(axis="y", visible=False)
ax.set_xlabel("Road crashes, 2023")
ax.set_title("Karnataka: top-12 police districts by road crashes, 2023")
savefig("fig20_karnataka")

with step("m4_india"):
    i24 = ind.sort_values("2024 Accidents", ascending=False)
    print(i24.head(8)[["City", "2024 Accidents", "2024 Killed", "2024 Ranking Accidents", "2024 Ranking Killed", "Killed_per_100_2024"]].to_string(index=False))
    b = ind[ind["City"] == "Bengaluru"].iloc[0]
    print(f"\nBengaluru: rank {int(b['2024 Ranking Accidents'])} for accidents, rank {int(b['2024 Ranking Killed'])} for deaths;"
          f" {b['Killed_per_100_2024']} killed per 100 accidents (median of 50 cities: {ind['Killed_per_100_2024'].median()})")
fig, ax = plt.subplots(figsize=(9.5, 5.2))
others = ind[ind["City"] != "Bengaluru"]
ax.scatter(others["2024 Accidents"], others["2024 Killed"], s=40, color=GREY, edgecolor="white", label="Other million-plus cities")
ax.scatter(b["2024 Accidents"], b["2024 Killed"], s=110, color=BLUE, edgecolor="white", zorder=5, label="Bengaluru")
for _, rr in i24.head(6).iterrows():
    off = {"Chennai": (-6, -12), "Indore": (-6, 4), "Hyderabad": (6, -10)}.get(rr["City"], (6, 3))
    ax.annotate(rr["City"], (rr["2024 Accidents"], rr["2024 Killed"]), xytext=off, textcoords="offset points",
                fontsize=8.5, ha="right" if off[0] < 0 else "left")
xx = np.linspace(0, ind["2024 Accidents"].max(), 10)
for k_, lab in [(10, "10 killed / 100"), (30, "30 killed / 100")]:
    ax.plot(xx, xx * k_ / 100, color=MUTED, ls=":", lw=1)
    ax.text(xx[-1], xx[-1] * k_ / 100, lab, fontsize=8, color=MUTED, ha="right", va="bottom")
ax.set_xlabel("Road accidents, 2024")
ax.set_ylabel("Persons killed, 2024")
ax.set_title("Bengaluru among India's 50 million-plus cities, 2024 (MoRTH)")
ax.legend(loc="upper left")
savefig("fig21_india_cities")

record(desc=desc.reset_index().rename(columns={"index": "var"}).to_dict("records"), period=per.reset_index().to_dict("records"),
       mw_U=float(mw.statistic), mw_p=float(mw.pvalue), shapiro_W=round(float(sw.statistic), 3), shapiro_p=float(sw.pvalue),
       corr=pear.to_dict(), spear_fr_total=float(spear.loc["Fatality_Rate_pct", "Total"]),
       n_full=len(full), rho_adj=[round(float(a), 2) for a in adj], rho_18_25=round(float(rho.loc[2018, 2025]), 2),
       always_top10=sorted(always), top10_freq=freq.head(12).to_dict(), zone_year_fr=zfr.round(1).to_dict(),
       hpi=r.head(15).round(2).to_dict("records"), hpi_tiers=r["Tier"].value_counts().to_dict(), hpi_overlap=overlap,
       ka_top=ka23.head(8)[["District", "Crashes", "Deaths", "Deaths_per_100"]].to_dict("records"),
       ka_share=round(share, 1), ka_blr_dp100=float(blr["Deaths_per_100"]), ka_median_dp100=float(ka23["Deaths_per_100"].median()),
       n_ka=len(ka23),
       india_top=i24.head(8)[["City", "2024 Accidents", "2024 Killed", "2024 Ranking Accidents", "2024 Ranking Killed", "Killed_per_100_2024"]].to_dict("records"),
       blr_rank_acc=int(b["2024 Ranking Accidents"]), blr_rank_killed=int(b["2024 Ranking Killed"]),
       blr_kp100=float(b["Killed_per_100_2024"]), india_median_kp100=float(ind["Killed_per_100_2024"].median()))
