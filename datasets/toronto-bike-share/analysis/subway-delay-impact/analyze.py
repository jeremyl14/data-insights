"""Subway delay impact on bike-share ridership analysis for Bike Share Toronto 2025.

Quantifies whether TTC subway delays cause measurable increases in bike-share
ridership, especially near affected stations. Uses OLS regression controlling
for weather, day-of-week, and month.

See README.md for full description.
"""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
import statsmodels.formula.api as smf

REPO_ROOT = Path(__file__).resolve().parent.parents[3]

BIKE_DIR = REPO_ROOT / "datasets" / "toronto-bike-share"
BIKE_RAW_DIR = BIKE_DIR / "raw"
SEASONAL_DIR = BIKE_DIR / "analysis" / "seasonal-ridership" / "outputs"
STATIONS_PATH = (
    REPO_ROOT / "datasets" / "toronto-bike-stations" / "raw" / "stations.csv"
)

TTC_DIR = REPO_ROOT / "datasets" / "ttc-subway-delay"
TTC_RAW = TTC_DIR / "raw" / "ttc-subway-delay-data-since-2025.csv"
TTC_CODES = TTC_DIR / "raw" / "ttc-subway-delay-codes.xlsx"

WEATHER_RAW = (
    REPO_ROOT
    / "datasets"
    / "toronto-weather-daily"
    / "raw"
    / "toronto-pearson-daily-2025.csv"
)

SCRIPT_DIR = Path(__file__).resolve().parent
OUTPUTS = SCRIPT_DIR / "outputs"
OUTPUTS.mkdir(exist_ok=True)

START_TIME_NAMES = {
    "trip_start_time",
    "start_time",
    "start_station_time",
}

DISRUPTION_PERCENTILE = 90
SINGLE_DELAY_THRESH_MIN = 30

