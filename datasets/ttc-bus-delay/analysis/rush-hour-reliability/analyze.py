from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

REPO_ROOT = Path(__file__).resolve().parent.parents[3]
DATA_PATH = (
    REPO_ROOT
    / "datasets"
    / "ttc-bus-delay"
    / "raw"
    / "ttc-bus-delay-data-since-2025.csv"
)
OUTPUT_DIR = Path(__file__).resolve().parent / "outputs"
OUTPUT_DIR.mkdir(exist_ok=True)

RUSH_HOURS_AM = range(7, 10)
RUSH_HOURS_PM = range(16, 19)
RUSH_HOURS = set(RUSH_HOURS_AM) | set(RUSH_HOURS_PM)
WEEKDAYS = {"Monday", "Tuesday", "Wednesday", "Thursday", "Friday"}
SIGNIFICANT_THRESHOLD = 5


def load_data():
    df = pd.read_csv(DATA_PATH)
    df["Date"] = pd.to_datetime(df["Date"])
    df = df[df["Date"].dt.year == 2025].copy()
    df["Line"] = df["Line"].fillna("Unknown")
    df["hour"] = df["Time"].str.split(":").str[0].astype(int)
    df["day_of_week"] = df["Day"]
    df["is_weekday"] = df["day_of_week"].isin(WEEKDAYS)
    df["is_rush_hour"] = df["hour"].isin(RUSH_HOURS) & df["is_weekday"]
    df["is_significant"] = df["Min Delay"] >= SIGNIFICANT_THRESHOLD
    n_unknown = (df["Line"] == "Unknown").sum()
    if n_unknown > 0:
        print(f"Note: {n_unknown} rows have NaN Line, grouped as 'Unknown'")
    return df


def build_hourly_summary(df):
    sig = df[df["is_significant"]]
    grouped = (
        sig.groupby(["day_of_week", "hour"])
        .agg(
            total_delays=pd.NamedAgg(column="Min Delay", aggfunc="size"),
            significant_delays=pd.NamedAgg(column="Min Delay", aggfunc="size"),
            mean_delay_min=pd.NamedAgg(column="Min Delay", aggfunc="mean"),
            median_delay_min=pd.NamedAgg(column="Min Delay", aggfunc="median"),
        )
        .reset_index()
    )
    all_grouped = (
        df.groupby(["day_of_week", "hour"])
        .agg(
            total_delays=pd.NamedAgg(column="Min Delay", aggfunc="size"),
        )
        .reset_index()
    )
    grouped["total_delays"] = all_grouped["total_delays"]
    return grouped


def plot_hourly_heatmap(df):
    sig = df[df["is_significant"]]
    pivot = sig.pivot_table(
        index="day_of_week", columns="hour", values="Min Delay", aggfunc="mean"
    )
    day_order = [
        "Monday",
        "Tuesday",
        "Wednesday",
        "Thursday",
        "Friday",
        "Saturday",
        "Sunday",
    ]
    day_order = [d for d in day_order if d in pivot.index]
    pivot = pivot.reindex(day_order)
    fig, ax = plt.subplots(figsize=(14, 5))
    sns.heatmap(pivot, cmap="YlOrRd", annot=True, fmt=".1f", linewidths=0.5, ax=ax)
    ax.set_title("TTC Bus 2025: Mean delay duration by hour and day")
    ax.set_xlabel("Hour of day")
    ax.set_ylabel("Day of week")
    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / "hourly-heatmap.png", dpi=150)
    plt.close(fig)


def bootstrap_ci(series, n_boot=10000, ci=95):
    rng = np.random.default_rng(42)
    boots = [
        series.sample(len(series), replace=True, random_state=rng).mean()
        for _ in range(n_boot)
    ]
    lower = np.percentile(boots, (100 - ci) / 2)
    upper = np.percentile(boots, 100 - (100 - ci) / 2)
    return lower, upper


