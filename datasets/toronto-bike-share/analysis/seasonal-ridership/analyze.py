"""Seasonal ridership analysis for Bike Share Toronto.

Produces a daily ridership plot (trips per day, one line per year)
and summary CSVs. See README.md for full description.
"""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

RAW = Path(__file__).resolve().parents[2] / "raw"
OUTPUTS = Path(__file__).resolve().parent / "outputs"
OUTPUTS.mkdir(exist_ok=True)

YEARS = list(range(2016, 2027))

START_TIME_NAMES = {
    "trip_start_time",
    "start_time",
    "start_station_time",
}


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    cols = {
        c: c.strip().lower().replace(" ", "_").replace("__", "_") for c in df.columns
    }
    df = df.rename(columns=cols)
    rename = {}
    for c in df.columns:
        if c == "trip_start_time":
            rename[c] = "start_time"
        elif c == "trip_stop_time":
            rename[c] = "end_time"
        elif c == "trip_id":
            rename[c] = "trip_id"
    return df.rename(columns=rename)


def load_trips(year: int) -> pd.DataFrame:
    path = RAW / f"bike-share-toronto-ridership-{year}.csv"
    if not path.exists():
        print(f"WARN: {path} not found; skipping {year}", file=sys.stderr)
        return pd.DataFrame()

    df = pd.read_csv(path, low_memory=False)
    df = normalize_columns(df)

    if "start_time" not in df.columns:
        candidates = [c for c in df.columns if c in START_TIME_NAMES]
        if not candidates:
            print(
                f"WARN: {year} has no time column (cols: {list(df.columns)[:6]}); skipping",
                file=sys.stderr,
            )
            return pd.DataFrame()
        df = df.rename(columns={candidates[0]: "start_time"})

    df["start_time"] = pd.to_datetime(df["start_time"], errors="coerce")
    df = df[df["start_time"].dt.year >= 2014]
    df = df.dropna(subset=["start_time"])
    df["year"] = df["start_time"].dt.year
    df["day_of_year"] = df["start_time"].dt.dayofyear
    df["date"] = df["start_time"].dt.date
    return df[["start_time", "year", "day_of_year", "date"]]


def daily_rides(frames: list[pd.DataFrame]) -> pd.DataFrame:
    combined = pd.concat([f for f in frames if not f.empty], ignore_index=True)
    daily = combined.groupby(["year", "date"]).size().reset_index(name="trips")
    daily["date"] = pd.to_datetime(daily["date"])
    daily["day_of_year"] = daily["date"].dt.dayofyear
    daily = daily.sort_values(["year", "date"])
    return daily


def plot_daily_rides(daily: pd.DataFrame) -> None:
    daily = daily.copy()
    daily = daily.sort_values(["year", "date"])
    daily["trips_ma7"] = daily.groupby("year")["trips"].transform(
        lambda s: s.rolling(7, min_periods=3, center=True).mean()
    )

    sns.set_theme(style="whitegrid", font_scale=1.1)
    years = sorted(daily["year"].unique())
    palette = sns.color_palette("viridis", n_colors=len(years))
    fig, ax = plt.subplots(figsize=(14, 6))
    for i, year in enumerate(years):
        grp = daily[daily["year"] == year]
        alpha = 0.9 if year >= 2024 else 0.45
        lw = 1.0 if year >= 2024 else 0.5
        ax.plot(
            grp["day_of_year"],
            grp["trips_ma7"],
            label=str(year),
            color=palette[i],
            linewidth=lw,
            alpha=alpha,
        )
    ax.set_xlabel("Month")
    ax.set_ylabel("Daily trips (7-day moving avg)")
    ax.set_title("Bike Share Toronto: Daily ridership by year (2016–2026)")
    month_ticks = [1, 32, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
    month_labels = [
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
    ax.set_xticks(month_ticks)
    ax.set_xticklabels(month_labels)
    ax.legend(
        title="Year",
        bbox_to_anchor=(1.02, 1),
        loc="upper left",
        fontsize="small",
        frameon=False,
    )
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"{x:,.0f}"))
    fig.tight_layout()
    path = OUTPUTS / "daily-rides-by-year.png"
    fig.savefig(path, dpi=150)
    print(f"Saved {path}")
    plt.close(fig)


def main() -> int:
    frames = []
    for year in YEARS:
        df = load_trips(year)
        if not df.empty:
            print(f"  {year}: {len(df):,} trips loaded", file=sys.stderr)
            frames.append(df)

    if not frames:
        print("No data found. Run `dvc pull` first.", file=sys.stderr)
        return 1

    daily = daily_rides(frames)
    daily.to_csv(OUTPUTS / "daily-rides.csv", index=False)
    print(f"Wrote {len(daily):,} rows to outputs/daily-rides.csv")

    yearly = daily.groupby("year")["trips"].sum().reset_index()
    yearly.columns = ["year", "total_trips"]
    yearly.to_csv(OUTPUTS / "yearly-totals.csv", index=False)
    print(f"Yearly totals:\n{yearly.to_string(index=False)}")

    plot_daily_rides(daily)
    return 0


if __name__ == "__main__":
    sys.exit(main())
