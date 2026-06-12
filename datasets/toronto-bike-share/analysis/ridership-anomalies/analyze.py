"""Ridership dip detection for Bike Share Toronto.

Identifies sustained periods of low ridership (dip events) where
daily rides drop sharply below the seasonal trend and stay low for
multiple days — patterns consistent with snow events, ice, or
infrastructure outages that take time to resolve.
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

YEARS = list(range(2017, 2027))

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
        elif c == "trip_stop_time":
            rename[c] = "end_time"
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
            print(f"WARN: {year} has no time column; skipping", file=sys.stderr)
            return pd.DataFrame()
        df = df.rename(columns={candidates[0]: "start_time"})
    df["start_time"] = pd.to_datetime(df["start_time"], errors="coerce")
    df = df[df["start_time"].dt.year >= 2014]
    df = df.dropna(subset=["start_time"])
    df["year"] = df["start_time"].dt.year
    df["date"] = df["start_time"].dt.date
    return df[["start_time", "year", "date"]]


def daily_rides(frames: list[pd.DataFrame]) -> pd.DataFrame:
    combined = pd.concat([f for f in frames if not f.empty], ignore_index=True)
    daily = combined.groupby(["year", "date"]).size().reset_index(name="trips")
    daily["date"] = pd.to_datetime(daily["date"])
    daily["day_of_year"] = daily["date"].dt.dayofyear
    daily = daily.sort_values(["year", "date"]).reset_index(drop=True)
    return daily


def find_dip_events(
    daily: pd.DataFrame, min_duration: int = 2, threshold_pct: float = 0.20
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Find sustained dip events: periods where actual rides are significantly
    below the 7-day moving average for at least min_duration consecutive days.

    A dip event starts when actual drops below (1 - threshold_pct) * expected
    and ends when it recovers above that line. This captures the "sharp drop,
    sustained low, recovery" pattern.
    """
    daily = daily.copy()
    daily = daily.sort_values(["year", "date"]).reset_index(drop=True)

    daily["baseline"] = daily.groupby("year")["trips"].transform(
        lambda s: s.rolling(7, min_periods=3, center=True).mean()
    )
    daily = daily.dropna(subset=["baseline"])
    daily["pct_below"] = (daily["baseline"] - daily["trips"]) / daily["baseline"]
    daily["is_below"] = daily["pct_below"] >= threshold_pct

    events = []
    for year, grp in daily.groupby("year"):
        below = grp["is_below"].values
        dates = grp["date"].values
        trips = grp["trips"].values
        baseline = grp["baseline"].values

        in_event = False
        event_start = None
        for i in range(len(below)):
            if below[i] and not in_event:
                in_event = True
                event_start = i
            elif not below[i] and in_event:
                in_event = False
                duration = i - event_start
                if duration >= min_duration:
                    max_drop_pct = max(
                        (baseline[j] - trips[j]) / baseline[j]
                        for j in range(event_start, i)
                    )
                    total_lost = sum(
                        baseline[j] - trips[j] for j in range(event_start, i)
                    )
                    events.append(
                        {
                            "year": year,
                            "start_date": pd.Timestamp(dates[event_start]).date(),
                            "end_date": pd.Timestamp(dates[i - 1]).date(),
                            "duration_days": duration,
                            "max_drop_pct": round(max_drop_pct, 3),
                            "total_lost_trips": int(total_lost),
                            "trips_at_start": int(trips[event_start]),
                            "trips_at_lowest": int(min(trips[event_start:i])),
                            "baseline_at_start": int(baseline[event_start]),
                        }
                    )
        if in_event:
            duration = len(below) - event_start
            if duration >= min_duration:
                max_drop_pct = max(
                    (baseline[j] - trips[j]) / baseline[j]
                    for j in range(event_start, len(below))
                )
                total_lost = sum(
                    baseline[j] - trips[j] for j in range(event_start, len(below))
                )
                events.append(
                    {
                        "year": year,
                        "start_date": pd.Timestamp(dates[event_start]).date(),
                        "end_date": pd.Timestamp(dates[-1]).date(),
                        "duration_days": duration,
                        "max_drop_pct": round(max_drop_pct, 3),
                        "total_lost_trips": int(total_lost),
                        "trips_at_start": int(trips[event_start]),
                        "trips_at_lowest": int(min(trips[event_start:])),
                        "baseline_at_start": int(baseline[event_start]),
                    }
                )

    return daily, pd.DataFrame(events).sort_values("total_lost_trips", ascending=False)


