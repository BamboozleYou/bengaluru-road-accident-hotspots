"""MODULE 3 - Univariate and bivariate analysis.                   Author: Member 3

Objectives answered here: O1 (long-term trend), O2 (severity trend), O3 (concentration),
O4 (zones), O5 (volume hotspots), O6 (severity hotspots), O9 (improving / worsening stations).
"""
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from scipy import stats

from common import (BLUE, GREY, INK, INK2, MUTED, ORANGE, TABLES, ZONE_COL, ZONE_MARK, ZONE_ORDER, load,
                    record, savefig, step, zone_legend)

st, city = load("st"), load("city")
tot = st["Total"].astype(float)

# =========================================================== UNIVARIATE
with step("m3_central_tendency"):
    cols = ["Total", "Fatal", "Non_Fatal", "Fatality_Rate_pct"]
    uni = pd.DataFrame({
        "Mean": st[cols].astype(float).mean(),
        "Median": st[cols].astype(float).median(),
        "Mode": st[cols].astype(float).mode().iloc[0],
        "Std": st[cols].astype(float).std(),
        "Min": st[cols].astype(float).min(),
        "Max": st[cols].astype(float).max(),
        "Skew": st[cols].astype(float).skew(),
    }).round(2)
    print(uni)
    print("\nStation-years per zone:\n", st["Zone"].value_counts().reindex(ZONE_ORDER).to_string())
uni.to_csv(TABLES / "univariate_summary.csv")

# Fig 3 - distribution of crashes per station-year (histogram + box)
fig, (a1, a2) = plt.subplots(2, 1, figsize=(8.5, 4.6), sharex=True, gridspec_kw={"height_ratios": [4, 1]})
a1.hist(tot, bins=24, color=BLUE, edgecolor="white", linewidth=1)
for v, lab, ls, ha, dx in [(tot.mean(), f"Mean {tot.mean():.1f}", "-", "left", 3),
                          (tot.median(), f"Median {tot.median():.0f}", "--", "right", -3)]:
    a1.axvline(v, color=INK, ls=ls, lw=1.2)
    a1.text(v + dx, a1.get_ylim()[1] * 0.92, lab, fontsize=9, color=INK, ha=ha)
a1.set_ylabel("Station-years")
a1.set_title(f"Distribution of crashes per station-year, 2018-2025 (n = {len(tot)}, skew = {tot.skew():.2f})")
a2.boxplot(tot, vert=False, widths=0.6, patch_artist=True, boxprops=dict(facecolor="#cde2fb", color=INK),
           medianprops=dict(color=INK), flierprops=dict(marker="o", markerfacecolor=ORANGE, markeredgecolor="white"))
a2.set_yticks([])
a2.set_xlabel("Total crashes in a police-station area in one year")
a2.grid(False)
savefig("fig03_hist_total")

# Fig 4 - distribution of fatality rate
fr = st["Fatality_Rate_pct"]
fig, ax = plt.subplots(figsize=(8.5, 3.8))
ax.hist(fr, bins=24, color=ORANGE, edgecolor="white", linewidth=1)
ax.axvline(fr.mean(), color=INK, lw=1.2)
ax.text(fr.mean() + .6, ax.get_ylim()[1] * .9, f"Mean {fr.mean():.1f}%", fontsize=9)
ax.axvline(25, color=MUTED, lw=1, ls=":")
ax.text(25.6, ax.get_ylim()[1] * .7, f"> 25%: {(fr > 25).sum()} station-years", fontsize=9, color=INK2)
ax.set_xlabel("Fatality rate = fatal crashes / all crashes (%)")
ax.set_ylabel("Station-years")
ax.set_title(f"Distribution of fatality rate per station-year (skew = {fr.skew():.2f})")
savefig("fig04_hist_fatality_rate")

# Fig 5 - zone frequency (share of crashes and fatal crashes, 2023-2025)
recent = st[st["Year"] >= 2023]
zshare = recent.groupby("Zone", observed=True)[["Total", "Fatal"]].sum().reindex(ZONE_ORDER)
zshare_pct = (zshare / zshare.sum() * 100).round(1)
fig, ax = plt.subplots(figsize=(8.5, 3.8))
y = np.arange(len(ZONE_ORDER))
ax.barh(y + .2, zshare_pct["Total"], height=.38, color=BLUE, label="Share of all crashes")
ax.barh(y - .2, zshare_pct["Fatal"], height=.38, color=ORANGE, label="Share of fatal crashes")
for i, z in enumerate(ZONE_ORDER):
    ax.text(zshare_pct.loc[z, "Total"] + .4, i + .2, f"{zshare_pct.loc[z, 'Total']}%  ({int(zshare.loc[z, 'Total']):,})", va="center", fontsize=9)
    ax.text(zshare_pct.loc[z, "Fatal"] + .4, i - .2, f"{zshare_pct.loc[z, 'Fatal']}%  ({int(zshare.loc[z, 'Fatal']):,})", va="center", fontsize=9)
