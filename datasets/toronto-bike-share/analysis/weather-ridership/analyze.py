"""Weather-ridership overlay analysis for Bike Share Toronto 2025.

Merges daily weather data from the toronto-weather-daily dataset (ECCC Toronto
Pearson, station 51459) with bike-share daily ridership, identifies significant
precipitation events, and produces a dual-panel figure.

See README.md for full description.
"""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

REPO_ROOT = Path(__file__).resolve().parent.parents[3]
WEATHER_DIR = REPO_ROOT / "datasets" / "toronto-weather-daily"
WEATHER_RAW = WEATHER_DIR / "raw" / "toronto-pearson-daily-2025.csv"

BIKE_DIR = REPO_ROOT / "datasets" / "toronto-bike-share"
BIKE_RAW_DIR = BIKE_DIR / "raw"
SEASONAL_DIR = BIKE_DIR / "analysis" / "seasonal-ridership" / "outputs"

SCRIPT_DIR = Path(__file__).resolve().parent
OUTPUTS = SCRIPT_DIR / "outputs"
OUTPUTS.mkdir(exist_ok=True)

PRECIP_THRESHOLDS = {
    "total_snow_cm": 5.0,
    "total_rain_mm": 10.0,
    "total_precip_mm": 15.0,
}

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
    return df.rename(columns=rename)


def load_weather() -> pd.DataFrame:
    if not WEATHER_RAW.exists():
        print(f"ERROR: Weather data not found at {WEATHER_RAW}", file=sys.stderr)
        print(
            "Run the fetch procedure in datasets/toronto-weather-daily/raw/SOURCE.md first.",
            file=sys.stderr,
        )
        sys.exit(1)

    df = pd.read_csv(WEATHER_RAW)

    df.columns = [c.strip() for c in df.columns]
    df = df.rename(
        columns={
            "Date/Time": "date",
            "Max Temp (°C)": "max_temp_c",
            "Min Temp (°C)": "min_temp_c",
            "Mean Temp (°C)": "temp_mean_c",
            "Total Rain (mm)": "total_rain_mm",
            "Total Snow (cm)": "total_snow_cm",
            "Total Precip (mm)": "total_precip_mm",
            "Snow on Grnd (cm)": "snow_on_grnd_cm",
        }
    )
    df["date"] = pd.to_datetime(df["date"])

    for col in [
        "max_temp_c",
        "min_temp_c",
        "temp_mean_c",
        "total_rain_mm",
        "total_snow_cm",
        "total_precip_mm",
        "snow_on_grnd_cm",
    ]:
        if col in df.columns:
            df[col] = pd.to_numeric(
                df[col].astype(str).str.replace("T", "0.0"), errors="coerce"
            )
            df[col] = df[col].fillna(0.0)

    return df[
        [
            "date",
            "max_temp_c",
            "min_temp_c",
            "temp_mean_c",
            "total_rain_mm",
            "total_snow_cm",
            "total_precip_mm",
            "snow_on_grnd_cm",
        ]
    ].copy()


def load_ridership() -> pd.DataFrame:
    daily_csv = SEASONAL_DIR / "daily-rides.csv"
    if daily_csv.exists():
        daily = pd.read_csv(daily_csv)
        daily["date"] = pd.to_datetime(daily["date"])
        daily_2025 = daily[daily["year"] == 2025][["date", "trips"]].copy()
        daily_2025 = daily_2025.rename(columns={"trips": "ridership"})
        if len(daily_2025) > 0:
            return daily_2025.reset_index(drop=True)

    raw_path = BIKE_RAW_DIR / "bike-share-toronto-ridership-2025.csv"
    df = pd.read_csv(raw_path, low_memory=False)
    df = normalize_columns(df)

    if "start_time" not in df.columns:
        candidates = [c for c in df.columns if c in START_TIME_NAMES]
        if not candidates:
            print("ERROR: No time column found in ridership data", file=sys.stderr)
            sys.exit(1)
        df = df.rename(columns={candidates[0]: "start_time"})

    df["start_time"] = pd.to_datetime(df["start_time"], errors="coerce")
    df = df.dropna(subset=["start_time"])
    df["date"] = df["start_time"].dt.date
    daily = df.groupby("date").size().reset_index(name="ridership")
    daily["date"] = pd.to_datetime(daily["date"])
    return daily


