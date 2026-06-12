import pathlib
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Patch

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parents[3]
RAW_DIR = REPO_ROOT / "datasets" / "toronto-bike-counters" / "raw"
OUTPUTS_DIR = pathlib.Path(__file__).resolve().parent / "outputs"
OUTPUTS_DIR.mkdir(exist_ok=True)

MIN_DAYS_PER_YEAR = 100
MIN_PRIOR_YEARS = 3
CURRENT_YEAR = 2025


def load_data():
    locs = pd.read_csv(RAW_DIR / "cycling-permanent-counts-locations.csv")
    daily = pd.read_csv(
        RAW_DIR / "cycling-permanent-counts-daily.csv", parse_dates=["dt"]
    )
    return locs, daily


def filter_active(locs):
    return locs[locs["date_decommissioned"].isna()].copy()


def build_location_pairs(active_locs):
    grouped = active_locs.groupby("location_name")
    pair_map = {}
    for name, grp in grouped:
        dirs = grp.sort_values("direction")
        pair_map[name] = dirs["location_dir_id"].tolist()
    return pair_map


def compute_yearly_means(daily, active_locs):
    df = daily[daily["location_dir_id"].isin(active_locs["location_dir_id"])].copy()
    df["year"] = df["dt"].dt.year
    yearly = (
        df.groupby(["location_dir_id", "year"])
        .agg(
            mean_daily_volume=("daily_volume", "mean"),
            days_with_data=("daily_volume", "count"),
        )
        .reset_index()
    )
    yearly = yearly[yearly["days_with_data"] >= MIN_DAYS_PER_YEAR]
    return yearly


def compute_combined_yearly(yearly, dir_ids):
    subset = yearly[yearly["location_dir_id"].isin(dir_ids)]
    combined = (
        subset.groupby("year")
        .agg(
            mean_daily_volume=("mean_daily_volume", "sum"),
            days_with_data=("days_with_data", "max"),
        )
        .reset_index()
    )
    return combined


def compute_percentile(prior_means, current_mean):
    n_prior = len(prior_means)
    n_lower = (prior_means < current_mean).sum()
    percentile = n_lower / n_prior * 100
    rank_val = n_lower + 1
    return {
        "percentile": round(percentile, 1),
        "rank": f"{rank_val}/{n_prior}",
        "rank_val": rank_val,
        "n_prior": n_prior,
    }


def compute_all_percentiles(yearly, active_locs):
    pair_map = build_location_pairs(active_locs)
    dir_lookup_name = dict(
        zip(active_locs["location_dir_id"], active_locs["location_name"])
    )
    dir_lookup_dir = dict(zip(active_locs["location_dir_id"], active_locs["direction"]))

    results = []

    for loc_name, dir_ids in pair_map.items():
        is_pair = len(dir_ids) == 2

        if is_pair:
            combined = compute_combined_yearly(yearly, dir_ids)
            combined["location_name"] = loc_name
            combined["direction"] = "Combined"
            combined["location_dir_id"] = ",".join(str(d) for d in sorted(dir_ids))
            res = _compute_entry(combined, CURRENT_YEAR)
            if res:
                res["location_name"] = loc_name
                res["location_dir_ids"] = ",".join(str(d) for d in sorted(dir_ids))
                res["direction"] = "Combined"
                results.append(res)

        for did in dir_ids:
            subset = yearly[yearly["location_dir_id"] == did].copy()
            if subset.empty:
                continue
            subset = subset.copy()
            subset["location_name"] = dir_lookup_name[did]
            subset["direction"] = dir_lookup_dir[did]
            res = _compute_entry(subset, CURRENT_YEAR)
            if res:
                res["location_name"] = dir_lookup_name[did]
                res["location_dir_ids"] = str(did)
                res["direction"] = dir_lookup_dir[did]
                results.append(res)

    return pd.DataFrame(results)


