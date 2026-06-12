from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parents[3]
DATA_DIR = REPO_ROOT / "datasets" / "toronto-bike-counters" / "raw"
OUTPUT_DIR = Path(__file__).resolve().parent / "outputs"
OUTPUT_DIR.mkdir(exist_ok=True)

daily = pd.read_csv(DATA_DIR / "cycling-permanent-counts-daily.csv", parse_dates=["dt"])
locs = pd.read_csv(DATA_DIR / "cycling-permanent-counts-locations.csv")

active_ids = locs.loc[
    locs["date_decommissioned"].isna() | (locs["date_decommissioned"] == ""),
    "location_dir_id",
].values
df = daily[daily["location_dir_id"].isin(active_ids)].copy()

merged = (
    df.groupby(["location_name", "dt"])
    .agg(daily_volume=("daily_volume", "sum"))
    .reset_index()
)
merged["year"] = merged["dt"].dt.year
merged["month"] = merged["dt"].dt.month
merged["dow"] = merged["dt"].dt.dayofweek
merged["day_name"] = merged["dt"].dt.day_name()

CURRENT_YEAR = 2026
COMPLETE_YEARS = sorted(y for y in merged["year"].unique() if y < CURRENT_YEAR)

vol_2024 = merged[merged["year"] == 2024].groupby("location_name")["daily_volume"].sum()
top4 = vol_2024.nlargest(4).index.tolist()

monthly = (
    merged.groupby(["location_name", "year", "month"])
    .agg(
        mean_daily_volume=("daily_volume", "mean"),
        total_volume=("daily_volume", "sum"),
        days_with_data=("daily_volume", "count"),
    )
    .reset_index()
)
monthly.to_csv(OUTPUT_DIR / "monthly-by-location.csv", index=False)

fig, axes = plt.subplots(2, 2, figsize=(14, 10), sharey=False)
axes = axes.flatten()
palette = {2022: "#1f77b4", 2023: "#ff7f0e", 2024: "#2ca02c", 2025: "#d62728"}
for i, loc in enumerate(top4):
    ax = axes[i]
    sub = monthly[monthly["location_name"] == loc]
    for yr in sorted(sub["year"].unique()):
        if yr < 2022:
            continue
        s = sub[sub["year"] == yr]
        ax.plot(
            s["month"],
            s["mean_daily_volume"],
            marker="o",
            label=str(yr),
            color=palette.get(yr, "#999999"),
        )
    ax.set_title(loc, fontsize=9)
    ax.set_xlabel("Month")
    ax.set_ylabel("Mean daily volume")
    ax.set_xticks(range(1, 13))
    ax.legend(fontsize=7)
    ax.grid(True, alpha=0.3)
fig.suptitle("Toronto Bike Counters: Seasonal pattern by year", fontsize=14)
fig.tight_layout()
fig.savefig(OUTPUT_DIR / "monthly-seasonality.png", dpi=150)
plt.close(fig)

dow_2024 = merged[merged["year"] == 2024].copy()
dow_order = [
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday",
]
dow_2024["day_name"] = pd.Categorical(
    dow_2024["day_name"], categories=dow_order, ordered=True
)
dow_stats = (
    dow_2024[dow_2024["location_name"].isin(top4)]
    .groupby(["location_name", "day_name"], observed=False)["daily_volume"]
    .mean()
    .reset_index()
)

fig, axes = plt.subplots(2, 2, figsize=(14, 10), sharey=False)
axes = axes.flatten()
for i, loc in enumerate(top4):
    ax = axes[i]
    sub = dow_stats[dow_stats["location_name"] == loc]
    ax.bar(sub["day_name"], sub["daily_volume"], color="#4c78a8")
    ax.set_title(loc, fontsize=9)
    ax.set_xlabel("Day of week")
    ax.set_ylabel("Mean daily volume")
    ax.tick_params(axis="x", rotation=45)
    ax.grid(True, alpha=0.3, axis="y")
fig.suptitle("Toronto Bike Counters 2024: Traffic by day of week", fontsize=14)
fig.tight_layout()
fig.savefig(OUTPUT_DIR / "day-of-week.png", dpi=150)
plt.close(fig)

