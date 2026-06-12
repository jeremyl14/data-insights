from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

REPO_ROOT = Path(__file__).resolve().parent.parents[3]
DATA_PATH = (
    REPO_ROOT
    / "datasets"
    / "ttc-subway-delay"
    / "raw"
    / "ttc-subway-delay-data-since-2025.csv"
)
OUTPUT_DIR = Path(__file__).resolve().parent / "outputs"
OUTPUT_DIR.mkdir(exist_ok=True)

RUSH_HOURS = list(range(7, 10)) + list(range(16, 19))
WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
SIGNIFICANT_THRESHOLD = 5
LINES = ["YU", "BD"]

DAY_ORDER = [
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday",
]


def load_data():
    df = pd.read_csv(DATA_PATH, parse_dates=["Date"])
    df = df[df["Date"].dt.year == 2025].copy()
    df["hour"] = pd.to_datetime(df["Time"], format="%H:%M", errors="coerce").dt.hour
    df = df.dropna(subset=["hour"])
    df["hour"] = df["hour"].astype(int)
    df["day_of_week"] = df["Day"]
    df["is_weekday"] = df["day_of_week"].isin(WEEKDAYS)
    df["is_rush"] = df["is_weekday"] & df["hour"].isin(RUSH_HOURS)
    df["period"] = np.where(df["is_rush"], "rush", "off-peak")
    df = df[df["Line"].isin(LINES)].copy()
    df["significant"] = df["Min Delay"] >= SIGNIFICANT_THRESHOLD
    return df


def build_hourly_summary(df):
    rows = []
    for line in LINES:
        sub = df[df["Line"] == line]
        for day in DAY_ORDER:
            for hour in range(24):
                grp = sub[(sub["day_of_week"] == day) & (sub["hour"] == hour)]
                if len(grp) == 0:
                    continue
                sig = grp[grp["significant"]]
                rows.append(
                    {
                        "line": line,
                        "day_of_week": day,
                        "hour": hour,
                        "total_delays": len(grp),
                        "significant_delays": len(sig),
                        "mean_delay_min": round(grp["Min Delay"].mean(), 2)
                        if len(grp) > 0
                        else 0,
                        "median_delay_min": round(grp["Min Delay"].median(), 2)
                        if len(grp) > 0
                        else 0,
                        "total_delay_min": int(grp["Min Delay"].sum()),
                    }
                )
    return pd.DataFrame(rows)


def build_rush_comparison(df):
    rows = []
    for line in LINES:
        for period in ["rush", "off-peak"]:
            grp = df[(df["Line"] == line) & (df["period"] == period)]
            sig = grp[grp["significant"]]
            mean_delays = sig["Min Delay"].values
            if len(mean_delays) > 1:
                boot_means = [
                    np.mean(
                        np.random.choice(
                            mean_delays, size=len(mean_delays), replace=True
                        )
                    )
                    for _ in range(1000)
                ]
                ci_lower = round(np.percentile(boot_means, 2.5), 2)
                ci_upper = round(np.percentile(boot_means, 97.5), 2)
            else:
                ci_lower = np.nan
                ci_upper = np.nan
            rows.append(
                {
                    "line": line,
                    "period": period,
                    "total_delays": len(grp),
                    "significant_delays": len(sig),
                    "mean_delay_min": round(sig["Min Delay"].mean(), 2)
                    if len(sig) > 0
                    else np.nan,
                    "ci_lower": ci_lower,
                    "ci_upper": ci_upper,
                    "total_delay_min": int(sig["Min Delay"].sum())
                    if len(sig) > 0
                    else 0,
                }
            )
    return pd.DataFrame(rows)


