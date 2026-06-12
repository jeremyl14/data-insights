"""Snow clearing event study: how snowfall events suppress cycling volume,
with 311 complaints as a proxy for snow clearing speed.

Event study around major snowfall events in 2025, measuring ridership
deficit and 311 complaint timing in the ±2-week window around each storm.
"""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
import pandas as pd
import seaborn as sns

REPO_ROOT = Path(__file__).resolve().parent.parents[3]
WEATHER_DIR = REPO_ROOT / "datasets" / "toronto-weather-daily" / "raw"
BIKE_DIR = REPO_ROOT / "datasets" / "toronto-bike-share" / "raw"
YEARS = [2025, 2026]

SCRIPT_DIR = Path(__file__).resolve().parent
OUTPUTS = SCRIPT_DIR / "outputs"
OUTPUTS.mkdir(exist_ok=True)

SNOW_THRESHOLD = 2.0
GAP_DAYS = 2
WINDOW_PRE = 3
WINDOW_POST = 14
BASELINE_DAYS = 7
TOP_N_EVENTS = 5

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


def load_weather() -> pd.DataFrame:
    frames = []
    for year in YEARS:
        path = WEATHER_DIR / f"toronto-pearson-daily-{year}.csv"
        if not path.exists():
            print(f"WARN: {path} not found, skipping", file=sys.stderr)
            continue
        df = pd.read_csv(path)
        df.columns = [c.strip() for c in df.columns]
        df = df.rename(
            columns={
                "Date/Time": "date",
                "Max Temp (\u00b0C)": "max_temp_c",
                "Min Temp (\u00b0C)": "min_temp_c",
                "Mean Temp (\u00b0C)": "temp_mean_c",
                "Total Rain (mm)": "total_rain_mm",
                "Total Snow (cm)": "total_snow_cm",
                "Total Precip (mm)": "total_precip_mm",
                "Snow on Grnd (cm)": "snow_on_grnd_cm",
            }
        )
        df["date"] = pd.to_datetime(df["date"])
        for col in [
            "total_snow_cm",
            "snow_on_grnd_cm",
            "total_rain_mm",
            "total_precip_mm",
            "max_temp_c",
            "min_temp_c",
            "temp_mean_c",
        ]:
            if col in df.columns:
                df[col] = pd.to_numeric(
                    df[col].astype(str).str.replace("T", "0.0"), errors="coerce"
                )
                df[col] = df[col].fillna(0.0)
        keep = [
            c
            for c in [
                "date",
                "max_temp_c",
                "min_temp_c",
                "temp_mean_c",
                "total_rain_mm",
                "total_snow_cm",
                "total_precip_mm",
                "snow_on_grnd_cm",
            ]
            if c in df.columns
        ]
        frames.append(df[keep].copy())
    return (
        pd.concat(frames, ignore_index=True).sort_values("date").reset_index(drop=True)
    )


def load_ridership() -> pd.DataFrame:
    frames = []
    for year in YEARS:
        path = BIKE_DIR / f"bike-share-toronto-ridership-{year}.csv"
        if not path.exists():
            print(f"WARN: {path} not found, skipping", file=sys.stderr)
            continue
        df = pd.read_csv(path, low_memory=False)
        df = normalize_columns(df)
        if "start_time" not in df.columns:
            candidates = [c for c in df.columns if c in START_TIME_NAMES]
            if not candidates:
                print(f"WARN: {year} has no time column, skipping", file=sys.stderr)
                continue
            df = df.rename(columns={candidates[0]: "start_time"})
        df["start_time"] = pd.to_datetime(df["start_time"], errors="coerce")
        df = df.dropna(subset=["start_time"])
        df["date"] = df["start_time"].dt.date
        daily = df.groupby("date").size().reset_index(name="ridership")
        daily["date"] = pd.to_datetime(daily["date"])
        frames.append(daily)
    return (
        pd.concat(frames, ignore_index=True).sort_values("date").reset_index(drop=True)
    )


def load_311() -> pd.DataFrame:
    frames = []
    for year in YEARS:
        path = BIKE_DIR / f"311-bike-infrastructure-daily-{year}.csv"
        if not path.exists():
            print(f"WARN: {path} not found, skipping", file=sys.stderr)
            continue
        df = pd.read_csv(path)
        df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]
        df["date"] = pd.to_datetime(df["date"])
        frames.append(df[["date", "total_complaints"]].copy())
    return (
        pd.concat(frames, ignore_index=True).sort_values("date").reset_index(drop=True)
    )