counter_year_days = (
    merged.groupby(["location_name", "year"])["daily_volume"]
    .agg(annual_volume="sum", days_active="count")
    .reset_index()
)

yoy_rows = []
for y_prev, y_curr in zip(COMPLETE_YEARS[:-1], COMPLETE_YEARS[1:]):
    prev = counter_year_days[counter_year_days["year"] == y_prev].set_index(
        "location_name"
    )
    curr = counter_year_days[counter_year_days["year"] == y_curr].set_index(
        "location_name"
    )
    common = prev.index.intersection(curr.index)
    mask = (prev.loc[common, "days_active"] >= 200) & (
        curr.loc[common, "days_active"] >= 200
    )
    like_for_like = common[mask]
    if len(like_for_like) == 0:
        continue
    total_prev = prev.loc[like_for_like, "annual_volume"].sum()
    total_curr = curr.loc[like_for_like, "annual_volume"].sum()
    pct = (total_curr - total_prev) / total_prev * 100
    yoy_rows.append(
        {
            "year": y_curr,
            "yoy_pct_change": round(pct, 2),
            "n_like_for_like": len(like_for_like),
        }
    )

annual_summary = (
    merged[merged["year"].isin(COMPLETE_YEARS)]
    .groupby("year")
    .agg(
        n_counters_active=("location_name", "nunique"),
        total_volume=("daily_volume", "sum"),
        mean_daily_per_counter=("daily_volume", "mean"),
    )
    .reset_index()
)
annual_summary["mean_daily_per_counter"] = annual_summary[
    "mean_daily_per_counter"
].round(1)

yoy_df = pd.DataFrame(yoy_rows)
if not yoy_df.empty:
    annual_summary = annual_summary.merge(
        yoy_df[["year", "yoy_pct_change"]], on="year", how="left"
    )
else:
    annual_summary["yoy_pct_change"] = np.nan

annual_summary.to_csv(OUTPUT_DIR / "annual-summary.csv", index=False)

if not yoy_df.empty:
    fig, ax = plt.subplots(figsize=(8, 5))
    bars = ax.bar(yoy_df["year"], yoy_df["yoy_pct_change"], color="#4c78a8")
    ax.axhline(0, color="black", linewidth=0.8)
    ax.set_xlabel("Year")
    ax.set_ylabel("YoY % change in total volume")
    ax.set_title(
        "Toronto Bike Counters: Year-over-year growth (like-for-like counters)"
    )
    for bar, val in zip(bars, yoy_df["yoy_pct_change"]):
        offset = 0.5 if val >= 0 else -0.5
        va = "bottom" if val >= 0 else "top"
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + offset,
            f"{val:+.1f}%",
            ha="center",
            va=va,
            fontsize=9,
        )
    ax.grid(True, alpha=0.3, axis="y")
    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / "yoy-growth.png", dpi=150)
    plt.close(fig)

FULL_YEAR_MIN_DAYS = 340
PAIR_YEARS = [(2023, 2024), (2024, 2025)]

always_on_pairs = {}
for y_prev, y_curr in PAIR_YEARS:
    prev_locs = set(
        counter_year_days[
            (counter_year_days["year"] == y_prev)
            & (counter_year_days["days_active"] >= FULL_YEAR_MIN_DAYS)
        ]["location_name"]
    )
    curr_locs = set(
        counter_year_days[
            (counter_year_days["year"] == y_curr)
            & (counter_year_days["days_active"] >= FULL_YEAR_MIN_DAYS)
        ]["location_name"]
    )
    always_on_pairs[(y_prev, y_curr)] = sorted(prev_locs & curr_locs)