def plot_heatmap(df):
    sig = df[df["significant"]].copy()
    fig, axes = plt.subplots(1, 2, figsize=(16, 6), sharey=True)
    for idx, line in enumerate(LINES):
        sub = sig[sig["Line"] == line]
        pivot = sub.groupby(["day_of_week", "hour"])["Min Delay"].mean().reset_index()
        pivot.columns = ["day_of_week", "hour", "mean_delay"]
        heatmap_data = pivot.pivot(
            index="day_of_week", columns="hour", values="mean_delay"
        )
        heatmap_data = heatmap_data.reindex(index=DAY_ORDER)
        heatmap_data = heatmap_data.reindex(columns=range(24))
        sns.heatmap(
            heatmap_data,
            ax=axes[idx],
            cmap="YlOrRd",
            annot=True,
            fmt=".1f",
            linewidths=0.5,
            cbar_kws={"label": "Mean delay (min)"},
        )
        axes[idx].set_title(f"Line {1 if line == 'YU' else 2} ({line})")
        axes[idx].set_xlabel("Hour of day")
        axes[idx].set_ylabel("Day of week" if idx == 0 else "")
    fig.suptitle(
        "TTC Subway 2025: Mean delay duration by hour and day", fontsize=14, y=1.02
    )
    plt.tight_layout()
    fig.savefig(OUTPUT_DIR / "delay-heatmap.png", dpi=150, bbox_inches="tight")
    plt.close(fig)


def plot_rush_vs_offpeak(rush_df):
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6), sharey=False)
    width = 0.35
    x = np.arange(len(LINES))

    rush_sig = [
        rush_df[(rush_df["line"] == ln) & (rush_df["period"] == "rush")][
            "significant_delays"
        ].values[0]
        for ln in LINES
    ]
    offpeak_sig = [
        rush_df[(rush_df["line"] == ln) & (rush_df["period"] == "off-peak")][
            "significant_delays"
        ].values[0]
        for ln in LINES
    ]
    rush_mean = [
        rush_df[(rush_df["line"] == ln) & (rush_df["period"] == "rush")][
            "mean_delay_min"
        ].values[0]
        for ln in LINES
    ]
    offpeak_mean = [
        rush_df[(rush_df["line"] == ln) & (rush_df["period"] == "off-peak")][
            "mean_delay_min"
        ].values[0]
        for ln in LINES
    ]
    rush_ci_lo = [
        rush_df[(rush_df["line"] == ln) & (rush_df["period"] == "rush")][
            "ci_lower"
        ].values[0]
        for ln in LINES
    ]
    rush_ci_hi = [
        rush_df[(rush_df["line"] == ln) & (rush_df["period"] == "rush")][
            "ci_upper"
        ].values[0]
        for ln in LINES
    ]
    offpeak_ci_lo = [
        rush_df[(rush_df["line"] == ln) & (rush_df["period"] == "off-peak")][
            "ci_lower"
        ].values[0]
        for ln in LINES
    ]
    offpeak_ci_hi = [
        rush_df[(rush_df["line"] == ln) & (rush_df["period"] == "off-peak")][
            "ci_upper"
        ].values[0]
        for ln in LINES
    ]

    labels = [f"Line 1 ({ln})" if ln == "YU" else f"Line 2 ({ln})" for ln in LINES]

    ax1.bar(x - width / 2, rush_sig, width, label="Rush", color="#d95f02", alpha=0.8)
    ax1.bar(
        x + width / 2, offpeak_sig, width, label="Off-peak", color="#1b9e77", alpha=0.8
    )
    ax1.set_xticks(x)
    ax1.set_xticklabels(labels)
    ax1.set_ylabel("Significant delay count")
    ax1.set_title("Count of significant delays")
    ax1.legend()

    rush_err = [
        [rush_mean[i] - rush_ci_lo[i], rush_ci_hi[i] - rush_mean[i]]
        for i in range(len(LINES))
    ]
    offpeak_err = [
        [offpeak_mean[i] - offpeak_ci_lo[i], offpeak_ci_hi[i] - offpeak_mean[i]]
        for i in range(len(LINES))
    ]

    ax2.errorbar(
        x - width / 2,
        rush_mean,
        yerr=np.array(rush_err).T,
        fmt="o",
        color="#d95f02",
        markersize=8,
        capsize=5,
        label="Rush",
    )
    ax2.errorbar(
        x + width / 2,
        offpeak_mean,
        yerr=np.array(offpeak_err).T,
        fmt="s",
        color="#1b9e77",
        markersize=8,
        capsize=5,
        label="Off-peak",
    )
    ax2.set_xticks(x)
    ax2.set_xticklabels(labels)
    ax2.set_ylabel("Mean delay duration (min)")
    ax2.set_title("Mean delay duration (95% CI)")
    ax2.legend()

    fig.suptitle("TTC Subway 2025: Rush hour vs off-peak delays by line", fontsize=13)
    plt.tight_layout()
    fig.savefig(OUTPUT_DIR / "rush-vs-offpeak.png", dpi=150, bbox_inches="tight")
    plt.close(fig)