def build_rush_comparison(df):
    results = []
    for period_label, mask in [
        ("rush", df["is_rush_hour"]),
        ("off-peak", ~df["is_rush_hour"]),
    ]:
        period_df = df.loc[mask]
        period_sig = period_df[period_df["is_significant"]]
        total_delays = len(period_df)
        significant_delays = len(period_sig)
        mean_delay = period_sig["Min Delay"].mean() if len(period_sig) > 0 else np.nan
        ci_lower, ci_upper = (np.nan, np.nan)
        if len(period_sig) >= 10:
            ci_lower, ci_upper = bootstrap_ci(period_sig["Min Delay"])
        total_delay_min = period_sig["Min Delay"].sum()
        results.append(
            {
                "period": period_label,
                "total_delays": total_delays,
                "significant_delays": significant_delays,
                "mean_delay_min": round(mean_delay, 2),
                "ci_lower": round(ci_lower, 2),
                "ci_upper": round(ci_upper, 2),
                "total_delay_min": int(total_delay_min),
            }
        )
    return pd.DataFrame(results)


def plot_rush_vs_offpeak(df, rush_comp):
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))

    periods = rush_comp["period"].values
    sig_counts = rush_comp["significant_delays"].values
    colors = ["#d62728", "#1f77b4"]

    ax1.bar(periods, sig_counts, color=colors)
    ax1.set_title("Significant delay count")
    ax1.set_ylabel("Count (≥5 min)")

    means = rush_comp["mean_delay_min"].values
    ci_lo = rush_comp["ci_lower"].values
    ci_hi = rush_comp["ci_upper"].values
    yerr = [means - ci_lo, ci_hi - means]

    ax2.errorbar(
        periods,
        means,
        yerr=yerr,
        fmt="o",
        markersize=8,
        capsize=5,
        color="black",
        ecolor="gray",
    )
    ax2.set_title("Mean delay duration (95% CI)")
    ax2.set_ylabel("Minutes")

    fig.suptitle(
        "TTC Bus 2025: Rush hour vs off-peak delays", fontsize=13, fontweight="bold"
    )
    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / "rush-vs-offpeak.png", dpi=150)
    plt.close(fig)


def build_route_comparison(df):
    sig = df[df["is_significant"]]
    rush_sig = sig[sig["is_rush_hour"]]
    offpeak_sig = sig[~sig["is_rush_hour"]]

    rush_stats = (
        rush_sig.groupby("Line")
        .agg(
            rush_delays=pd.NamedAgg(column="Min Delay", aggfunc="size"),
            rush_mean_delay=pd.NamedAgg(column="Min Delay", aggfunc="mean"),
            rush_total_min=pd.NamedAgg(column="Min Delay", aggfunc="sum"),
        )
        .reset_index()
    )

    offpeak_stats = (
        offpeak_sig.groupby("Line")
        .agg(
            offpeak_delays=pd.NamedAgg(column="Min Delay", aggfunc="size"),
            offpeak_mean_delay=pd.NamedAgg(column="Min Delay", aggfunc="mean"),
            offpeak_total_min=pd.NamedAgg(column="Min Delay", aggfunc="sum"),
        )
        .reset_index()
    )

    merged = rush_stats.merge(offpeak_stats, on="Line", how="left")
    merged["offpeak_delays"] = merged["offpeak_delays"].fillna(0).astype(int)
    merged["offpeak_mean_delay"] = merged["offpeak_mean_delay"].fillna(0)
    merged["offpeak_total_min"] = merged["offpeak_total_min"].fillna(0).astype(int)
    merged = merged.rename(columns={"Line": "route"})
    return merged.sort_values("rush_total_min", ascending=False)