def _compute_entry(df, current_year):
    prior = df[df["year"] < current_year]
    current = df[df["year"] == current_year]
    if len(prior) < MIN_PRIOR_YEARS or current.empty:
        return None

    current_mean = float(current.iloc[0]["mean_daily_volume"])
    hist_avg = float(prior["mean_daily_volume"].mean())
    pct_change = (
        ((current_mean - hist_avg) / hist_avg) * 100 if hist_avg > 0 else np.nan
    )

    pctl = compute_percentile(prior["mean_daily_volume"].values, current_mean)

    return {
        "years_of_data": pctl["n_prior"] + 1,
        "rank": pctl["rank"],
        "percentile_2025": pctl["percentile"],
        "mean_daily_2025": round(current_mean, 1),
        "mean_daily_historical_avg": round(hist_avg, 1),
        "pct_change_vs_avg": round(pct_change, 1),
    }


def build_yearly_means_csv(yearly, active_locs):
    dir_lookup_name = dict(
        zip(active_locs["location_dir_id"], active_locs["location_name"])
    )
    dir_lookup_dir = dict(zip(active_locs["location_dir_id"], active_locs["direction"]))

    out = yearly.copy()
    out["location_name"] = out["location_dir_id"].map(dir_lookup_name)
    out["direction"] = out["location_dir_id"].map(dir_lookup_dir)
    out = out[
        [
            "location_dir_id",
            "location_name",
            "direction",
            "year",
            "mean_daily_volume",
            "days_with_data",
        ]
    ]
    out = out.sort_values(["location_dir_id", "year"]).reset_index(drop=True)
    out["mean_daily_volume"] = out["mean_daily_volume"].round(1)
    return out


def build_excluded_report(yearly, active_locs):
    pair_map = build_location_pairs(active_locs)
    dir_lookup_name = dict(
        zip(active_locs["location_dir_id"], active_locs["location_name"])
    )
    dir_lookup_dir = dict(zip(active_locs["location_dir_id"], active_locs["direction"]))

    excluded = []
    for loc_name, dir_ids in pair_map.items():
        for did in dir_ids:
            subset = yearly[yearly["location_dir_id"] == did]
            prior = subset[subset["year"] < CURRENT_YEAR]
            current = subset[subset["year"] == CURRENT_YEAR]
            reason = []
            if len(prior) < MIN_PRIOR_YEARS:
                reason.append(f"only {len(prior)} prior year(s)")
            if current.empty:
                reason.append("no 2025 data")
            elif current.iloc[0]["days_with_data"] < MIN_DAYS_PER_YEAR:
                reason.append(
                    f"only {int(current.iloc[0]['days_with_data'])} days in 2025"
                )
            if reason:
                excluded.append(
                    {
                        "location_dir_id": did,
                        "location_name": dir_lookup_name[did],
                        "direction": dir_lookup_dir[did],
                        "reason": "; ".join(reason),
                    }
                )
    return pd.DataFrame(excluded)