def classify_event_type(rain_mm: float, snow_cm: float) -> str:
    is_rain = rain_mm >= PRECIP_THRESHOLDS["total_rain_mm"]
    is_snow = snow_cm >= PRECIP_THRESHOLDS["total_snow_cm"]
    is_precip_total = (rain_mm + snow_cm * 10) >= PRECIP_THRESHOLDS["total_precip_mm"]
    if is_rain and is_snow:
        return "mixed"
    if is_snow:
        return "snow"
    if is_rain:
        return "rain"
    if is_precip_total:
        if snow_cm > rain_mm / 10:
            return "snow"
        return "rain"
    return "none"


def find_precip_events(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
    is_sig = (
        (df["total_snow_cm"] >= PRECIP_THRESHOLDS["total_snow_cm"])
        | (df["total_rain_mm"] >= PRECIP_THRESHOLDS["total_rain_mm"])
        | (df["total_precip_mm"] >= PRECIP_THRESHOLDS["total_precip_mm"])
    )

    events = []
    in_event = False
    event_start = None
    event_dates = []

    for idx in range(len(df)):
        if is_sig.iloc[idx]:
            if not in_event:
                event_start = df["date"].iloc[idx]
                event_dates = [df["date"].iloc[idx]]
                in_event = True
            else:
                event_dates.append(df["date"].iloc[idx])
        else:
            if in_event:
                event_dates_arr = pd.DatetimeIndex(event_dates)
                sub = df[df["date"].isin(event_dates_arr)]
                rain_total = sub["total_rain_mm"].sum()
                snow_total = sub["total_snow_cm"].sum()
                etype = classify_event_type(rain_total, snow_total)
                events.append(
                    {
                        "start_date": event_start,
                        "end_date": event_dates[-1],
                        "duration_days": len(event_dates),
                        "total_rain_mm": round(rain_total, 1),
                        "total_snow_cm": round(snow_total, 1),
                        "type": etype,
                    }
                )
                in_event = False

    if in_event:
        event_dates_arr = pd.DatetimeIndex(event_dates)
        sub = df[df["date"].isin(event_dates_arr)]
        rain_total = sub["total_rain_mm"].sum()
        snow_total = sub["total_snow_cm"].sum()
        etype = classify_event_type(rain_total, snow_total)
        events.append(
            {
                "start_date": event_start,
                "end_date": event_dates[-1],
                "duration_days": len(event_dates),
                "total_rain_mm": round(rain_total, 1),
                "total_snow_cm": round(snow_total, 1),
                "type": etype,
            }
        )

    return pd.DataFrame(events), is_sig


def plot_figure(df: pd.DataFrame, events: pd.DataFrame) -> None:
    sns.set_theme(style="whitegrid", font_scale=1.1)

    df = df.copy()
    df = df.sort_values("date")
    df["ridership_ma7"] = df["ridership"].rolling(7, min_periods=3, center=True).mean()

    fig, (ax_top, ax_bot) = plt.subplots(
        2,
        1,
        figsize=(16, 9),
        sharex=True,
        gridspec_kw={"height_ratios": [2, 1], "hspace": 0.08},
    )

    for _, ev in events.iterrows():
        start = ev["start_date"]
        end = ev["end_date"]
        etype = ev["type"]
        if etype == "rain":
            color = "#4a90d9"
            alpha = 0.15
        elif etype == "snow":
            color = "#aaaaaa"
            alpha = 0.20
        else:
            color = "#7b4fa2"
            alpha = 0.18
        ax_top.axvspan(start, end, color=color, alpha=alpha, label=None)

    ax_top.scatter(
        df["date"], df["ridership"], color="#cccccc", s=8, alpha=0.6, zorder=2
    )
    ax_top.plot(
        df["date"], df["ridership_ma7"], color="#2171b5", linewidth=1.8, zorder=3
    )

    ax_top.set_ylabel("Daily trips")
    ax_top.set_title(
        "Bike Share Toronto 2025: Daily ridership and precipitation",
        fontsize=14,
        fontweight="bold",
    )
    ax_top.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"{x:,.0f}"))

    seen_labels = set()
    for _, ev in events.iterrows():
        start = ev["start_date"]
        end = ev["end_date"]
        etype = ev["type"]
        label = etype.capitalize() if etype not in seen_labels else None
        seen_labels.add(etype)
        if etype == "rain":
            color = "#4a90d9"
        elif etype == "snow":
            color = "#aaaaaa"
        else:
            color = "#7b4fa2"
        ax_top.axvspan(start, end, color=color, alpha=0.15, label=label)

    from matplotlib.patches import Patch

    legend_elements = [
        Patch(facecolor="#4a90d9", alpha=0.3, label="Rain event"),
        Patch(facecolor="#aaaaaa", alpha=0.4, label="Snow event"),
        Patch(facecolor="#7b4fa2", alpha=0.35, label="Mixed event"),
        plt.Line2D([0], [0], color="#2171b5", linewidth=2, label="7-day MA"),
        plt.Line2D(
            [0],
            [0],
            marker="o",
            color="#cccccc",
            markersize=5,
            linewidth=0,
            label="Actual daily",
        ),
    ]
    ax_top.legend(
        handles=legend_elements, loc="upper left", fontsize="small", frameon=True
    )

    rain_vals = df["total_rain_mm"].fillna(0)
    snow_mm_eq = df["total_snow_cm"].fillna(0) * 10

    bar_width = pd.Timedelta(hours=20)

    ax_bot.bar(
        df["date"],
        rain_vals,
        width=bar_width,
        color="#4a90d9",
        label="Rain (mm)",
        zorder=2,
    )
    ax_bot.bar(
        df["date"],
        snow_mm_eq,
        bottom=rain_vals,
        width=bar_width,
        color="#aaaaaa",
        label="Snow (cm × 10 = mm w.e.)",
        edgecolor="#666666",
        linewidth=0.5,
        hatch="//",
        zorder=2,
    )

    ax_bot.set_ylabel("Precipitation (mm water equivalent)")
    ax_bot.set_xlabel("Month")
    ax_bot.legend(loc="upper right", fontsize="small", frameon=True)

    import matplotlib.dates as mdates

    ax_bot.xaxis.set_major_locator(mdates.MonthLocator())
    ax_bot.xaxis.set_major_formatter(mdates.DateFormatter("%b"))

    fig.tight_layout()
    path = OUTPUTS / "weather-ridership-2025.png"
    fig.savefig(path, dpi=150)
    print(f"Saved {path}")
    plt.close(fig)