def plot_monthly_delay_rate(df):
    df_copy = df.copy()
    df_copy["month"] = df_copy["Date"].dt.month

    fig, ax = plt.subplots(figsize=(10, 6))
    colors = {"rush": "#d95f02", "off-peak": "#1b9e77"}
    markers = {"YU": "o", "BD": "s"}

    for line in LINES:
        for period in ["rush", "off-peak"]:
            sub = df_copy[(df_copy["Line"] == line) & (df_copy["period"] == period)]
            monthly = (
                sub.groupby("month")
                .agg(
                    total=("significant", "count"),
                    sig=("significant", "sum"),
                )
                .reset_index()
            )
            monthly["rate"] = monthly["sig"] / monthly["total"]
            label = f"{'Line 1' if line == 'YU' else 'Line 2'} ({line}) - {period}"
            ax.plot(
                monthly["month"],
                monthly["rate"],
                marker=markers[line],
                color=colors[period],
                label=label,
                linewidth=2,
                markersize=6,
            )

    ax.set_xlabel("Month (2025)")
    ax.set_ylabel("Significant delay rate")
    ax.set_ylim(0, 1)
    ax.set_xticks(range(1, 13))
    ax.set_xticklabels(
        [
            "Jan",
            "Feb",
            "Mar",
            "Apr",
            "May",
            "Jun",
            "Jul",
            "Aug",
            "Sep",
            "Oct",
            "Nov",
            "Dec",
        ]
    )
    ax.legend(fontsize=9)
    ax.set_title(
        "TTC Subway 2025: Significant delay rate by period and line", fontsize=13
    )
    plt.tight_layout()
    fig.savefig(OUTPUT_DIR / "monthly-delay-rate.png", dpi=150, bbox_inches="tight")
    plt.close(fig)


def main():
    np.random.seed(42)
    print("Loading data...")
    df = load_data()
    print(f"Loaded {len(df)} delay records for YU/BD in 2025")

    print("Building hourly summary...")
    hourly = build_hourly_summary(df)
    hourly.to_csv(OUTPUT_DIR / "hourly-delay-summary.csv", index=False)
    print(f"Hourly summary: {len(hourly)} rows written")

    print("Building rush comparison...")
    rush = build_rush_comparison(df)
    rush.to_csv(OUTPUT_DIR / "rush-comparison.csv", index=False)
    print("Rush comparison written")

    print("Plotting heatmap...")
    plot_heatmap(df)

    print("Plotting rush vs off-peak...")
    plot_rush_vs_offpeak(rush)

    print("Plotting monthly delay rate...")
    plot_monthly_delay_rate(df)

    print("\n=== RESULTS ===")
    for _, row in rush.iterrows():
        print(
            f"{row['line']} {row['period']}: "
            f"{row['significant_delays']} significant delays, "
            f"mean delay = {row['mean_delay_min']} min "
            f"(95% CI [{row['ci_lower']}, {row['ci_upper']}]), "
            f"total delay = {row['total_delay_min']} min"
        )

    worse_line = (
        rush[rush["period"] == "rush"]
        .sort_values("mean_delay_min", ascending=False)
        .iloc[0]["line"]
    )
    print(f"\nWorse rush-hour line: {worse_line}")

    print(
        "\nNote: Monthly delay rates are noisy. See monthly-delay-rate.png for the full trend."
    )

    print("\nDone.")


if __name__ == "__main__":
    main()