def plot_percentile_ranks(pct_df):
    chart_df = pct_df.copy()
    chart_df["label"] = chart_df.apply(
        lambda r: f"{r['location_name']} ({r['direction']})"
        if r["direction"] != "Combined"
        else r["location_name"],
        axis=1,
    )
    chart_df = chart_df.sort_values("percentile_2025")

    fig, ax = plt.subplots(figsize=(14, max(5, len(chart_df) * 0.5)))

    colors = []
    for p in chart_df["percentile_2025"]:
        if p >= 75:
            colors.append("#2ca02c")
        elif p >= 25:
            colors.append("#ffbb00")
        else:
            colors.append("#d62728")

    bars = ax.barh(
        chart_df["label"],
        chart_df["percentile_2025"],
        color=colors,
        edgecolor="white",
        height=0.6,
    )

    for bar, (_, row) in zip(bars, chart_df.iterrows()):
        pct = row["percentile_2025"]
        rank_str = row["rank"]
        ax.text(
            bar.get_width() + 1.5,
            bar.get_y() + bar.get_height() / 2,
            f"{pct:.0f}% ({rank_str})",
            va="center",
            fontsize=8,
        )

    ax.set_xlim(0, 115)
    ax.set_xlabel("2025 Percentile Rank (%)")
    ax.set_title(
        "Toronto Bike Counters 2025: Where does this year rank historically?",
        fontsize=13,
        fontweight="bold",
    )
    ax.axvline(25, color="#d62728", linestyle="--", alpha=0.4, linewidth=0.8)
    ax.axvline(75, color="#2ca02c", linestyle="--", alpha=0.4, linewidth=0.8)

    legend_elements = [
        Patch(facecolor="#2ca02c", label=">= 75th percentile"),
        Patch(facecolor="#ffbb00", label="25th-75th percentile"),
        Patch(facecolor="#d62728", label="< 25th percentile"),
    ]
    ax.legend(handles=legend_elements, loc="lower right", fontsize=8)
    ax.text(
        0.5,
        -0.08,
        "Note: Most active counters (installed 2022-2023) have only 2 prior years, below the 3-year minimum. "
        "Only counters with >=3 prior years and >=100 days in 2025 are shown.",
        transform=ax.transAxes,
        fontsize=7,
        ha="center",
        color="#666666",
    )

    plt.tight_layout()
    fig.savefig(OUTPUTS_DIR / "percentile-rank-chart.png", dpi=150, bbox_inches="tight")
    plt.close(fig)