ax.set_yticks(y, ZONE_ORDER)
ax.invert_yaxis()
ax.set_xlim(0, 42)
ax.grid(axis="x"); ax.grid(axis="y", visible=False)
ax.set_xlabel("% of Bengaluru total, 2023-2025")
ax.set_title("Zone share of crashes and fatal crashes, 2023-2025")
ax.legend(loc="lower right")
savefig("fig05_zone_share")

# Fig 6 - concentration (Lorenz / Pareto) of crashes across stations, 2023-2025
with step("m3_concentration"):
    s = recent.groupby("Station")["Total"].sum().sort_values(ascending=False).astype(float)
    cum = s.cumsum() / s.sum() * 100
    n = len(s)
    top10_share = cum.iloc[9]
    top20pct_n = int(np.ceil(n * 0.2))
    top20pct_share = cum.iloc[top20pct_n - 1]
    srt = np.sort(s.values)
    gini = (2 * np.sum(np.arange(1, n + 1) * srt) / (n * srt.sum())) - (n + 1) / n
    print(f"Stations active 2023-25: {n}")
    print(f"Top 10 stations' share of crashes: {top10_share:.1f}%")
    print(f"Top 20% ({top20pct_n} stations) share: {top20pct_share:.1f}%")
    print(f"Gini coefficient of crashes across stations: {gini:.3f}")
fig, ax = plt.subplots(figsize=(8.5, 4))
x = np.arange(1, n + 1) / n * 100
ax.plot(np.r_[0, x], np.r_[0, cum.values], color=BLUE, marker="o", markersize=3.5)
ax.plot([0, 100], [0, 100], color=GREY, ls="--", lw=1)
ax.scatter([top20pct_n / n * 100], [top20pct_share], s=70, color=ORANGE, zorder=5)
ax.annotate(f"Top 20% of stations ({top20pct_n}) =\n{top20pct_share:.0f}% of all crashes",
            (top20pct_n / n * 100, top20pct_share), xytext=(30, 40), textcoords="offset points", fontsize=9,
            arrowprops=dict(arrowstyle="-", color=INK2))
ax.text(62, 52, "line of perfect equality", fontsize=8.5, color=MUTED, rotation=25)
ax.set_xlabel("% of police stations (ranked from most to fewest crashes)")
ax.set_ylabel("Cumulative % of crashes")
ax.set_title(f"Concentration of crashes across stations, 2023-2025 (Gini = {gini:.2f})")
ax.set_xlim(0, 100); ax.set_ylim(0, 102)
savefig("fig06_concentration_curve")

# =========================================================== BIVARIATE
# Fig 7 - O1: long-term trend of crashes (Year vs crashes), stacked fatal / non-fatal
with step("m3_city_trend"):
    lr = stats.linregress(city["Year"], city["Total"])
    tau = stats.kendalltau(city["Year"], city["Total"])
    print(f"Linear trend 2007-2025: {lr.slope:.1f} crashes/year, R^2 = {lr.rvalue**2:.2f}, p = {lr.pvalue:.4f}")
    print(f"Kendall tau = {tau.statistic:.2f}, p = {tau.pvalue:.4f}")
    print(city[["Year", "Fatal", "Non_Fatal", "Total", "YoY_change_pct", "Fatality_Rate_pct"]].to_string(index=False))
fig, ax = plt.subplots(figsize=(10, 4.2))
ax.bar(city["Year"], city["Non_Fatal"], color="#86b6ef", label="Non-fatal crashes", width=.75, edgecolor="white", linewidth=1)
ax.bar(city["Year"], city["Fatal"], bottom=city["Non_Fatal"], color="#184f95", label="Fatal crashes", width=.75, edgecolor="white", linewidth=1)
ax.plot(city["Year"], lr.intercept + lr.slope * city["Year"], color=ORANGE, ls="--", lw=1.6, label=f"Linear trend ({lr.slope:.0f}/yr)")
ax.axvspan(2019.5, 2021.5, color="#f0efec", zorder=0)
ax.text(2020.5, 3500, "COVID-19\nyears", ha="center", fontsize=8.5, color=INK2)
for yv in (2007, 2016, 2025):
    v = int(city.loc[city.Year == yv, "Total"].iloc[0])
    ax.text(yv, v + 120, f"{v:,}", ha="center", fontsize=8.5)