NEAR_SUBWAY_MATCHES = {
    "BATHURST STATION": [
        "Bathurst St / Front St W",
        "Bathurst St / Lennox St",
        "Bathurst St/Queens Quay(Billy Bishop Airport)",
    ],
    "BAY STATION": [
        "Bay St / Charles St W - SMART",
        "Bay St / Dundas St W",
        "Bay St / Harbour St",
        "Bay St / Queens Quay W (Ferry Terminal)",
    ],
    "BLOOR STATION": [
        "Bloor St E / Parliament St",
        "Bloor St W / Huron St",
        "Bloor St W / Kingsmill Rd",
    ],
    "BROADVIEW STATION": [
        "Danforth Ave / Dewhurst Blvd",
    ],
    "CHESTER STATION": [],
    "CHRISTIE STATION": [
        "Christie Pits",
    ],
    "COLLEGE STATION": [
        "College St / Spadina Ave",
    ],
    "DUNDAS STATION": [
        "Dundonald St / Church St",
    ],
    "DUNDAS WEST STATION": [
        "Dundas St W",
    ],
    "EGLINTON STATION": [
        "Davisville Ave / Pailton Cres",
    ],
    "FINCH STATION": [],
    "HIGH PARK STATION": [],
    "KEELE STATION": [],
    "KING STATION": [
        "King St W / Charlotte St",
    ],
    "KIPLING STATION": [],
    "LANSDOWNE STATION": [],
    "MAIN STREET STATION": [],
    "OSSINGTON STATION": [],
    "QUEEN STATION": [
        "Queen St / Bay St",
    ],
    "QUEEN'S PARK STATION": [],
    "SPADINA STATION": [],
    "ST ANDREW STATION": [],
    "ST CLAIR STATION": [],
    "ST GEORGE STATION": [],
    "ST PATRICK STATION": [],
    "UNION STATION": [
        "Union Station",
        "Front St W / Bay St (North Side)",
        "Front St W / University Ave (2)",
        "Front St W / Yonge St (Hockey Hall of Fame)",
    ],
    "WARDEN STATION": [],
    "WELLESLEY STATION": [],
    "YONGE STATION": [
        "Yonge St / Dundas Sq",
    ],
    "YORK MILLS STATION": [],
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


def load_ttc_delays() -> pd.DataFrame:
    if not TTC_RAW.exists():
        print(f"ERROR: TTC delay data not found at {TTC_RAW}", file=sys.stderr)
        sys.exit(1)

    df = pd.read_csv(TTC_RAW)
    df.columns = [c.strip() for c in df.columns]

    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df["Time"] = df["Time"].astype(str).str.strip()
    df = df.dropna(subset=["Date"])

    df = df[df["Date"].dt.year == 2025].copy()

    df["Min Delay"] = pd.to_numeric(df["Min Delay"], errors="coerce").fillna(0)

    df["Station"] = df["Station"].str.strip().str.upper()

    daily = (
        df.groupby(df["Date"].dt.date)
        .agg(
            total_delay_min=("Min Delay", "sum"),
            num_events=("Min Delay", "count"),
            max_single_delay_min=("Min Delay", "max"),
        )
        .reset_index()
    )
    daily.columns = ["date", "total_delay_min", "num_events", "max_single_delay_min"]
    daily["date"] = pd.to_datetime(daily["date"])

    p90 = daily["total_delay_min"].quantile(DISRUPTION_PERCENTILE / 100)
    daily["is_disruption_day"] = (
        (daily["total_delay_min"] > p90)
        | (daily["max_single_delay_min"] >= SINGLE_DELAY_THRESH_MIN)
    ).astype(int)

    daily["is_strict_disruption"] = (
        (daily["total_delay_min"] > daily["total_delay_min"].quantile(0.95))
        | (daily["max_single_delay_min"] >= 60)
    ).astype(int)

    return daily


def load_weather() -> pd.DataFrame:
    if not WEATHER_RAW.exists():
        print(f"ERROR: Weather data not found at {WEATHER_RAW}", file=sys.stderr)
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


def load_near_subway_ridership() -> tuple[pd.DataFrame, dict[str, list[str]]]:
    raw_path = BIKE_RAW_DIR / "bike-share-toronto-ridership-2025.csv"
    df = pd.read_csv(raw_path, low_memory=False)
    df = normalize_columns(df)

    if "start_time" not in df.columns:
        candidates = [c for c in df.columns if c in START_TIME_NAMES]
        if not candidates:
            print("ERROR: No time column found in ridership data", file=sys.stderr)
            sys.exit(1)
        df = df.rename(columns={candidates[0]: "start_time"})

    if "start_station_name" not in df.columns:
        name_col_candidates = [
            c for c in df.columns if "station" in c and "name" in c and "start" in c
        ]
        if not name_col_candidates:
            print("ERROR: No start station name column found", file=sys.stderr)
            sys.exit(1)
        df = df.rename(columns={name_col_candidates[0]: "start_station_name"})

    df["start_time"] = pd.to_datetime(df["start_time"], errors="coerce")
    df = df.dropna(subset=["start_time"])
    df = df[df["start_time"].dt.year == 2025].copy()

    matched_stations = {}
    near_subway_names = set()
    for ttc_station, bike_names in NEAR_SUBWAY_MATCHES.items():
        found = []
        for bn in bike_names:
            if bn in df["start_station_name"].values:
                found.append(bn)
                near_subway_names.add(bn)
        if found:
            matched_stations[ttc_station] = found

    near_df = df[df["start_station_name"].isin(near_subway_names)].copy()
    near_df["date"] = near_df["start_time"].dt.date
    daily_near = (
        near_df.groupby("date").size().reset_index(name="near_subway_ridership")
    )
    daily_near["date"] = pd.to_datetime(daily_near["date"])

    return daily_near, matched_stations


def run_regression(
    merged: pd.DataFrame, dep_var: str, treatment: str = "is_disruption_day"
) -> pd.DataFrame:
    formula = (
        f"{dep_var} ~ {treatment} + temp_mean_c + total_rain_mm + total_snow_cm "
        f"+ C(day_of_week) + C(month)"
    )
    model = smf.ols(formula=formula, data=merged).fit(
        cov_type="HAC", cov_kwds={"maxlags": 7}
    )
    return model


def plot_delay_ridership_overview(merged: pd.DataFrame) -> None:
    sns.set_theme(style="whitegrid", font_scale=1.1)

    df = merged.copy().sort_values("date")
    df["ridership_ma7"] = df["ridership"].rolling(7, min_periods=3, center=True).mean()

    disruption_dates = df[df["is_disruption_day"] == 1]["date"]

    fig, (ax_top, ax_bot) = plt.subplots(
        2,
        1,
        figsize=(16, 9),
        sharex=True,
        gridspec_kw={"height_ratios": [2, 1], "hspace": 0.08},
    )

    for d in disruption_dates:
        ax_top.axvspan(
            d - pd.Timedelta(hours=12),
            d + pd.Timedelta(hours=12),
            color="#d9534f",
            alpha=0.2,
            zorder=1,
        )

    ax_top.scatter(
        df["date"], df["ridership"], color="#cccccc", s=8, alpha=0.6, zorder=2
    )
    ax_top.plot(
        df["date"], df["ridership_ma7"], color="#2171b5", linewidth=1.8, zorder=3
    )
    ax_top.set_ylabel("Daily trips")
    ax_top.set_title(
        "Bike Share Toronto 2025: Ridership and subway disruptions",
        fontsize=14,
        fontweight="bold",
    )
    ax_top.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"{x:,.0f}"))

    from matplotlib.patches import Patch

    legend_elements = [
        Patch(facecolor="#d9534f", alpha=0.4, label="Disruption day"),
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

    import matplotlib.dates as mdates

    bar_width = pd.Timedelta(hours=20)
    colors = [
        "#d9534f" if d in disruption_dates.values else "#2171b5" for d in df["date"]
    ]
    ax_bot.bar(
        df["date"], df["total_delay_min"], width=bar_width, color=colors, zorder=2
    )
    ax_bot.set_ylabel("Total delay (min)")
    ax_bot.set_xlabel("Month")
    ax_bot.xaxis.set_major_locator(mdates.MonthLocator())
    ax_bot.xaxis.set_major_formatter(mdates.DateFormatter("%b"))

    fig.tight_layout()
    path = OUTPUTS / "delay-ridership-overview.png"
    fig.savefig(path, dpi=150)
    print(f"Saved {path}")
    plt.close(fig)


def plot_disruption_effect(merged: pd.DataFrame) -> None:
    sns.set_theme(style="whitegrid", font_scale=1.1)

    fig, axes = plt.subplots(1, 2, figsize=(12, 5), sharey=False)

    for ax, col, title in [
        (axes[0], "ridership", "All trips"),
        (axes[1], "near_subway_ridership", "Near-subway trips"),
    ]:
        data = merged[merged[col].notna()].copy()
        data["Disruption"] = data["is_disruption_day"].map(
            {0: "Normal day", 1: "Disruption day"}
        )
        sns.boxplot(
            data=data,
            x="Disruption",
            y=col,
            ax=ax,
            palette=["#4a90d9", "#d9534f"],
            hue="Disruption",
            legend=False,
        )
        ax.set_title(title, fontsize=12, fontweight="bold")
        ax.set_xlabel("")
        ax.set_ylabel("Daily trips")

    fig.suptitle(
        "Ridership on subway disruption days vs normal days",
        fontsize=14,
        fontweight="bold",
    )
    fig.tight_layout()
    path = OUTPUTS / "disruption-effect.png"
    fig.savefig(path, dpi=150)
    print(f"Saved {path}")
    plt.close(fig)


def plot_regression_coefficients(model_all, model_near) -> None:
    sns.set_theme(style="whitegrid", font_scale=1.1)

    predictors = ["is_disruption_day", "temp_mean_c", "total_rain_mm", "total_snow_cm"]

    rows = []
    for pred in predictors:
        for label, model in [
            ("All trips", model_all),
            ("Near-subway trips", model_near),
        ]:
            key = pred
            if key in model.params.index:
                rows.append(
                    {
                        "predictor": pred,
                        "model": label,
                        "coef": model.params[key],
                        "ci_lower": model.conf_int().loc[key, 0],
                        "ci_upper": model.conf_int().loc[key, 1],
                    }
                )

    coef_df = pd.DataFrame(rows)

    fig, ax = plt.subplots(figsize=(10, 6))
    range(len(coef_df))
    for i, row in coef_df.iterrows():
        color = "#2171b5" if row["model"] == "All trips" else "#d9534f"
        marker = "o" if row["model"] == "All trips" else "s"
        ax.errorbar(
            row["coef"],
            i,
            xerr=[[row["coef"] - row["ci_lower"]], [row["ci_upper"] - row["coef"]]],
            fmt=marker,
            color=color,
            capsize=4,
            markersize=8,
            linewidth=1.5,
        )
    ax.axvline(0, color="#666666", linestyle="--", linewidth=0.8)
    ax.set_yticks(range(len(coef_df)))
    ax.set_yticklabels(
        [f"{r['predictor']} ({r['model']})" for _, r in coef_df.iterrows()]
    )
    ax.set_xlabel("Coefficient (with 95% CI)")
    ax.set_title(
        "Effect of subway disruptions on daily ridership (controlling for weather)",
        fontsize=13,
        fontweight="bold",
    )
    fig.tight_layout()
    path = OUTPUTS / "regression-coefficients.png"
    fig.savefig(path, dpi=150)
    print(f"Saved {path}")
    plt.close(fig)


def main() -> int:
    print("Loading TTC delay data...", file=sys.stderr)
    delays = load_ttc_delays()
    n_disruption = delays["is_disruption_day"].sum()
    print(f"  {len(delays)} days, {n_disruption} disruption days", file=sys.stderr)

    print("Loading weather data...", file=sys.stderr)
    weather = load_weather()
    print(f"  Weather: {len(weather)} days loaded", file=sys.stderr)

    print("Loading bike-share ridership...", file=sys.stderr)
    ridership = load_ridership()
    print(f"  Ridership: {len(ridership)} days loaded", file=sys.stderr)

    print("Loading near-subway-station ridership...", file=sys.stderr)
    near_ridership, matched_stations = load_near_subway_ridership()
    print(
        f"  Near-subway ridership: {len(near_ridership)} days loaded", file=sys.stderr
    )
    print(
        f"  Matched {len(matched_stations)} TTC stations to bike-share stations:",
        file=sys.stderr,
    )
    for ttc, bikes in sorted(matched_stations.items()):
        print(f"    {ttc} -> {bikes}", file=sys.stderr)

    delays.to_csv(OUTPUTS / "daily-delay-summary.csv", index=False)
    print(f"Wrote {len(delays)} rows to outputs/daily-delay-summary.csv")

    merged = pd.merge(delays, weather, on="date", how="left")
    merged = pd.merge(merged, ridership, on="date", how="left")
    merged = pd.merge(merged, near_ridership, on="date", how="left")
    merged["ridership"] = merged["ridership"].fillna(0).astype(int)
    merged["near_subway_ridership"] = (
        merged["near_subway_ridership"].fillna(0).astype(int)
    )
    merged = merged.sort_values("date").reset_index(drop=True)

    merged["day_of_week"] = merged["date"].dt.dayofweek
    merged["month"] = merged["date"].dt.month

    for col in ["temp_mean_c", "total_rain_mm", "total_snow_cm"]:
        if col in merged.columns:
            merged[col] = merged[col].fillna(0.0)

    print("Running binary disruption regression (all trips)...", file=sys.stderr)
    model_all = run_regression(merged, "ridership", "is_disruption_day")
    print(model_all.summary(), file=sys.stderr)

    print("Running binary disruption regression (near-subway)...", file=sys.stderr)
    model_near = run_regression(merged, "near_subway_ridership", "is_disruption_day")
    print(model_near.summary(), file=sys.stderr)

    print("Running strict binary disruption regression (all trips)...", file=sys.stderr)
    model_strict_all = run_regression(merged, "ridership", "is_strict_disruption")
    print(model_strict_all.summary(), file=sys.stderr)

    print(
        "Running strict binary disruption regression (near-subway)...", file=sys.stderr
    )
    model_strict_near = run_regression(
        merged, "near_subway_ridership", "is_strict_disruption"
    )
    print(model_strict_near.summary(), file=sys.stderr)

    print(
        "Running continuous (total_delay_min) regression (all trips)...",
        file=sys.stderr,
    )
    model_cont_all = run_regression(merged, "ridership", "total_delay_min")
    print(model_cont_all.summary(), file=sys.stderr)

    print(
        "Running continuous (total_delay_min) regression (near-subway)...",
        file=sys.stderr,
    )
    model_cont_near = run_regression(merged, "near_subway_ridership", "total_delay_min")
    print(model_cont_near.summary(), file=sys.stderr)

    reg_rows = []
    for model, label in [
        (model_all, "binary_all_trips"),
        (model_near, "binary_near_subway"),
        (model_strict_all, "strict_all_trips"),
        (model_strict_near, "strict_near_subway"),
        (model_cont_all, "continuous_all_trips"),
        (model_cont_near, "continuous_near_subway"),
    ]:
        for param in model.params.index:
            reg_rows.append(
                {
                    "model": label,
                    "predictor": param,
                    "coefficient": model.params[param],
                    "std_err": model.bse[param],
                    "t_value": model.tvalues[param],
                    "p_value": model.pvalues[param],
                }
            )
    reg_df = pd.DataFrame(reg_rows)
    reg_df.to_csv(OUTPUTS / "regression-results.csv", index=False)
    print(f"Wrote {len(reg_df)} rows to outputs/regression-results.csv")

    print("Generating figures...", file=sys.stderr)
    plot_delay_ridership_overview(merged)
    plot_disruption_effect(merged)
    plot_regression_coefficients(model_all, model_near)

    n_strict = merged["is_strict_disruption"].sum()

    print("\n=== KEY RESULTS ===", file=sys.stderr)
    for label, model, treatment in [
        ("Binary (90th %ile / 30 min)", model_all, "is_disruption_day"),
        ("Binary (95th %ile / 60 min)", model_strict_all, "is_strict_disruption"),
        ("Continuous (total_delay_min)", model_cont_all, "total_delay_min"),
    ]:
        if treatment in model.params.index:
            coef = model.params[treatment]
            pval = model.pvalues[treatment]
            print(
                f"All trips - {label}: coef={coef:.2f}, p={pval:.4f}", file=sys.stderr
            )
    for label, model, treatment in [
        ("Binary (90th %ile / 30 min)", model_near, "is_disruption_day"),
        ("Binary (95th %ile / 60 min)", model_strict_near, "is_strict_disruption"),
        ("Continuous (total_delay_min)", model_cont_near, "total_delay_min"),
    ]:
        if treatment in model.params.index:
            coef = model.params[treatment]
            pval = model.pvalues[treatment]
            print(
                f"Near-subway - {label}: coef={coef:.2f}, p={pval:.4f}", file=sys.stderr
            )
    print(f"Disruption days (broad): {n_disruption}", file=sys.stderr)
    print(f"Disruption days (strict): {n_strict}", file=sys.stderr)
    print(f"All trips R² (binary): {model_all.rsquared:.4f}", file=sys.stderr)
    print(f"Near-subway R² (binary): {model_near.rsquared:.4f}", file=sys.stderr)
    print(f"All trips R² (continuous): {model_cont_all.rsquared:.4f}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())
