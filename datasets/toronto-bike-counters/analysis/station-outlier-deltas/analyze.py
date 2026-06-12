import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parents[3]
RAW_DIR = REPO_ROOT / "datasets" / "toronto-bike-counters" / "raw"
OUTPUTS_DIR = Path(__file__).resolve().parent / "outputs"
OUTPUTS_DIR.mkdir(exist_ok=True)

MIN_PRIOR_YEARS = 3
MIN_DAYS_2025 = 15
OUTLIER_Z_THRESHOLD = 2

daily = pd.read_csv(RAW_DIR / "cycling-permanent-counts-daily.csv", parse_dates=["dt"])
locs = pd.read_csv(RAW_DIR / "cycling-permanent-counts-locations.csv")

active_locs = locs[locs["date_decommissioned"].isna()].copy()

daily["year"] = daily["dt"].dt.year
daily["month"] = daily["dt"].dt.month

direction_pairs = {
    "Eastbound": "Westbound",
    "Westbound": "Eastbound",
    "Northbound": "Southbound",
    "Southbound": "Northbound",
}


def get_location_base_name(name):
    return name.replace(" (retired)", "").strip()


active_locs["base_name"] = active_locs["location_name"].apply(get_location_base_name)

active_ids = set(active_locs["location_dir_id"])
daily_active = daily[daily["location_dir_id"].isin(active_ids)].copy()

daily_active = daily_active.merge(
    active_locs[["location_dir_id", "base_name"]],
    on="location_dir_id",
    how="left",
)

direction_reported = (
    daily_active.groupby(["base_name", "dt"])["direction"].nunique().reset_index()
)
direction_reported.columns = ["base_name", "dt", "n_directions"]

daily_active = daily_active.merge(
    direction_reported, on=["base_name", "dt"], how="left"
)

expected_directions = active_locs.groupby("base_name")["direction"].nunique().to_dict()
daily_active["expected_directions"] = daily_active["base_name"].map(expected_directions)
daily_active = daily_active[
    daily_active["n_directions"] == daily_active["expected_directions"]
].copy()

merged = (
    daily_active.groupby(["base_name", "year", "month", "dt"])
    .agg(daily_volume=("daily_volume", "sum"))
    .reset_index()
)

historical = merged[merged["year"] < 2025].copy()
current = merged[merged["year"] == 2025].copy()

historical_monthly = (
    historical.groupby(["base_name", "month", "year"])
    .agg(mean_daily=("daily_volume", "mean"))
    .reset_index()
)

baseline = (
    historical_monthly.groupby(["base_name", "month"])
    .agg(
        historical_mean_daily=("mean_daily", "mean"),
        historical_std_daily=("mean_daily", "std"),
        n_prior_years=("mean_daily", "count"),
    )
    .reset_index()
)

baseline = baseline[baseline["n_prior_years"] >= MIN_PRIOR_YEARS].copy()

current_monthly = (
    current.groupby(["base_name", "month"])
    .agg(
        actual_mean_daily=("daily_volume", "mean"),
        n_days_2025=("daily_volume", "count"),
    )
    .reset_index()
)

current_monthly = current_monthly[
    current_monthly["n_days_2025"] >= MIN_DAYS_2025
].copy()

results = current_monthly.merge(baseline, on=["base_name", "month"], how="inner")

results["delta"] = results["actual_mean_daily"] - results["historical_mean_daily"]
results["z_score"] = results["delta"] / results["historical_std_daily"]
results["is_outlier"] = results["z_score"].abs() > OUTLIER_Z_THRESHOLD

results = results.sort_values(["base_name", "month"]).reset_index(drop=True)

monthly_zscores = results[
    [
        "base_name",
        "month",
        "actual_mean_daily",
        "historical_mean_daily",
        "historical_std_daily",
        "delta",
        "z_score",
        "is_outlier",
    ]
].rename(columns={"base_name": "location_name"})
monthly_zscores.to_csv(OUTPUTS_DIR / "monthly-zscores.csv", index=False)

outlier_events = results[results["is_outlier"]].copy()
outlier_events["direction"] = np.where(
    outlier_events["delta"] > 0, "above baseline", "below baseline"
)
outlier_csv = outlier_events[
    [
        "base_name",
        "month",
        "actual_mean_daily",
        "historical_mean_daily",
        "delta",
        "z_score",
        "direction",
    ]
].rename(columns={"base_name": "location_name"})
outlier_csv.to_csv(OUTPUTS_DIR / "outlier-events.csv", index=False)

# --- Figure a: Heatmap ---
heatmap_data = results.pivot_table(
    index="base_name", columns="month", values="z_score", aggfunc="first"
)