def plot_anomalies(daily: pd.DataFrame, events: pd.DataFrame) -> None:
    years = sorted(daily["year"].unique())
    ncols = 3
    nrows = (len(years) + ncols - 1) // ncols

    sns.set_theme(style="whitegrid", font_scale=0.9)
    fig, axes = plt.subplots(nrows, ncols, figsize=(16, 4 * nrows), sharey=False)

    for ax in axes.flat[len(years) :]:
        ax.set_visible(False)

    for i, year in enumerate(years):
        ax = axes.flat[i]
        yr_data = daily[daily["year"] == year].copy()

        ax.plot(
            yr_data["day_of_year"],
            yr_data["trips"],
            color="silver",
            linewidth=0.5,
            alpha=0.7,
        )
        ax.plot(
            yr_data["day_of_year"],
            yr_data["baseline"],
            color="steelblue",
            linewidth=1.5,
            alpha=0.9,
        )

        yr_events = (
            events[events["year"] == year]
            if events is not None and len(events) > 0
            else pd.DataFrame()
        )
        for _, evt in yr_events.iterrows():
            mask = (yr_data["date"].dt.date >= evt["start_date"]) & (
                yr_data["date"].dt.date <= evt["end_date"]
            )
            ax.fill_between(
                yr_data.loc[mask, "day_of_year"],
                yr_data.loc[mask, "trips"],
                yr_data.loc[mask, "baseline"],
                color="red",
                alpha=0.25,
                zorder=3,
            )
            ax.axvline(
                yr_data.loc[mask, "day_of_year"].iloc[0],
                color="red",
                linewidth=0.8,
                alpha=0.6,
                linestyle="--",
                zorder=4,
            )

        ax.set_title(
            f"{year} ({len(yr_events)} dips)" if len(yr_events) > 0 else str(year),
            fontsize=10,
            fontweight="bold",
        )
        ax.set_xlim(1, 366)
        ax.set_xlabel("")
        ax.set_ylabel("")

        month_ticks = [1, 32, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
        month_labels = ["J", "F", "M", "A", "M", "J", "J", "A", "S", "O", "N", "D"]
        ax.set_xticks(month_ticks)
        ax.set_xticklabels(month_labels, fontsize=7)

    fig.supxlabel("Month")
    fig.supylabel("Daily trips")
    fig.suptitle(
        "Bike Share Toronto: Sustained ridership dips (≥20% below 7-day trend, ≥2 days)",
        fontsize=12,
        fontweight="bold",
        y=1.01,
    )
    fig.tight_layout()

    path = OUTPUTS / "ridership-anomalies.png"
    fig.savefig(path, dpi=150, bbox_inches="tight")
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

    daily, events = find_dip_events(daily, min_duration=2, threshold_pct=0.20)

    events.to_csv(OUTPUTS / "dip-events.csv", index=False)
    print(f"Wrote {len(events)} dip events to outputs/dip-events.csv")
    print()
    print("Top 10 dip events by total lost trips:")
    for _, evt in events.head(10).iterrows():
        print(
            f"  {evt['year']} {evt['start_date']} → {evt['end_date']}: "
            f"{evt['duration_days']}d, {evt['max_drop_pct']:.0%} drop, "
            f"{evt['total_lost_trips']:,} lost trips"
        )

    daily[["date", "year", "trips"]].rename(columns={"trips": "actual_trips"}).to_csv(
        OUTPUTS / "daily-rides.csv", index=False
    )
    print(f"Wrote {len(daily):,} rows to outputs/daily-rides.csv")

    plot_anomalies(daily, events)
    return 0


if __name__ == "__main__":
    sys.exit(main())