def find_snow_events(weather: pd.DataFrame) -> pd.DataFrame:
    snowy = weather[weather["total_snow_cm"] >= SNOW_THRESHOLD].copy()
    if snowy.empty:
        return pd.DataFrame(
            columns=[
                "event_id",
                "start_date",
                "end_date",
                "total_snow_cm",
                "peak_snow_cm",
                "duration_days",
            ]
        )
    events = []
    current_dates = [snowy["date"].iloc[0]]
    for i in range(1, len(snowy)):
        gap = (snowy["date"].iloc[i] - snowy["date"].iloc[i - 1]).days
        if gap <= GAP_DAYS + 1:
            current_dates.append(snowy["date"].iloc[i])
        else:
            events.append(current_dates)
            current_dates = [snowy["date"].iloc[i]]
    events.append(current_dates)

    rows = []
    for idx, dates in enumerate(events):
        sub = weather[weather["date"].isin(dates)]
        rows.append(
            {
                "event_id": idx + 1,
                "start_date": min(dates),
                "end_date": max(dates),
                "total_snow_cm": sub["total_snow_cm"].sum(),
                "peak_snow_cm": sub["total_snow_cm"].max(),
                "duration_days": len(dates),
            }
        )
    return pd.DataFrame(rows)


def build_event_details(merged: pd.DataFrame, events: pd.DataFrame) -> pd.DataFrame:
    all_rows = []
    for _, ev in events.iterrows():
        start = ev["start_date"]
        baseline_dates = pd.date_range(
            end=start - pd.Timedelta(days=1), periods=BASELINE_DAYS, freq="D"
        )
        baseline = merged[merged["date"].isin(baseline_dates)]
        expected = baseline["ridership"].mean()
        if pd.isna(expected) or expected == 0:
            expected = baseline["ridership"].median()

        window_dates = pd.date_range(
            start - pd.Timedelta(days=WINDOW_PRE),
            start + pd.Timedelta(days=WINDOW_POST),
            freq="D",
        )
        for d in window_dates:
            rel = (d - start).days
            row_data = merged[merged["date"] == d]
            if row_data.empty:
                all_rows.append(
                    {
                        "event_id": ev["event_id"],
                        "relative_day": rel,
                        "date": d,
                        "ridership": np.nan,
                        "expected_ridership": expected,
                        "deficit_pct": np.nan,
                        "complaints": np.nan,
                        "snow_cm": np.nan,
                        "snow_on_grnd_cm": np.nan,
                    }
                )
                continue
            row = row_data.iloc[0]
            actual = row["ridership"]
            deficit = ((actual - expected) / expected * 100) if expected > 0 else np.nan
            all_rows.append(
                {
                    "event_id": ev["event_id"],
                    "relative_day": rel,
                    "date": d,
                    "ridership": actual,
                    "expected_ridership": round(expected, 1),
                    "deficit_pct": round(deficit, 1),
                    "complaints": row.get("total_complaints", np.nan),
                    "snow_cm": row.get("total_snow_cm", np.nan),
                    "snow_on_grnd_cm": row.get("snow_on_grnd_cm", np.nan),
                }
            )
    return pd.DataFrame(all_rows)


