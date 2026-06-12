"""Ridership time series — one continuous axis, 2017–2026.

Plots daily trips (7-day moving average) on a single continuous date axis
for all years with reliable full-year data. Overlays 311 bike
infrastructure complaints for 2025 as secondary context.

Partial years (2016 Jul–Dec, 2026 Jan–Mar) and 2022 (missing January) are
excluded from the main plot but shown in the summary CSV.
"""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pandas as pd
import seaborn as sns

REPO_ROOT = Path(__file__).resolve().parent.parents[3]
RAW = REPO_ROOT / "datasets" / "toronto-bike-share" / "raw"
OUTPUTS = Path(__file__).resolve().parent / "outputs"
OUTPUTS.mkdir(exist_ok=True)

RELIABLE_YEARS = [2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025, 2026]
MA_WINDOW = 7


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    cols = {
        c: c.strip().lower().replace(" ", "_").replace("__", "_") for c in df.columns
    }
    df = df.rename(columns=cols)
    rename = {}
    for c in df.columns:
        if c == "trip_start_time":
            rename[c] = "start_time"
    return df.rename(columns=rename)


def load_year(year: int) -> pd.DataFrame:
    path = RAW / f"bike-share-toronto-ridership-{year}.csv"
    if not path.exists():
        print(f"WARN: {path} not found", file=sys.stderr)
        return pd.DataFrame()
    df = pd.read_csv(path, low_memory=False)
    df = normalize_columns(df)
    if "start_time" not in df.columns:
        print(f"WARN: {year} has no start_time column", file=sys.stderr)
        return pd.DataFrame()
    df["start_time"] = pd.to_datetime(df["start_time"], errors="coerce")
    df = df.dropna(subset=["start_time"])
    df["date"] = df["start_time"].dt.date
    return df[["date"]]


def main() -> int:
    frames = []
    for year in RELIABLE_YEARS:
        df = load_year(year)
        if df.empty:
            continue
        print(f"  {year}: {len(df):,} trips loaded", file=sys.stderr)
        frames.append(df)

    if not frames:
        print("No data. Run `dvc pull` first.", file=sys.stderr)
        return 1

    combined = pd.concat(frames, ignore_index=True)
    daily = combined.groupby("date").size().reset_index(name="trips")
    daily["date"] = pd.to_datetime(daily["date"])
    daily = daily.sort_values("date")
    daily["trips_ma"] = (
        daily["trips"].rolling(MA_WINDOW, min_periods=3, center=True).mean()
    )

    daily["year"] = daily["date"].dt.year

    yearly = daily.groupby("year")["trips"].sum().reset_index()
    yearly.columns = ["year", "total_trips"]
    yearly.to_csv(OUTPUTS / "summary.csv", index=False)
    print(f"\nYearly totals:\n{yearly.to_string(index=False)}")

    cum = (
        daily.groupby(["year", daily["date"].dt.dayofyear])["trips"]
        .sum()
        .groupby(level=0)
        .cumsum()
        .reset_index()
    )
    cum.columns = ["year", "day_of_year", "cum_trips"]
    cum.to_csv(OUTPUTS / "cumulative-by-year.csv", index=False)

    csv_311 = RAW / "311-bike-infrastructure-daily-2025.csv"
    if csv_311.exists():
        complaints = pd.read_csv(csv_311)
        complaints.columns = (
            complaints.columns.str.strip().str.lower().str.replace(" ", "_")
        )
        complaints["date"] = pd.to_datetime(complaints["date"])
        complaints = complaints[complaints["date"].dt.year == 2025]
        print(f"  311 complaints 2025: {len(complaints)} days loaded", file=sys.stderr)
    else:
        complaints = pd.DataFrame(columns=["date", "total_complaints"])
        print("WARN: 311 CSV not found", file=sys.stderr)

    partial_years = {2016, 2026}
    peak_dates = daily.loc[daily.groupby("year")["trips"].idxmax()][
        ["year", "date", "trips"]
    ]

    prev_totals = {int(row["year"]): row["total_trips"] for _, row in yearly.iterrows()}

    sns.set_theme(style="whitegrid", font_scale=1.1)
    fig, ax = plt.subplots(figsize=(16, 6))

    year_starts = yearly["year"].values
    band_colors = ["#f0f0f0", "#e8e8e8"]
    for i, yr in enumerate(year_starts):
        start = pd.Timestamp(f"{yr}-01-01")
        end = pd.Timestamp(f"{yr}-12-31")
        ax.axvspan(start, end, color=band_colors[i % 2], alpha=0.6, zorder=0)

    ax.fill_between(
        daily["date"], daily["trips"], alpha=0.15, color="#4c78a8", label="Daily trips"
    )
    ax.plot(
        daily["date"],
        daily["trips_ma"],
        color="#e45756",
        linewidth=1.2,
        label=f"{MA_WINDOW}-day moving avg",
    )

    y_top = daily["trips"].max() * 1.25
    ax.set_ylim(0, y_top)

    for _, row in peak_dates.iterrows():
        yr = int(row["year"])
        if yr in partial_years:
            continue
        total = yearly.loc[yearly["year"] == yr, "total_trips"].values[0]
        lines = [f"{total / 1e6:.1f}M"]
        if (yr - 1) in prev_totals:
            pct = (total - prev_totals[yr - 1]) / prev_totals[yr - 1] * 100
            lines.append(f"+{pct:.0f}% YoY")
        mid_year = pd.Timestamp(f"{yr}-07-02")
        peak_y = row["trips"]
        ax.annotate(
            "\n".join(lines),
            xy=(mid_year, peak_y),
            xytext=(0, 10),
            textcoords="offset points",
            ha="center",
            va="bottom",
            fontsize=8,
            color="#333333",
            fontfamily="sans-serif",
            fontweight="bold",
        )

    if not complaints.empty:
        ax3 = ax.twinx()
        ax3.bar(
            complaints["date"],
            complaints["total_complaints"],
            width=1.0,
            color="#ff9900",
            alpha=0.5,
            zorder=1,
            label="311 bike infra complaints",
        )
        ax3.set_ylabel("311 bike infrastructure complaints")
        ax3.set_ylim(bottom=0)
        ax3.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"{x:.0f}"))

        handles_311, labels_311 = ax3.get_legend_handles_labels()
    else:
        handles_311, labels_311 = [], []

    ax.set_xlabel("Date")
    ax.set_ylabel("Daily trips")
    ax.set_title("Bike Share Toronto: Daily ridership 2017–2026 (311 overlay 2025)")
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"{x:,.0f}"))
    ax.xaxis.set_major_locator(mdates.YearLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    ax.xaxis.set_minor_locator(mdates.MonthLocator())

    handles_main, labels_main = ax.get_legend_handles_labels()
    ax.legend(
        handles_main + handles_311,
        labels_main + labels_311,
        frameon=False,
        fontsize=10,
        loc="upper left",
    )

    fig.tight_layout()
    path = OUTPUTS / "ridership-time-series.png"
    fig.savefig(path, dpi=150)
    print(f"Saved {path}")
    plt.close(fig)
    return 0


if __name__ == "__main__":
    sys.exit(main())