ax.set_xticks(city["Year"]); ax.tick_params(axis="x", rotation=45)
ax.set_ylabel("Road crashes")
ax.set_ylim(0, 9200)
ax.set_title("Bengaluru road crashes per year, 2007-2025")
ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.16), ncol=3)
savefig("fig07_city_trend")

# Fig 8 - O2: severity trend - fatality rate and killed per 100 crashes
with step("m3_severity_trend"):
    lr2 = stats.linregress(city["Year"], city["Fatality_Rate_pct"])
    print(f"Fatality-rate trend: {lr2.slope:+.2f} percentage points/year, R^2 = {lr2.rvalue**2:.2f}, p = {lr2.pvalue:.5f}")
    print("2007 fatality rate:", city.loc[0, "Fatality_Rate_pct"], "% | 2025:", city.iloc[-1]["Fatality_Rate_pct"], "%")
fig, ax = plt.subplots(figsize=(10, 3.9))
ax.plot(city["Year"], city["Killed_per_100"], color=BLUE, marker="o", markersize=5, label="Persons killed per 100 crashes")
ax.plot(city["Year"], city["Fatality_Rate_pct"], color=ORANGE, marker="s", markersize=5, label="Fatal crashes per 100 crashes")
ax.plot(city["Year"], lr2.intercept + lr2.slope * city["Year"], color=MUTED, ls="--", lw=1.2, label="Linear trend (fatality rate)")
for yv in (2007, 2016, 2025):
    v = city.loc[city.Year == yv, "Fatality_Rate_pct"].iloc[0]
    ax.annotate(f"{v:.1f}%", (yv, v), xytext=(0, -15), textcoords="offset points", ha="center", fontsize=8.5)
ax.set_xticks(city["Year"]); ax.tick_params(axis="x", rotation=45)
ax.set_ylabel("Per 100 crashes")
ax.set_ylim(0, 22)
ax.set_title("Crash severity in Bengaluru, 2007-2025: share of fatal crashes rose from 11.4% to 17.2%")
ax.legend(loc="lower right")
savefig("fig08_severity_trend")

# Fig 9 - O4: zone totals by year (line)
zy = st.groupby(["Year", "Zone"], observed=True)["Total"].sum().unstack()[ZONE_ORDER]
with step("m3_zone_year"):
    print(zy.to_string())
    print("\nChange 2018 -> 2025 (%):", ((zy.loc[2025] / zy.loc[2018] - 1) * 100).round(1).to_dict())
fig, ax = plt.subplots(figsize=(9.5, 4))
for z in ZONE_ORDER:
    ax.plot(zy.index, zy[z], color=ZONE_COL[z], marker=ZONE_MARK[z], markersize=6, label=z)
    ax.text(2025.12, zy.loc[2025, z], z, va="center", fontsize=9, color=INK)
ax.axvspan(2019.5, 2021.5, color="#f0efec", zorder=0)
ax.set_xlim(2017.7, 2025.8)
ax.set_ylabel("Road crashes")
ax.set_title("Crashes by traffic zone, 2018-2025 (stations mapped to 2025 zones)")
ax.legend(ncol=4, loc="upper left")
savefig("fig09_zone_trend")

# Fig 10 - zone vs fatality rate (boxplot comparing categories) + Kruskal-Wallis
with step("m3_zone_kruskal"):
    groups = [st.loc[st["Zone"] == z, "Fatality_Rate_pct"] for z in ZONE_ORDER]
    kw = stats.kruskal(*groups)
    ct = recent.groupby("Zone", observed=True)[["Fatal", "Non_Fatal"]].sum().reindex(ZONE_ORDER).astype(int)
    chi = stats.chi2_contingency(ct)
    print(st.groupby("Zone", observed=True)["Fatality_Rate_pct"].describe()[["mean", "50%", "std"]].round(2))
    print(f"\nKruskal-Wallis H = {kw.statistic:.2f}, p = {kw.pvalue:.4f}")
    print("Contingency table 2023-25 (fatal vs non-fatal crashes by zone):\n", ct)
    print(f"Chi-square = {chi.statistic:.2f}, dof = {chi.dof}, p = {chi.pvalue:.2e}")
    print("Fatal share by zone 2023-25 (%):", (ct["Fatal"] / ct.sum(axis=1) * 100).round(1).to_dict())
