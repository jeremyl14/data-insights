"""Ridership + 311 bike infrastructure complaints + snowfall, 2025-2026.

Plots daily bike-share trips (area + moving average) with 311 bike
infrastructure complaint bars and snowfall on secondary axes, covering
full-year 2025 and partial 2026.
"""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pandas as pd
import seaborn as sns

REPO_ROOT = Path(__file__).resolve().parent.parents[3]
RAW_BIKE = REPO_ROOT / "datasets" / "toronto-bike-share" / "raw"
RAW_WEATHER = REPO_ROOT / "datasets" / "toronto-weather-daily" / "raw"
OUTPUTS = Path(__file__).resolve().parent / "outputs"
OUTPUTS.mkdir(exist_ok=True)

MA_WINDOW = 7
YEARS = [2025, 2026]

START_TIME_NAMES = {"trip_start_time", "start_time", "start_station_time"}


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


def load_ridership() -> pd.DataFrame:
    frames = []
    for year in YEARS:
        path = RAW_BIKE / f"bike-share-toronto-ridership-{year}.csv"
        if not path.exists():
            continue
        df = pd.read_csv(path, low_memory=False)
        df = normalize_columns(df)
        if "start_time" not in df.columns:
            candidates = [c for c in df.columns if c in START_TIME_NAMES]
            if not candidates:
                continue
            df = df.rename(columns={candidates[0]: "start_time"})
        df["start_time"] = pd.to_datetime(df["start_time"], errors="coerce")
        df = df.dropna(subset=["start_time"])
        df["date"] = df["start_time"].dt.date
        daily = df.groupby("date").size().reset_index(name="trips")
        daily["date"] = pd.to_datetime(daily["date"])
        frames.append(daily)
        print(f"  {year}: {len(df):,} trips", file=sys.stderr)
    return (
        pd.concat(frames, ignore_index=True).sort_values("date").reset_index(drop=True)
    )


def load_311() -> pd.DataFrame:
    frames = []
    for year in YEARS:
        path = RAW_BIKE / f"311-bike-infrastructure-daily-{year}.csv"
        if not path.exists():
            continue
        df = pd.read_csv(path)
        df.columns = df.columns.str.strip().str.lower().str.replace(" ", "_")
        df["date"] = pd.to_datetime(df["date"])
        frames.append(df[["date", "total_complaints", "winter_maintenance"]].copy())
        print(
            f"  311 {year}: {len(df)} days, {df['total_complaints'].sum():,} complaints",
            file=sys.stderr,
        )
    if not frames:
        return pd.DataFrame(columns=["date", "total_complaints", "winter_maintenance"])
    return (
        pd.concat(frames, ignore_index=True).sort_values("date").reset_index(drop=True)
    )


def load_weather() -> pd.DataFrame:
    frames = []
    for year in YEARS:
        path = RAW_WEATHER / f"toronto-pearson-daily-{year}.csv"
        if not path.exists():
            continue
        df = pd.read_csv(path)
        df.columns = [c.strip() for c in df.columns]
        df = df.rename(
            columns={
                "Date/Time": "date",
                "Total Snow (cm)": "total_snow_cm",
                "Snow on Grnd (cm)": "snow_on_grnd_cm",
                "Mean Temp (°C)": "mean_temp_c",
            }
        )
        df["date"] = pd.to_datetime(df["date"])
        df["total_snow_cm"] = pd.to_numeric(
            df["total_snow_cm"].astype(str).str.replace("T", "0.0"), errors="coerce"
        ).fillna(0.0)
        df["snow_on_grnd_cm"] = pd.to_numeric(
            df["snow_on_grnd_cm"].astype(str).str.replace("T", "0.0"), errors="coerce"
        ).fillna(0.0)
        df["mean_temp_c"] = pd.to_numeric(df["mean_temp_c"], errors="coerce")
        frames.append(
            df[["date", "total_snow_cm", "snow_on_grnd_cm", "mean_temp_c"]].copy()
        )
    if not frames:
        return pd.DataFrame(
            columns=["date", "total_snow_cm", "snow_on_grnd_cm", "mean_temp_c"]
        )
    return (
        pd.concat(frames, ignore_index=True).sort_values("date").reset_index(drop=True)
    )