def main() -> int:
    print("Loading weather data...", file=sys.stderr)
    weather = load_weather()
    print(f"  Weather: {len(weather)} days loaded", file=sys.stderr)

    print("Loading ridership data...", file=sys.stderr)
    ridership = load_ridership()
    print(f"  Ridership: {len(ridership)} days loaded", file=sys.stderr)

    df = pd.merge(weather, ridership, on="date", how="left")
    df["ridership"] = df["ridership"].fillna(0).astype(int)
    df = df.sort_values("date").reset_index(drop=True)

    print("Finding precipitation events...", file=sys.stderr)
    events, is_precip_event = find_precip_events(df)
    df["is_precip_event"] = is_precip_event
    print(f"  Found {len(events)} significant precip events", file=sys.stderr)

    merged_csv = df[
        [
            "date",
            "ridership",
            "total_rain_mm",
            "total_snow_cm",
            "total_precip_mm",
            "temp_mean_c",
            "is_precip_event",
        ]
    ].copy()
    merged_csv["is_precip_event"] = merged_csv["is_precip_event"].astype(int)
    merged_csv.to_csv(OUTPUTS / "weather-ridership-2025.csv", index=False)
    print(f"Wrote {len(merged_csv)} rows to outputs/weather-ridership-2025.csv")

    events.to_csv(OUTPUTS / "precip-events-2025.csv", index=False)
    print(f"Wrote {len(events)} events to outputs/precip-events-2025.csv")

    print("Generating figure...", file=sys.stderr)
    plot_figure(df, events)

    return 0


if __name__ == "__main__":
    sys.exit(main())
