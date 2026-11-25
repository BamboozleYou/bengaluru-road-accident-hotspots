"""MODULE 1 - Data acquisition and understanding.                 Author: Member 1

Loads the eight raw CSV files exactly as published on the OpenCity Urban Data Portal,
documents their structure, and reshapes the five year-wise Bengaluru Traffic Police
station files (each with a different layout) into one tidy Station x Year table.
"""
import numpy as np
import pandas as pd

from common import RAW, TABLES, record, save, step

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

with step("m1_load"):
    # Read every column as text first so nothing is silently converted;
    # utf-8-sig removes the invisible byte-order mark some files start with.
    raw = {k: pd.read_csv(RAW / f, encoding="utf-8-sig", dtype=str) for k, f in RAW_FILES.items()}
    inventory = pd.DataFrame([{"Dataset": k, "File": RAW_FILES[k], "Rows": d.shape[0], "Columns": d.shape[1]}
                              for k, d in raw.items()])
    print(inventory.to_string(index=False))

with step("m1_inspect"):
    print(raw["btp_2018_2020"].iloc[:4, :8].to_string(index=False))
    print("\nLast column name :", repr(raw["btp_2018_2020"].columns[-1]))
    print("City 'Total' value:", repr(raw["city_annual"].loc[0, "Total"]), "->", type(raw["city_annual"].loc[0, "Total"]))
    print("\nColumns per BTP file:", {k: raw[k].shape[1] for k in RAW_FILES if k.startswith("btp")})
    print("\nTail of 2025 file (sub-total rows mixed with data):")
    print(raw["btp_2025"].tail(4).to_string(index=False))
inventory.to_csv(TABLES / "raw_inventory.csv", index=False)


def tidy_wide(df, years, has_subdiv):
    """Convert one wide 'YYYY - Metric' BTP file into long format (one row per station-year)."""
    df = df.copy()
    df.columns = [c.strip() for c in df.columns]

    def pick(r, *names):
        for n in names:
            if n in df.columns:
                return r[n]
        return np.nan

    rows = []
    for _, r in df.iterrows():
        for y in years:
            rows.append({
                "Zone_reported": r["Zone"],
                "Sub_division": r["Sub-division"] if has_subdiv else np.nan,
                "Station_raw": r["Station"],
                "Year": y,
                "Fatal": pick(r, f"{y} - Fatal", f"{y} - Fatal Cases", f"{y}-Fatal crashes"),
                "Killed": pick(r, f"{y} - Killed", f"{y} - Killed People"),
                "Non_Fatal": pick(r, f"{y} - Non-Fatal", f"{y}-Non Fatal"),
                "Injured": pick(r, f"{y} - Injured", f"{y} - Injured People"),
                "Total": pick(r, f"{y} - Total Cases", f"{y}-Total crashes"),
            })
    return pd.DataFrame(rows)


with step("m1_reshape"):
    parts = [
        tidy_wide(raw["btp_2018_2020"], [2018, 2019, 2020], False).assign(Source_file=RAW_FILES["btp_2018_2020"]),
        tidy_wide(raw["btp_2021_2022"], [2021, 2022], False).assign(Source_file=RAW_FILES["btp_2021_2022"]),
        tidy_wide(raw["btp_2023"], [2023], True).assign(Source_file=RAW_FILES["btp_2023"]),
        tidy_wide(raw["btp_2024"], [2024], True).assign(Source_file=RAW_FILES["btp_2024"]),
        tidy_wide(raw["btp_2025"], [2025], True).assign(Source_file=RAW_FILES["btp_2025"]),
    ]
    stations_raw = pd.concat(parts, ignore_index=True)
    print("Combined long table (before cleaning):", stations_raw.shape)
    print(stations_raw.head(6).drop(columns="Source_file").to_string())
    print("\nRows per year:", stations_raw["Year"].value_counts().sort_index().to_dict())

with step("m1_info"):
    stations_raw.info()

save(raw, "raw")
save(stations_raw, "stations_raw")
record(raw_inventory=inventory.to_dict("records"), raw_long_shape=list(stations_raw.shape))