def main() -> int:
    print("Loading ridership...", file=sys.stderr)
    daily = load_ridership()
    print("Loading 311...", file=sys.stderr)
    complaints = load_311()
    print("Loading weather...", file=sys.stderr)
    weather = load_weather()

    daily["trips_ma"] = (
        daily["trips"].rolling(MA_WINDOW, min_periods=3, center=True).mean()
    )
    daily["year"] = daily["date"].dt.year

    merged = daily.merge(complaints, on="date", how="left")
    merged["total_complaints"] = merged["total_complaints"].fillna(0).astype(int)
    merged["winter_maintenance"] = merged["winter_maintenance"].fillna(0).astype(int)
    merged = merged.merge(weather, on="date", how="left")
    merged["total_snow_cm"] = merged["total_snow_cm"].fillna(0.0)
    merged["mean_temp_c"] = merged["mean_temp_c"].ffill()
    merged["temp_ma7"] = (
        merged["mean_temp_c"].rolling(7, min_periods=3, center=True).mean()
    )

    yearly = daily.groupby("year")["trips"].sum().reset_index()
    yearly.columns = ["year", "total_trips"]

    yearly_311 = (
        complaints.groupby(complaints["date"].dt.year)["total_complaints"]
        .sum()
        .reset_index()
    )
    yearly_311.columns = ["year", "total_complaints"]
    summary = yearly.merge(yearly_311, on="year", how="left")
    summary.to_csv(OUTPUTS / "summary.csv", index=False)
    print(f"\nSummary:\n{summary.to_string(index=False)}")

    merged.to_csv(OUTPUTS / "311-daily-comparison.csv", index=False)

    sns.set_theme(style="whitegrid", font_scale=1.1)
    fig, ax1 = plt.subplots(figsize=(16, 7))

    years = sorted(daily["year"].unique())
    for i, yr in enumerate(years):
        yr_data = merged[merged["year"] == yr]
        start = pd.Timestamp(f"{yr}-01-01")
        end = yr_data["date"].max() + pd.Timedelta(days=1)
        band_color = "#f5f5f5" if i % 2 == 0 else "#ececec"
        ax1.axvspan(start, end, color=band_color, alpha=0.8, zorder=0)

    ax1.fill_between(
        merged["date"],
        merged["trips"],
        alpha=0.15,
        color="#4c78a8",
        label="Daily trips",
    )
    ax1.plot(
        merged["date"],
        merged["trips_ma"],
        color="#e45756",
        linewidth=1.2,
        label=f"{MA_WINDOW}-day moving avg",
    )

    ax2 = ax1.twinx()
    ax2.bar(
        merged["date"],
        merged["total_complaints"],
        width=1.0,
        color="#ff9900",
        alpha=0.5,
        zorder=1,
        label="311 bike infra complaints",
    )
    ax2.set_ylabel("311 bike infrastructure complaints", color="#ff9900")
    ax2.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"{x:.0f}"))
    ax2.tick_params(axis="y", labelcolor="#ff9900")

    ax3 = ax1.twinx()
    ax3.spines["right"].set_position(("outward", 60))
    snowy = merged[merged["total_snow_cm"] >= 0.5]
    if len(snowy) > 0:
        ax3.bar(
            snowy["date"],
            snowy["total_snow_cm"],
            width=1.0,
            color="#9e9ac8",
            alpha=0.7,
            zorder=1,
            label="Snowfall (cm)",
        )
    ax3.set_ylabel("Snowfall (cm)", color="#9e9ac8")
    ax3.tick_params(axis="y", labelcolor="#9e9ac8")

    ax1.set_xlim(
        pd.Timestamp("2025-01-01"), merged["date"].max() + pd.Timedelta(days=3)
    )
    ax1.set_ylabel("Daily trips")
    ax1.set_title(
        "Bike Share Toronto: Ridership, temperature, snowfall & 311 bike complaints (2025–2026)\n"
        "CAUTION: four y-axes — do not compare axis scales visually",
        fontsize=13,
    )
    ax1.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"{x:,.0f}"))
    ax1.xaxis.set_major_locator(mdates.MonthLocator())
    ax1.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))

    ax1.set_ylim(0, 50000)
    ax1.yaxis.set_major_locator(plt.MultipleLocator(10000))

    ax2.set_ylim(0, 120)
    ax2.yaxis.set_major_locator(plt.MultipleLocator(24))
    ax2.grid(False)

    ax3.set_ylim(80, 0)
    ax3.yaxis.set_major_locator(plt.MultipleLocator(16))
    ax3.grid(False)

    ax_temp = ax1.twinx()
    ax_temp.spines["right"].set_position(("outward", 120))
    ax_temp.plot(
        merged["date"],
        merged["temp_ma7"],
        color="#2ca02c",
        linewidth=1.0,
        linestyle="--",
        zorder=5,
        label="7-day avg temp (°C)",
    )
    ax_temp.set_ylabel("Mean temp (°C)", color="#2ca02c")
    ax_temp.tick_params(axis="y", labelcolor="#2ca02c")
    ax_temp.set_ylim(-20, 30)
    ax_temp.yaxis.set_major_locator(plt.MultipleLocator(10))
    ax_temp.grid(False)

    handles_1, labels_1 = ax1.get_legend_handles_labels()
    handles_t, labels_t = ax_temp.get_legend_handles_labels()
    handles_2, labels_2 = ax2.get_legend_handles_labels()
    handles_3, labels_3 = ax3.get_legend_handles_labels()
    ax1.legend(
        handles_1 + handles_t + handles_2 + handles_3,
        labels_1 + labels_t + labels_2 + labels_3,
        frameon=False,
        fontsize=10,
        loc="upper left",
        bbox_to_anchor=(0.0, 0.85),
    )

    fig.tight_layout()
    path = OUTPUTS / "ridership-311-2025-2026.png"
    fig.savefig(path, dpi=150)
    print(f"Saved {path}")
    plt.close(fig)
    return 0


if __name__ == "__main__":
    sys.exit(main())