fig, ax = plt.subplots(figsize=(8.5, 4))
sns.boxplot(data=st, x="Zone", y="Fatality_Rate_pct", order=ZONE_ORDER, palette=ZONE_COL, width=.5,
            linecolor=INK, fliersize=3, ax=ax, boxprops=dict(alpha=.85))
means = st.groupby("Zone", observed=True)["Fatality_Rate_pct"].mean().reindex(ZONE_ORDER)
ax.scatter(range(4), means, marker="D", color="white", edgecolor=INK, s=40, zorder=5, label="Mean")
for i, m in enumerate(means):
    ax.text(i + .3, m, f"{m:.1f}%", va="center", fontsize=9)
ax.set_xlabel("")
ax.set_ylabel("Fatality rate per station-year (%)")
ax.set_title(f"Fatality rate by zone, 2018-2025 (Kruskal-Wallis p < 0.001)")
ax.legend(loc="upper right")
savefig("fig10_zone_fatality_box")

# Fig 11 - O5: top-15 volume hotspots, 2023-2025
rank = recent.groupby(["Station", "Zone"], observed=True).agg(Total=("Total", "sum"), Fatal=("Fatal", "sum")).reset_index()
rank["Fatality_Rate_pct"] = (rank["Fatal"] / rank["Total"] * 100).round(1)
rank = rank.sort_values("Total", ascending=False).reset_index(drop=True)
rank.index += 1
with step("m3_top_stations"):
    print(rank.head(15).to_string())
rank.to_csv(TABLES / "station_rank_2023_2025.csv", index_label="Rank")
t = rank.head(15).iloc[::-1]
fig, ax = plt.subplots(figsize=(9.5, 5.4))
ax.barh(t["Station"], t["Total"] - t["Fatal"], color=[ZONE_COL[z] for z in t["Zone"]], alpha=.45, label="Non-fatal")
ax.barh(t["Station"], t["Fatal"], left=t["Total"] - t["Fatal"], color=[ZONE_COL[z] for z in t["Zone"]], label="Fatal")
for i, (v, f) in enumerate(zip(t["Total"], t["Fatal"])):
    ax.text(v + 6, i, f"{v}  ({f} fatal)", va="center", fontsize=8.5)
ax.set_xlim(0, t["Total"].max() * 1.2)
ax.grid(axis="x"); ax.grid(axis="y", visible=False)
ax.set_xlabel("Crashes 2023-2025 (three years combined); darker segment = fatal crashes")
ax.set_title("Top-15 crash hotspot stations by volume, 2023-2025")
zone_legend(ax, loc="lower right")
savefig("fig11_top_stations")

# Fig 12 - O6: fatal vs total scatter -> stations deadlier than their volume predicts
with step("m3_fatal_vs_total"):
    r = stats.pearsonr(rank["Total"], rank["Fatal"])
    m, b = np.polyfit(rank["Total"], rank["Fatal"], 1)
    rank["Expected_Fatal"] = m * rank["Total"] + b
    rank["Excess_Fatal"] = (rank["Fatal"] - rank["Expected_Fatal"]).round(1)
    print(f"Pearson r (total vs fatal, 2023-25 stations) = {r.statistic:.2f}, p = {r.pvalue:.2e}")
    print(f"Fit: Fatal = {m:.3f} x Total + {b:.2f}")
    print("\nDeadlier than expected:\n", rank.sort_values("Excess_Fatal", ascending=False).head(6)[["Station", "Zone", "Total", "Fatal", "Fatality_Rate_pct", "Excess_Fatal"]].to_string(index=False))
fig, ax = plt.subplots(figsize=(9.5, 5.2))
for z in ZONE_ORDER:
    d = rank[rank["Zone"] == z]
    ax.scatter(d["Total"], d["Fatal"], color=ZONE_COL[z], marker=ZONE_MARK[z], s=55, edgecolor="white", linewidth=1)
xs = np.linspace(0, rank["Total"].max() * 1.03, 50)
ax.plot(xs, m * xs + b, color=MUTED, ls="--", lw=1.2)
ax.text(xs[-1], m * xs[-1] + b - 8, "linear fit", fontsize=8.5, color=MUTED, ha="right")
lab = set(rank.sort_values("Excess_Fatal", ascending=False).head(5).index) | set(rank.head(4).index)
for i in lab:
    rr = rank.loc[i]
    off = {"Whitefield": (6, -11), "Chikkajala": (-6, 6)}.get(rr["Station"], (5, 3))
    ax.annotate(rr["Station"], (rr["Total"], rr["Fatal"]), xytext=off, textcoords="offset points", fontsize=8.5,
                ha="right" if off[0] < 0 else "left")