def plot_directional_breakdown(yearly, pct_df, active_locs):
    combined = pct_df[pct_df["direction"] == "Combined"]
    if combined.empty:
        return

    top_locs = combined.nlargest(6, "mean_daily_2025")["location_name"].tolist()

    dir_lookup = dict(zip(active_locs["location_dir_id"], active_locs["direction"]))

    n_locs = len(top_locs)
    n_cols = min(3, n_locs)
    n_rows = (n_locs + n_cols - 1) // n_cols

    fig, axes = plt.subplots(n_rows, n_cols, figsize=(6 * n_cols, 5 * n_rows))
    if n_locs == 1:
        axes = np.array([[axes]])
    elif n_rows == 1:
        axes = axes.reshape(1, -1)

    loc_groups = active_locs.groupby("location_name")

    for idx, loc_name in enumerate(top_locs):
        ax = axes[idx // n_cols][idx % n_cols]
        if loc_name not in loc_groups.groups:
            ax.set_visible(False)
            continue

        grp = loc_groups.get_group(loc_name)
        dir_ids = grp["location_dir_id"].tolist()

        bar_width = 0.35
        years_all = sorted(
            yearly[yearly["location_dir_id"].isin(dir_ids)]["year"].unique()
        )

        x = np.arange(len(years_all))
        offsets = np.arange(len(dir_ids)) - (len(dir_ids) - 1) / 2

        for i, did in enumerate(dir_ids):
            sub = yearly[yearly["location_dir_id"] == did].sort_values("year")
            dir_name = dir_lookup[did]
            means = []
            for yr in years_all:
                yr_data = sub[sub["year"] == yr]
                means.append(
                    float(yr_data["mean_daily_volume"].iloc[0])
                    if len(yr_data) > 0
                    else 0
                )
            bar_colors = [
                "#2ca02c" if yr == CURRENT_YEAR else "#999999" for yr in years_all
            ]
            ax.bar(
                x + offsets[i] * bar_width,
                means,
                bar_width * 0.9,
                label=dir_name,
                color=bar_colors,
                edgecolor="white",
            )

        hist_mean = combined[combined["location_name"] == loc_name][
            "mean_daily_historical_avg"
        ].values[0]
        ax.axhline(
            hist_mean,
            color="#d62728",
            linestyle="--",
            linewidth=0.8,
            alpha=0.7,
            label="Historical avg",
        )

        ax.set_xticks(x)
        ax.set_xticklabels([str(y) for y in years_all], fontsize=8)
        ax.set_title(loc_name, fontsize=9, fontweight="bold")
        ax.set_ylabel("Mean daily volume", fontsize=8)
        ax.legend(fontsize=7, loc="upper left")

    for idx in range(n_locs, n_rows * n_cols):
        axes[idx // n_cols][idx % n_cols].set_visible(False)

    fig.suptitle(
        "Toronto Bike Counters 2025: Directional traffic vs historical average\n(green = 2025, grey = prior years, dashed red = historical average)",
        fontsize=12,
        fontweight="bold",
    )
    plt.tight_layout()
    fig.savefig(OUTPUTS_DIR / "directional-breakdown.png", dpi=150, bbox_inches="tight")
    plt.close(fig)


def main():
    locs, daily = load_data()
    active_locs = filter_active(locs)

    yearly = compute_yearly_means(daily, active_locs)
    pct_df = compute_all_percentiles(yearly, active_locs)

    if pct_df.empty:
        print("No counters met the minimum data requirements.")
        return

    pct_df = pct_df.sort_values("percentile_2025", ascending=False).reset_index(
        drop=True
    )

    pct_df.to_csv(OUTPUTS_DIR / "percentile-ranks.csv", index=False)

    yearly_means = build_yearly_means_csv(yearly, active_locs)
    yearly_means.to_csv(OUTPUTS_DIR / "yearly-means.csv", index=False)

    excluded = build_excluded_report(yearly, active_locs)
    excluded.to_csv(OUTPUTS_DIR / "excluded-counters.csv", index=False)

    plot_percentile_ranks(pct_df)
    plot_directional_breakdown(yearly, pct_df, active_locs)

    print("=" * 80)
    print("COUNTER PERCENTILE RANKS")
    print("=" * 80)
    for _, row in pct_df.iterrows():
        label = (
            f"{row['location_name']} ({row['direction']})"
            if row["direction"] != "Combined"
            else row["location_name"]
        )
        status = (
            "RECORD HIGH"
            if row["percentile_2025"] == 100
            else ("BELOW AVG" if row["percentile_2025"] < 50 else "ABOVE AVG")
        )
        print(
            f"  {label:60s}  rank={row['rank']:6s}  pctl={row['percentile_2025']:5.1f}%  {status}"
        )

    combined = pct_df[pct_df["direction"] == "Combined"].sort_values(
        "percentile_2025", ascending=False
    )

    print()
    print("=" * 80)
    print("COMBINED-DIRECTION SUMMARY")
    print("=" * 80)
    for _, row in combined.iterrows():
        status = (
            "RECORD HIGH"
            if row["percentile_2025"] == 100
            else ("BELOW AVG" if row["percentile_2025"] < 50 else "ABOVE AVG")
        )
        print(
            f"  {row['location_name']:50s}  rank={row['rank']:6s}  pctl={row['percentile_2025']:5.1f}%  {status}"
        )

    print()
    print("RECORD HIGHS (100th percentile):")
    record = combined[combined["percentile_2025"] == 100]
    if record.empty:
        print("  (none)")
    else:
        for _, row in record.iterrows():
            print(f"  {row['location_name']}")

    print()
    print("BELOW AVERAGE (<50th percentile):")
    below = combined[combined["percentile_2025"] < 50]
    if below.empty:
        print("  (none)")
    else:
        for _, row in below.iterrows():
            print(f"  {row['location_name']} (pctl={row['percentile_2025']}%)")

    print()
    print(f"Excluded counters ({len(excluded)}):")
    for _, row in excluded.iterrows():
        print(f"  {row['location_name']} ({row['direction']}): {row['reason']}")

    print()
    print(f"Outputs saved to {OUTPUTS_DIR}")
    print(f"  - percentile-ranks.csv ({len(pct_df)} rows)")
    print(f"  - yearly-means.csv ({len(yearly_means)} rows)")
    print(f"  - excluded-counters.csv ({len(excluded)} rows)")
    print("  - percentile-rank-chart.png")
    print("  - directional-breakdown.png")


if __name__ == "__main__":
    main()