always_on_yoy_rows = []
for y_prev, y_curr in PAIR_YEARS:
    locs_pair = always_on_pairs[(y_prev, y_curr)]
    if len(locs_pair) == 0:
        continue
    prev = counter_year_days[
        (counter_year_days["year"] == y_prev)
        & (counter_year_days["location_name"].isin(locs_pair))
    ].set_index("location_name")
    curr = counter_year_days[
        (counter_year_days["year"] == y_curr)
        & (counter_year_days["location_name"].isin(locs_pair))
    ].set_index("location_name")
    total_prev = prev["annual_volume"].sum()
    total_curr = curr["annual_volume"].sum()
    pct = (total_curr - total_prev) / total_prev * 100
    always_on_yoy_rows.append(
        {
            "year": y_curr,
            "yoy_pct_change": round(pct, 2),
            "n_always_on": len(locs_pair),
        }
    )

always_on_yoy_df = pd.DataFrame(always_on_yoy_rows)
always_on_yoy_df.to_csv(OUTPUT_DIR / "always-on-yoy.csv", index=False)

if not always_on_yoy_df.empty:
    fig, ax = plt.subplots(figsize=(10, 5))
    x = np.arange(len(always_on_yoy_df))
    width = 0.35
    all_bars = ax.bar(
        x - width / 2,
        yoy_df[yoy_df["year"].isin(always_on_yoy_df["year"])]["yoy_pct_change"].values,
        width,
        label="Like-for-like (>= 200 days)",
        color="#4c78a8",
        alpha=0.7,
    )
    pair_n = [always_on_pairs[(y - 1, y)] for y in always_on_yoy_df["year"]]
    on_bars = ax.bar(
        x + width / 2,
        always_on_yoy_df["yoy_pct_change"].values,
        width,
        label=f"Always-on (>= {FULL_YEAR_MIN_DAYS} days both years)",
        color="#e45756",
        alpha=0.9,
    )
    ax.axhline(0, color="black", linewidth=0.8)
    ax.set_xlabel("Year")
    ax.set_ylabel("YoY % change in total volume")
    ax.set_title(
        "Toronto Bike Counters: YoY growth — like-for-like vs always-on counters"
    )
    ax.set_xticks(x)
    ax.set_xticklabels(
        [
            f"{int(y)}\n({len(pair_n[i])} always-on)"
            for i, y in enumerate(always_on_yoy_df["year"])
        ]
    )
    ax.legend(fontsize=9)
    for bar, val in zip(
        all_bars,
        yoy_df[yoy_df["year"].isin(always_on_yoy_df["year"])]["yoy_pct_change"].values,
    ):
        offset = 0.5 if val >= 0 else -0.5
        va = "bottom" if val >= 0 else "top"
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + offset,
            f"{val:+.1f}%",
            ha="center",
            va=va,
            fontsize=8,
        )
    for bar, val in zip(on_bars, always_on_yoy_df["yoy_pct_change"].values):
        offset = 0.5 if val >= 0 else -0.5
        va = "bottom" if val >= 0 else "top"
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + offset,
            f"{val:+.1f}%",
            ha="center",
            va=va,
            fontsize=8,
        )
    ax.grid(True, alpha=0.3, axis="y")
    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / "yoy-growth-comparison.png", dpi=150)
    plt.close(fig)

print("=== Annual Summary ===")
print(annual_summary.to_string(index=False))
print()

if not always_on_yoy_df.empty:
    print("=== Always-on YoY (>= 340 days in both years) ===")
    print(always_on_yoy_df.to_string(index=False))
    for (y_prev, y_curr), locs_pair in always_on_pairs.items():
        print(f"  {y_prev}->{y_curr}: {len(locs_pair)} locations - {locs_pair}")
print()

peak = monthly.loc[monthly["mean_daily_volume"].idxmax()]
print(
    f"Peak month: {peak['month']:.0f}/{peak['year']:.0f} "
    f"at {peak['location_name']} "
    f"(mean daily vol: {peak['mean_daily_volume']:.0f})"
)
print()

weekday = merged[merged["dow"] < 5]["daily_volume"].mean()
weekend = merged[merged["dow"] >= 5]["daily_volume"].mean()
print(
    f"Weekend/weekday ratio: {weekend / weekday:.2f} "
    f"(weekend mean: {weekend:.0f}, weekday mean: {weekday:.0f})"
)