fig_a, ax_a = plt.subplots(figsize=(14, max(6, len(heatmap_data) * 0.45)))
sns.heatmap(
    heatmap_data,
    cmap="RdBu_r",
    center=0,
    annot=True,
    fmt=".1f",
    linewidths=0.5,
    linecolor="white",
    cbar_kws={"label": "z-score"},
    ax=ax_a,
    mask=heatmap_data.isna(),
)

for i in range(heatmap_data.shape[0]):
    for j in range(heatmap_data.shape[1]):
        val = heatmap_data.iloc[i, j]
        if pd.notna(val) and abs(val) > OUTLIER_Z_THRESHOLD:
            ax_a.add_patch(
                plt.Rectangle(
                    (j, i), 1, 1, fill=False, edgecolor="black", linewidth=2.5
                )
            )

ax_a.set_title(
    "Toronto Bike Counters 2025: Monthly traffic vs historical baseline (z-scores)"
)
ax_a.set_xlabel("Month")
ax_a.set_ylabel("")
month_labels = [str(m) for m in range(1, 13)]
ax_a.set_xticks([i + 0.5 for i in range(12)])
ax_a.set_xticklabels(month_labels)
fig_a.tight_layout()
fig_a.savefig(OUTPUTS_DIR / "outlier-months-heatmap.png", dpi=150)
plt.close(fig_a)

# --- Figure b: Top outlier deltas ---
top_outliers = results[results["is_outlier"]].copy()
top_outliers["abs_z"] = top_outliers["z_score"].abs()
top_outliers = top_outliers.nlargest(10, "abs_z")
top_outliers["label"] = (
    top_outliers["base_name"] + " (M" + top_outliers["month"].astype(str) + ")"
)
top_outliers = top_outliers.sort_values("z_score")

fig_b, ax_b = plt.subplots(figsize=(10, 6))
colors = ["#d62728" if z > 0 else "#1f77b4" for z in top_outliers["z_score"]]
ax_b.barh(
    top_outliers["label"],
    top_outliers["z_score"],
    color=colors,
    edgecolor="black",
    linewidth=0.5,
)
ax_b.axvline(0, color="black", linewidth=0.8)
ax_b.set_xlabel("z-score")
ax_b.set_title("Toronto Bike Counters 2025: Biggest deviations from historical norm")
ax_b.set_ylabel("")
for i, (z, label) in enumerate(zip(top_outliers["z_score"], top_outliers["label"])):
    ax_b.text(
        z + (0.1 if z >= 0 else -0.1),
        i,
        f"{z:.2f}",
        va="center",
        ha="left" if z >= 0 else "right",
        fontsize=9,
    )
fig_b.tight_layout()
fig_b.savefig(OUTPUTS_DIR / "top-outlier-deltas.png", dpi=150)
plt.close(fig_b)

print("=" * 60)
print("OUTLIER EVENTS")
print("=" * 60)
for _, row in outlier_csv.iterrows():
    print(
        f"  {row['location_name']:45s}  M{row['month']:2d}  z={row['z_score']:+.2f}  {row['direction']}"
    )

print()
print("=" * 60)
print("LOCATIONS WITH MOST OUTLIER MONTHS")
print("=" * 60)
outlier_counts = (
    outlier_csv.groupby("location_name").size().sort_values(ascending=False)
)
for loc, count in outlier_counts.items():
    print(f"  {loc:45s}  {count} outlier month(s)")

print()
print("=" * 60)
print("BIGGEST DELTAS")
print("=" * 60)
all_results = results.dropna(subset=["z_score"])
if len(all_results) > 0:
    max_pos = all_results.loc[all_results["z_score"].idxmax()]
    max_neg = all_results.loc[all_results["z_score"].idxmin()]
    print(
        f"  Biggest positive: {max_pos['base_name']} M{max_pos['month']:.0f}  z={max_pos['z_score']:+.2f}  delta={max_pos['delta']:+.1f}"
    )
    print(
        f"  Biggest negative: {max_neg['base_name']} M{max_neg['month']:.0f}  z={max_neg['z_score']:+.2f}  delta={max_neg['delta']:+.1f}"
    )

print()
print(f"Wrote {OUTPUTS_DIR / 'monthly-zscores.csv'}")
print(f"Wrote {OUTPUTS_DIR / 'outlier-events.csv'}")
print(f"Wrote {OUTPUTS_DIR / 'outlier-months-heatmap.png'}")
print(f"Wrote {OUTPUTS_DIR / 'top-outlier-deltas.png'}")
