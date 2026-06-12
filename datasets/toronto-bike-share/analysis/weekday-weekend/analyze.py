"""
Bike Share Toronto: Weekday vs weekend daily ridership over time.

Computes monthly ride counts split by weekday/weekend, produces a smoothed
line plot and summary CSVs.
"""

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

RAW_DIR = Path(__file__).resolve().parent.parent.parent / "raw"
OUT_DIR = Path(__file__).resolve().parent / "outputs"
YEARS = range(2016, 2027)

DATETIME_ALIASES = ["trip_start_time", "start_time"]


def normalize_columns(cols: pd.Index) -> pd.Index:
    return cols.str.strip().str.lower().str.replace(" ", "_", regex=False)


def load_year(year: int) -> pd.DataFrame:
    path = RAW_DIR / f"bike-share-toronto-ridership-{year}.csv"
    if not path.exists():
        print(f"  skipping {year}: file not found")
        return pd.DataFrame()

    df = pd.read_csv(path, encoding="utf-8-sig", low_memory=False)
    df.columns = normalize_columns(df.columns)

    dt_col = None
    for alias in DATETIME_ALIASES:
        if alias in df.columns:
            dt_col = alias
            break

    if dt_col is None:
        print(f"  skipping {year}: no datetime column found ({list(df.columns)})")
        return pd.DataFrame()

    df["trip_date"] = pd.to_datetime(df[dt_col], errors="coerce")
    df = df.dropna(subset=["trip_date"])
    df = df[df["trip_date"].dt.year == year]
    df["year"] = df["trip_date"].dt.year
    df["month"] = df["trip_date"].dt.month
    df["is_weekend"] = df["trip_date"].dt.dayofweek >= 5
    df["date"] = df["trip_date"].dt.date

    return df[["year", "month", "is_weekend", "date"]].copy()


def compute_monthly(frames: list[pd.DataFrame]) -> pd.DataFrame:
    df = pd.concat(frames, ignore_index=True)
    grouped = (
        df.groupby(["year", "month", "is_weekend"])
        .size()
        .reset_index(name="total_trips")
    )

    days_in_month = (
        df.drop_duplicates(subset=["year", "month", "is_weekend", "date"])
        .groupby(["year", "month", "is_weekend"])
        .size()
        .reset_index(name="days")
    )

    merged = grouped.merge(days_in_month, on=["year", "month", "is_weekend"])
    merged["avg_daily_trips"] = (merged["total_trips"] / merged["days"]).round(1)

    return merged[["year", "month", "is_weekend", "avg_daily_trips", "total_trips"]]


def compute_yearly(frames: list[pd.DataFrame]) -> pd.DataFrame:
    df = pd.concat(frames, ignore_index=True)
    grouped = df.groupby(["year", "is_weekend"]).size().reset_index(name="total_trips")
    days_in_year = (
        df.drop_duplicates(subset=["year", "is_weekend", "date"])
        .groupby(["year", "is_weekend"])
        .size()
        .reset_index(name="days")
    )
    merged = grouped.merge(days_in_year, on=["year", "is_weekend"])
    merged["avg_daily_trips"] = (merged["total_trips"] / merged["days"]).round(1)
    return merged[["year", "is_weekend", "avg_daily_trips", "total_trips"]]


def make_plot(monthly: pd.DataFrame) -> None:
    sns.set_theme(style="whitegrid")

    monthly["period"] = pd.to_datetime(
        monthly["year"].astype(str) + "-" + monthly["month"].astype(str) + "-01"
    )

    fig, ax = plt.subplots(figsize=(14, 6))

    for is_weekend, label, color in [
        (False, "Weekday", "#4C72B0"),
        (True, "Weekend", "#DD8452"),
    ]:
        subset = monthly[monthly["is_weekend"] == is_weekend].sort_values("period")
        smoothed = (
            subset["avg_daily_trips"]
            .rolling(window=3, center=True, min_periods=1)
            .mean()
        )
        ax.plot(subset["period"], smoothed, label=label, color=color, linewidth=2)

    ax.set_title(
        "Bike Share Toronto: Weekday vs weekend daily ridership",
        fontsize=14,
        fontweight="bold",
    )
    ax.set_xlabel("Month")
    ax.set_ylabel("Avg daily trips")
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"{x:,.0f}"))
    ax.legend(fontsize=11)
    fig.autofmt_xdate()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT_DIR / "weekday-weekend-monthly.png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    print("  saved weekday-weekend-monthly.png")


def main() -> None:
    print("Loading data...")
    frames = []
    for year in YEARS:
        print(f"  {year}...")
        df = load_year(year)
        if not df.empty:
            frames.append(df)

    print("Computing monthly aggregates...")
    monthly = compute_monthly(frames)
    yearly = compute_yearly(frames)

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    monthly.to_csv(OUT_DIR / "weekday-weekend-monthly.csv", index=False)
    print("  saved weekday-weekend-monthly.csv")

    yearly.to_csv(OUT_DIR / "weekday-weekend-yearly.csv", index=False)
    print("  saved weekday-weekend-yearly.csv")

    print("Generating figure...")
    make_plot(monthly)

    print("Done.")


if __name__ == "__main__":
    main()