def compute_summary(events: pd.DataFrame, details: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, ev in events.iterrows():
        eid = ev["event_id"]
        ev_detail = details[details["event_id"] == eid].copy()
        ev_detail = ev_detail.dropna(subset=["deficit_pct"])

        post_storm_start = ev["duration_days"] - 1
        post = ev_detail[ev_detail["relative_day"] >= post_storm_start]

        deficit_min_row = (
            post.loc[post["deficit_pct"].idxmin()] if len(post) > 0 else None
        )

        recovery_days = np.nan
        if deficit_min_row is not None and len(post) > 1:
            trough_day = deficit_min_row["relative_day"]
            after_trough = post[post["relative_day"] > trough_day]
            for _, r in after_trough.iterrows():
                if r["deficit_pct"] >= -5:
                    recovery_days = r["relative_day"] - post_storm_start
                    break
            if pd.isna(recovery_days):
                still_deficit = after_trough[after_trough["deficit_pct"] < -5]
                if len(still_deficit) == 0 and len(after_trough) > 0:
                    last_day = after_trough.iloc[-1]
                    recovery_days = last_day["relative_day"] - post_storm_start

        peak_complaints_day = np.nan
        complaints_peak = np.nan
        if len(post) > 0 and post["complaints"].notna().any():
            peak_idx = post["complaints"].idxmax()
            peak_complaints_day = post.loc[peak_idx, "relative_day"] - post_storm_start
            complaints_peak = post.loc[peak_idx, "complaints"]

        rows.append(
            {
                "event_id": eid,
                "start_date": ev["start_date"],
                "end_date": ev["end_date"],
                "total_snow_cm": ev["total_snow_cm"],
                "peak_snow_cm": ev["peak_snow_cm"],
                "duration_days": ev["duration_days"],
                "peak_complaints_day": peak_complaints_day,
                "complaints_peak": complaints_peak,
                "ridership_trough": deficit_min_row["deficit_pct"]
                if deficit_min_row is not None
                else np.nan,
                "recovery_days": recovery_days,
            }
        )
    return pd.DataFrame(rows)


def plot_event_panel(details: pd.DataFrame, events: pd.DataFrame) -> None:
    top_events = events.nlargest(TOP_N_EVENTS, "total_snow_cm")
    n = len(top_events)
    fig, axes = plt.subplots(n, 1, figsize=(14, 4 * n), sharex=True)
    if n == 1:
        axes = [axes]

    for ax, (_, ev) in zip(axes, top_events.iterrows()):
        eid = ev["event_id"]
        ev_data = details[details["event_id"] == eid].copy()
        ev_data = ev_data.dropna(subset=["deficit_pct"])

        days = ev_data["relative_day"]
        deficit = ev_data["deficit_pct"]
        complaints = ev_data["complaints"].fillna(0)

        ax2 = ax.twinx()

        ax2.bar(
            days,
            complaints,
            width=0.8,
            color="#ff9900",
            alpha=0.5,
            label="311 complaints",
            zorder=1,
        )
        ax.plot(
            days,
            deficit,
            color="#d62728",
            linewidth=2,
            marker="o",
            markersize=4,
            label="Ridership deficit %",
            zorder=2,
        )
        ax.axhline(0, color="#888888", linewidth=0.8, linestyle="-", zorder=0)
        ax.axvline(
            0,
            color="#333333",
            linewidth=1.5,
            linestyle="--",
            label="Storm day",
            zorder=3,
        )

        ax.set_ylabel("Ridership deficit %", color="#d62728")
        ax2.set_ylabel("311 complaints", color="#ff9900")
        ax.set_ylim(min(deficit.min() * 1.2, -10), max(abs(deficit.min()) * 0.3, 10))
        ax2.set_ylim(bottom=0)
        date_str = ev["start_date"].strftime("%Y-%m-%d")
        ax.set_title(
            f"Storm of {date_str}: {ev['total_snow_cm']:.1f} cm snow over {ev['duration_days']} day(s)",
            fontsize=11,
            fontweight="bold",
        )
        ax.tick_params(axis="y", labelcolor="#d62728")
        ax2.tick_params(axis="y", labelcolor="#ff9900")

        lines1, labels1 = ax.get_legend_handles_labels()
        lines2, labels2 = ax2.get_legend_handles_labels()
        ax.legend(
            lines1 + lines2,
            labels1 + labels2,
            loc="lower left",
            fontsize="small",
            frameon=True,
        )

    axes[-1].set_xlabel("Days relative to storm start")
    axes[-1].xaxis.set_major_locator(mticker.MultipleLocator(1))
    fig.suptitle(
        "Snowfall Event Study: Ridership Deficit & 311 Complaints",
        fontsize=14,
        fontweight="bold",
        y=1.01,
    )
    fig.tight_layout()
    path = OUTPUTS / "event-study-panel.png"
    fig.savefig(path, dpi=150, bbox_inches="tight")
    print(f"Saved {path}")
    plt.close(fig)


def plot_aggregate_curve(details: pd.DataFrame) -> None:
    pivot_deficit = details.pivot_table(
        index="relative_day", columns="event_id", values="deficit_pct"
    )
    pivot_complaints = details.pivot_table(
        index="relative_day", columns="event_id", values="complaints"
    )

    fig, ax1 = plt.subplots(figsize=(12, 6))
    ax2 = ax1.twinx()

    mean_deficit = pivot_deficit.mean(axis=1)
    sem_deficit = pivot_deficit.sem(axis=1)
    ci_lo = mean_deficit - 1.96 * sem_deficit.fillna(0)
    ci_hi = mean_deficit + 1.96 * sem_deficit.fillna(0)

    mean_complaints = pivot_complaints.mean(axis=1)
    sem_complaints = pivot_complaints.sem(axis=1)
    ci_lo_c = mean_complaints - 1.96 * sem_complaints.fillna(0)
    ci_hi_c = mean_complaints + 1.96 * sem_complaints.fillna(0)

    ax1.fill_between(mean_deficit.index, ci_lo, ci_hi, color="#d62728", alpha=0.15)
    ax1.plot(
        mean_deficit.index,
        mean_deficit,
        color="#d62728",
        linewidth=2.5,
        label="Mean ridership deficit %",
    )
    ax1.axhline(0, color="#888888", linewidth=0.8, linestyle="-")
    ax1.axvline(0, color="#333333", linewidth=1.5, linestyle="--", label="Storm day")

    ax2.fill_between(
        mean_complaints.index,
        ci_lo_c.clip(lower=0),
        ci_hi_c,
        color="#ff9900",
        alpha=0.15,
    )
    ax2.plot(
        mean_complaints.index,
        mean_complaints,
        color="#ff9900",
        linewidth=2.5,
        label="Mean 311 complaints",
    )
    ax2.set_ylim(bottom=0)

    ax1.set_xlabel("Days relative to storm start")
    ax1.set_ylabel("Ridership deficit %", color="#d62728")
    ax2.set_ylabel("311 complaints", color="#ff9900")
    ax1.tick_params(axis="y", labelcolor="#d62728")
    ax2.tick_params(axis="y", labelcolor="#ff9900")
    ax1.xaxis.set_major_locator(mticker.MultipleLocator(1))

    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(
        lines1 + lines2,
        labels1 + labels2,
        loc="lower right",
        fontsize="small",
        frameon=True,
    )

    ax1.set_title(
        "Aggregate Recovery Curve: Mean Ridership Deficit & 311 Complaints After Snowfall",
        fontsize=13,
        fontweight="bold",
    )
    fig.tight_layout()
    path = OUTPUTS / "aggregate-recovery-curve.png"
    fig.savefig(path, dpi=150, bbox_inches="tight")
    print(f"Saved {path}")
    plt.close(fig)


def main() -> int:
    print("Loading weather data...", file=sys.stderr)
    weather = load_weather()
    print(f"  Weather: {len(weather)} days loaded", file=sys.stderr)

    print("Loading ridership data...", file=sys.stderr)
    ridership = load_ridership()
    print(f"  Ridership: {len(ridership)} days loaded", file=sys.stderr)

    print("Loading 311 complaints...", file=sys.stderr)
    complaints = load_311()
    print(f"  311: {len(complaints)} days loaded", file=sys.stderr)

    merged = weather.merge(ridership, on="date", how="left")
    merged = merged.merge(complaints, on="date", how="left")
    merged["ridership"] = merged["ridership"].fillna(0).astype(int)
    merged["total_complaints"] = merged["total_complaints"].fillna(0).astype(int)
    merged = merged.sort_values("date").reset_index(drop=True)

    print("Finding snowfall events...", file=sys.stderr)
    events = find_snow_events(merged)
    print(f"  Found {len(events)} snowfall event(s)", file=sys.stderr)
    for _, ev in events.iterrows():
        print(
            f"    Event {ev['event_id']}: {ev['start_date'].strftime('%Y-%m-%d')} to "
            f"{ev['end_date'].strftime('%Y-%m-%d')}, {ev['total_snow_cm']:.1f} cm total snow",
            file=sys.stderr,
        )

    if events.empty:
        print("No snowfall events found. Exiting.", file=sys.stderr)
        return 0

    print("Building event details...", file=sys.stderr)
    details = build_event_details(merged, events)

    print("Computing summary...", file=sys.stderr)
    summary = compute_summary(events, details)

    details.to_csv(OUTPUTS / "event-details.csv", index=False)
    summary.to_csv(OUTPUTS / "summary.csv", index=False)
    print(f"Wrote {len(details)} rows to outputs/event-details.csv")
    print(f"Wrote {len(summary)} rows to outputs/summary.csv")

    print("Generating plots...", file=sys.stderr)
    sns.set_theme(style="whitegrid", font_scale=1.1)
    plot_event_panel(details, events)
    plot_aggregate_curve(details)

    print("\n=== Key Results ===")
    recovered = summary[summary["recovery_days"].notna()]
    if len(recovered) > 0:
        mean_recovery = recovered["recovery_days"].mean()
        print(
            f"Mean recovery time: {mean_recovery:.1f} days to return within 5% of baseline"
        )
    else:
        print("No events fully recovered within the 14-day window")

    clearing_days_list = []
    for _, ev in events.iterrows():
        eid = ev["event_id"]
        post_storm_offset = ev["duration_days"] - 1
        ev_post = details[
            (details["event_id"] == eid)
            & (details["relative_day"] >= post_storm_offset)
            & details["complaints"].notna()
        ]
        if len(ev_post) > 0:
            near_zero = ev_post[ev_post["complaints"] <= 1]
            if len(near_zero) > 0:
                first_near_zero = near_zero["relative_day"].min()
                clearing_days_list.append(first_near_zero - post_storm_offset)
    if clearing_days_list:
        mean_clearing = np.mean(clearing_days_list)
        print(
            f"Mean 311 complaint clearing time: {mean_clearing:.1f} days after storm end"
        )

    if len(recovered) > 0:
        deficit_trough = summary["ridership_trough"].mean()
        print(f"Mean ridership trough: {deficit_trough:.1f}% below baseline")

    return 0


if __name__ == "__main__":
    sys.exit(main())