def plot_top_rush_routes(route_comp):
    top15 = route_comp.head(15).copy()
    top15["rush_worse"] = top15["rush_mean_delay"] > top15["offpeak_mean_delay"]
    colors = top15["rush_worse"].map({True: "#d62728", False: "#1f77b4"})

    fig, ax = plt.subplots(figsize=(10, 7))
    y_pos = range(len(top15))
    ax.barh(y_pos, top15["rush_total_min"].values, color=colors.values)
    ax.set_yticks(list(y_pos))
    ax.set_yticklabels(top15["route"].values)
    ax.invert_yaxis()
    ax.set_xlabel("Total significant delay minutes (rush hour)")
    ax.set_title("TTC Bus 2025: Worst rush-hour routes")

    from matplotlib.patches import Patch

    legend_elements = [
        Patch(facecolor="#d62728", label="Rush mean > off-peak mean"),
        Patch(facecolor="#1f77b4", label="Off-peak mean ≥ rush mean"),
    ]
    ax.legend(handles=legend_elements, loc="lower right")

    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / "top-rush-routes.png", dpi=150)
    plt.close(fig)


def main():
    df = load_data()
    print(f"Loaded {len(df)} delay records for 2025")

    hourly_summary = build_hourly_summary(df)
    hourly_summary.to_csv(OUTPUT_DIR / "hourly-delay-summary.csv", index=False)
    print("Wrote hourly-delay-summary.csv")

    plot_hourly_heatmap(df)
    print("Wrote hourly-heatmap.png")

    rush_comp = build_rush_comparison(df)
    rush_comp.to_csv(OUTPUT_DIR / "rush-comparison.csv", index=False)
    print("Wrote rush-comparison.csv")

    plot_rush_vs_offpeak(df, rush_comp)
    print("Wrote rush-vs-offpeak.png")

    route_comp = build_route_comparison(df)
    route_comp.to_csv(OUTPUT_DIR / "route-rush-comparison.csv", index=False)
    print("Wrote route-rush-comparison.csv")

    plot_top_rush_routes(route_comp)
    print("Wrote top-rush-routes.png")

    print("\n=== SUMMARY ===")
    rush_row = rush_comp[rush_comp["period"] == "rush"].iloc[0]
    offpeak_row = rush_comp[rush_comp["period"] == "off-peak"].iloc[0]
    print(
        f"Rush hour: {int(rush_row['total_delays'])} total delays, "
        f"{int(rush_row['significant_delays'])} significant (≥5 min), "
        f"mean delay = {rush_row['mean_delay_min']:.2f} min "
        f"(95% CI: {rush_row['ci_lower']:.2f}–{rush_row['ci_upper']:.2f}), "
        f"total delay min = {int(rush_row['total_delay_min'])}"
    )
    print(
        f"Off-peak:  {int(offpeak_row['total_delays'])} total delays, "
        f"{int(offpeak_row['significant_delays'])} significant (≥5 min), "
        f"mean delay = {offpeak_row['mean_delay_min']:.2f} min "
        f"(95% CI: {offpeak_row['ci_lower']:.2f}–{offpeak_row['ci_upper']:.2f}), "
        f"total delay min = {int(offpeak_row['total_delay_min'])}"
    )

    top5 = route_comp.head(5)
    print("\nTop 5 rush-hour routes by total delay minutes:")
    for _, row in top5.iterrows():
        print(
            f"  {row['route']}: {int(row['rush_total_min'])} min "
            f"({int(row['rush_delays'])} delays, mean {row['rush_mean_delay']:.1f} min)"
        )

    overlap = (
        rush_row["ci_lower"] <= offpeak_row["mean_delay_min"] <= rush_row["ci_upper"]
    ) or (
        offpeak_row["ci_lower"] <= rush_row["mean_delay_min"] <= offpeak_row["ci_upper"]
    )
    if rush_row["mean_delay_min"] > offpeak_row["mean_delay_min"] and not overlap:
        print(
            "\nRush-hour delays are significantly worse than off-peak (CIs do not overlap)."
        )
    elif rush_row["mean_delay_min"] > offpeak_row["mean_delay_min"]:
        print(
            "\nRush-hour mean delay is higher, but CIs overlap — difference is not statistically clear."
        )
    else:
        print("\nRush-hour delays are NOT worse than off-peak by mean duration.")


if __name__ == "__main__":
    main()