ax.set_xlabel("All crashes, 2023-2025")
ax.set_ylabel("Fatal crashes, 2023-2025")
ax.set_title(f"Fatal vs total crashes per station, 2023-2025 (r = {r.statistic:.2f})")
zone_legend(ax, loc="upper left")
savefig("fig12_fatal_vs_total")

# Fig 13 - O9: improving vs worsening stations (2018-19 average vs 2024-25 average)
with step("m3_change"):
    pre = st[st["Year"].isin([2018, 2019])].groupby("Station")["Total"].mean()
    post = st[st["Year"].isin([2024, 2025])].groupby("Station")["Total"].mean()
    chg = pd.concat([pre.rename("Avg_2018_19"), post.rename("Avg_2024_25")], axis=1).dropna()
    chg["Change"] = chg["Avg_2024_25"] - chg["Avg_2018_19"]
    chg["Change_pct"] = (chg["Change"] / chg["Avg_2018_19"] * 100).round(1)
    chg = chg.sort_values("Change")
    print(f"Stations comparable in both periods: {len(chg)}")
    print(f"Worsened: {(chg['Change'] > 0).sum()} | Improved: {(chg['Change'] < 0).sum()}")
    print("\nMost improved:\n", chg.head(5).round(1).to_string())
    print("\nMost worsened:\n", chg.tail(5).round(1).to_string())
chg.to_csv(TABLES / "station_change.csv")
sel = pd.concat([chg.head(10), chg.tail(10)])
fig, ax = plt.subplots(figsize=(9.5, 6))
cols = [BLUE if v < 0 else "#e34948" for v in sel["Change"]]
ax.barh(sel.index, sel["Change"], color=cols)
ax.axvline(0, color=INK, lw=.8)
for i, (v, p) in enumerate(zip(sel["Change"], sel["Change_pct"])):
    ax.text(v + (2 if v >= 0 else -2), i, f"{v:+.0f} ({p:+.0f}%)", va="center", ha="left" if v >= 0 else "right", fontsize=8.5)
ax.set_xlim(sel["Change"].min() - 30, sel["Change"].max() + 30)
ax.grid(axis="x"); ax.grid(axis="y", visible=False)
ax.set_xlabel("Change in average crashes per year (2024-25 vs 2018-19)")
ax.set_title("Ten most-improved (blue) and ten most-worsened (red) stations")
savefig("fig13_station_change")

record(uni=uni.reset_index().to_dict("records"), top10_share=round(top10_share, 1), top20pct_n=top20pct_n,
       top20pct_share=round(top20pct_share, 1), gini=round(gini, 3), n_stations_recent=n,
       city_slope=round(lr.slope, 1), city_r2=round(lr.rvalue ** 2, 2), city_p=lr.pvalue,
       kendall_tau=round(tau.statistic, 2), kendall_p=tau.pvalue,
       fr_slope=round(lr2.slope, 3), fr_r2=round(lr2.rvalue ** 2, 2), fr_p=lr2.pvalue,
       city=city.to_dict("records"), zone_year=zy.to_dict(), zone_share=zshare_pct.to_dict(),
       zone_abs=zshare.astype(int).to_dict(), kw_H=round(kw.statistic, 2), kw_p=kw.pvalue,
       chi2=round(chi.statistic, 2), chi_p=chi.pvalue, zone_fr_mean=means.round(2).to_dict(),
       zone_fatal_share=(ct["Fatal"] / ct.sum(axis=1) * 100).round(1).to_dict(),
       top_stations=rank.head(15).to_dict("records"), r_fatal_total=round(r.statistic, 2),
       fit_m=round(m, 3), fit_b=round(b, 2),
       deadly=rank.sort_values("Excess_Fatal", ascending=False).head(6).to_dict("records"),
       n_change=len(chg), n_worse=int((chg["Change"] > 0).sum()), n_better=int((chg["Change"] < 0).sum()),
       most_improved=chg.head(5).round(1).reset_index().to_dict("records"),
       most_worsened=chg.tail(5).round(1).reset_index().to_dict("records"),
       fr_gt25=int((fr > 25).sum()))
