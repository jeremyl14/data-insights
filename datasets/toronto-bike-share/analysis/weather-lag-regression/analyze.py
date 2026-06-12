"""Distributed lag regression: quantifying how rain, snow (same-day + lagged),
and temperature affect daily bike-share ridership in Toronto, 2025.

See README.md for full description.
"""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import statsmodels.api as sm

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[3]
WEATHER_DIR = REPO_ROOT / "datasets" / "toronto-weather-daily"
WEATHER_RAW = WEATHER_DIR / "raw" / "toronto-pearson-daily-2025.csv"
BIKE_DIR = REPO_ROOT / "datasets" / "toronto-bike-share"
WEATHER_RIDERSHIP_DIR = BIKE_DIR / "analysis" / "weather-ridership" / "outputs"
COMPLAINTS_RAW = BIKE_DIR / "raw" / "311-bike-infrastructure-daily-2025.csv"
OUTPUTS = SCRIPT_DIR / "outputs"
OUTPUTS.mkdir(exist_ok=True)

MAX_LAG = 14
COMPLAINT_LAGS = 7


def load_merged_data() -> pd.DataFrame:
    merged = pd.read_csv(WEATHER_RIDERSHIP_DIR / "weather-ridership-2025.csv")
    merged["date"] = pd.to_datetime(merged["date"])

    complaints = pd.read_csv(COMPLAINTS_RAW)
    complaints["date"] = pd.to_datetime(complaints["date"])
    complaints = complaints[["date", "total_complaints"]].rename(
        columns={"total_complaints": "complaints_311"}
    )
    merged = pd.merge(merged, complaints, on="date", how="left")
    merged["complaints_311"] = merged["complaints_311"].fillna(0).astype(int)

    return merged


def load_snow_on_ground() -> pd.DataFrame:
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
            "Snow on Grnd (cm)": "snow_on_grnd_cm",
        }
    )
    df["date"] = pd.to_datetime(df["date"])
    if "snow_on_grnd_cm" in df.columns:
        df["snow_on_grnd_cm"] = pd.to_numeric(
            df["snow_on_grnd_cm"].astype(str).str.replace("T", "0.0"),
            errors="coerce",
        )
        df["snow_on_grnd_cm"] = df["snow_on_grnd_cm"].fillna(0.0)
        return df[["date", "snow_on_grnd_cm"]].copy()
    return pd.DataFrame({"date": pd.to_datetime(df["date"]), "snow_on_grnd_cm": 0.0})


def build_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df = df.sort_values("date").reset_index(drop=True)

    for lag in range(1, MAX_LAG + 1):
        df[f"snow_lag_{lag}"] = df["total_snow_cm"].shift(lag)

    for lag in range(1, COMPLAINT_LAGS + 1):
        df[f"complaints_lag_{lag}"] = df["complaints_311"].shift(lag)

    df["day_of_week"] = df["date"].dt.dayofweek
    df["month"] = df["date"].dt.month

    df = df.dropna().reset_index(drop=True)

    return df


def run_regression(df: pd.DataFrame):
    exog_cols = ["total_rain_mm", "total_snow_cm", "temp_mean_c", "complaints_311"]
    for lag in range(1, MAX_LAG + 1):
        exog_cols.append(f"snow_lag_{lag}")
    for lag in range(1, COMPLAINT_LAGS + 1):
        exog_cols.append(f"complaints_lag_{lag}")

    dow_dummies = pd.get_dummies(
        df["day_of_week"], prefix="dow", drop_first=True
    ).astype(float)
    month_dummies = pd.get_dummies(df["month"], prefix="month", drop_first=True).astype(
        float
    )

    exog = df[exog_cols].astype(float)
    exog = pd.concat([exog, dow_dummies, month_dummies], axis=1)
    exog = sm.add_constant(exog)

    y = df["ridership"].astype(float)

    model = sm.OLS(y, exog).fit()
    return model


def plot_lag_coefficients(model) -> None:
    lag_labels = ["lag_0"] + [f"lag_{i}" for i in range(1, MAX_LAG + 1)]
    coefs = [model.params["total_snow_cm"]] + [
        model.params[f"snow_lag_{i}"] for i in range(1, MAX_LAG + 1)
    ]
    ci_low = [model.conf_int().loc["total_snow_cm", 0]] + [
        model.conf_int().loc[f"snow_lag_{i}", 0] for i in range(1, MAX_LAG + 1)
    ]
    ci_high = [model.conf_int().loc["total_snow_cm", 1]] + [
        model.conf_int().loc[f"snow_lag_{i}", 1] for i in range(1, MAX_LAG + 1)
    ]
    p_values = [model.pvalues["total_snow_cm"]] + [
        model.pvalues[f"snow_lag_{i}"] for i in range(1, MAX_LAG + 1)
    ]

    x = list(range(len(lag_labels)))
    colors = ["#2171b5" if p < 0.05 else "#aaaaaa" for p in p_values]

    fig, ax = plt.subplots(figsize=(10, 6))
    for i in range(len(lag_labels)):
        ax.errorbar(
            x[i],
            coefs[i],
            yerr=[[coefs[i] - ci_low[i]], [ci_high[i] - coefs[i]]],
            fmt="o",
            color=colors[i],
            markersize=6,
            capsize=3,
            capthick=1,
            zorder=3,
        )

    ax.axhline(0, color="#666666", linewidth=0.8, linestyle="--")
    ax.set_xlabel("Days after snowfall")
    ax.set_ylabel("Change in daily trips per 1 cm snow")
    ax.set_title("Effect of snow on daily ridership, by lag (days after snowfall)")
    ax.set_xticks(x)
    ax.set_xticklabels([str(i) for i in x])

    rain_coef = model.params["total_rain_mm"]
    rain_p = model.pvalues["total_rain_mm"]
    temp_coef = model.params["temp_mean_c"]
    temp_p = model.pvalues["temp_mean_c"]
    r2 = model.rsquared
    r2_adj = model.rsquared_adj

    text = (
        f"Rain coef: {rain_coef:.1f} (p={rain_p:.4f})\n"
        f"Temp coef: {temp_coef:.1f} (p={temp_p:.4f})\n"
        f"R\u00b2: {r2:.3f}\n"
        f"Adj. R\u00b2: {r2_adj:.3f}"
    )
    ax.text(
        0.98,
        0.98,
        text,
        transform=ax.transAxes,
        fontsize=9,
        verticalalignment="top",
        horizontalalignment="right",
        bbox=dict(
            boxstyle="round,pad=0.4", facecolor="white", edgecolor="#cccccc", alpha=0.9
        ),
    )

    fig.tight_layout()
    path = OUTPUTS / "lag-coefficients.png"
    fig.savefig(path, dpi=150)
    print(f"Saved {path}")
    plt.close(fig)


def plot_cumulative_effect(model) -> None:
    snow_coefs = [model.params["total_snow_cm"]] + [
        model.params[f"snow_lag_{i}"] for i in range(1, MAX_LAG + 1)
    ]
    cumulative = np.cumsum(snow_coefs)

    x = list(range(len(cumulative)))

    fig, ax = plt.subplots(figsize=(10, 6))
    ax.step(x, cumulative, where="mid", color="#2171b5", linewidth=2, zorder=3)
    ax.fill_between(x, 0, cumulative, step="mid", alpha=0.2, color="#2171b5")
    ax.axhline(0, color="#666666", linewidth=0.8, linestyle="--")

    ax.set_xlabel("Days after snowfall")
    ax.set_ylabel("Cumulative trip reduction")
    ax.set_title("Cumulative ridership impact of a 1 cm snowfall event")
    ax.set_xticks(x)

    fig.tight_layout()
    path = OUTPUTS / "cumulative-effect.png"
    fig.savefig(path, dpi=150)
    print(f"Saved {path}")
    plt.close(fig)


def plot_actual_vs_predicted(model, df: pd.DataFrame) -> None:
    predicted = model.fittedvalues
    actual = df["ridership"].astype(float)

    fig, ax = plt.subplots(figsize=(8, 8))
    ax.scatter(
        actual,
        predicted,
        alpha=0.5,
        s=20,
        color="#2171b5",
        edgecolors="white",
        linewidths=0.3,
    )
    lim_min = min(actual.min(), predicted.min()) * 0.9
    lim_max = max(actual.max(), predicted.max()) * 1.1
    ax.plot(
        [lim_min, lim_max],
        [lim_min, lim_max],
        color="#cccccc",
        linewidth=1,
        linestyle="--",
        zorder=1,
    )
    ax.set_xlabel("Actual daily trips")
    ax.set_ylabel("Predicted daily trips")
    ax.set_title("Actual vs predicted daily ridership (distributed lag model)")

    r2 = model.rsquared
    ax.text(
        0.05,
        0.95,
        f"R\u00b2 = {r2:.3f}",
        transform=ax.transAxes,
        fontsize=12,
        verticalalignment="top",
        bbox=dict(
            boxstyle="round,pad=0.4", facecolor="white", edgecolor="#cccccc", alpha=0.9
        ),
    )

    fig.tight_layout()
    path = OUTPUTS / "actual-vs-predicted.png"
    fig.savefig(path, dpi=150)
    print(f"Saved {path}")
    plt.close(fig)


def plot_weather_coefficients(model) -> None:
    snow_coefs = [model.params["total_snow_cm"]] + [
        model.params[f"snow_lag_{i}"] for i in range(1, MAX_LAG + 1)
    ]
    cumulative_snow = sum(snow_coefs)

    rain_ci = model.conf_int().loc["total_rain_mm"]
    temp_ci = model.conf_int().loc["temp_mean_c"]
    snow_ci = model.conf_int().loc["total_snow_cm"]

    variances = [0.0] * (MAX_LAG + 1)
    variances[0] = model.cov_params().loc["total_snow_cm", "total_snow_cm"]
    for i in range(1, MAX_LAG + 1):
        variances[i] = model.cov_params().loc[f"snow_lag_{i}", f"snow_lag_{i}"]

    cov_sums = np.zeros((MAX_LAG + 1, MAX_LAG + 1))
    params_snow = ["total_snow_cm"] + [f"snow_lag_{i}" for i in range(1, MAX_LAG + 1)]
    for i, pi in enumerate(params_snow):
        for j, pj in enumerate(params_snow):
            cov_sums[i, j] = model.cov_params().loc[pi, pj]
    cum_var = cov_sums.sum()
    cum_se = np.sqrt(cum_var)
    cum_ci_low = cumulative_snow - 1.96 * cum_se
    cum_ci_high = cumulative_snow + 1.96 * cum_se

    complaints_ci = model.conf_int().loc["complaints_311"]

    labels = [
        "Temperature\n(per \u00b0C)",
        "Rain\n(per mm)",
        "Same-day snow\n(per cm)",
        "311 complaints\n(per complaint)",
        "Cumulative snow\n(lag 0\u201314)",
    ]
    coefs = [
        model.params["temp_mean_c"],
        model.params["total_rain_mm"],
        model.params["total_snow_cm"],
        model.params["complaints_311"],
        cumulative_snow,
    ]
    ci_lows = [temp_ci[0], rain_ci[0], snow_ci[0], complaints_ci[0], cum_ci_low]
    ci_highs = [temp_ci[1], rain_ci[1], snow_ci[1], complaints_ci[1], cum_ci_high]

    fig, ax = plt.subplots(figsize=(9, 6))
    y_pos = np.arange(len(labels))
    errors_low = [c - lo for c, lo in zip(coefs, ci_lows)]
    errors_high = [hi - c for c, hi in zip(coefs, ci_highs)]

    colors = ["#e34a33", "#4a90d9", "#888888", "#d95f02", "#2171b5"]
    ax.barh(
        y_pos,
        coefs,
        xerr=[errors_low, errors_high],
        color=colors,
        edgecolor="#333333",
        linewidth=0.5,
        capsize=4,
        height=0.6,
    )
    ax.axvline(0, color="#666666", linewidth=0.8, linestyle="--")
    ax.set_yticks(y_pos)
    ax.set_yticklabels(labels)
    ax.set_xlabel("Change in daily trips")
    ax.set_title("Weather effects on daily ridership")

    fig.tight_layout()
    path = OUTPUTS / "weather-coefficients.png"
    fig.savefig(path, dpi=150)
    print(f"Saved {path}")
    plt.close(fig)


def plot_311_effects(model) -> None:
    lag_labels = ["same_day"] + [f"lag_{i}" for i in range(1, COMPLAINT_LAGS + 1)]
    coefs = [model.params["complaints_311"]] + [
        model.params[f"complaints_lag_{i}"] for i in range(1, COMPLAINT_LAGS + 1)
    ]
    ci_low = [model.conf_int().loc["complaints_311", 0]] + [
        model.conf_int().loc[f"complaints_lag_{i}", 0]
        for i in range(1, COMPLAINT_LAGS + 1)
    ]
    ci_high = [model.conf_int().loc["complaints_311", 1]] + [
        model.conf_int().loc[f"complaints_lag_{i}", 1]
        for i in range(1, COMPLAINT_LAGS + 1)
    ]
    p_values = [model.pvalues["complaints_311"]] + [
        model.pvalues[f"complaints_lag_{i}"] for i in range(1, COMPLAINT_LAGS + 1)
    ]

    x = list(range(len(lag_labels)))
    colors = ["#d95f02" if p < 0.05 else "#aaaaaa" for p in p_values]

    fig, ax = plt.subplots(figsize=(8, 5))
    for i in range(len(lag_labels)):
        ax.errorbar(
            x[i],
            coefs[i],
            yerr=[[coefs[i] - ci_low[i]], [ci_high[i] - coefs[i]]],
            fmt="o",
            color=colors[i],
            markersize=6,
            capsize=3,
            capthick=1,
            zorder=3,
        )

    ax.axhline(0, color="#666666", linewidth=0.8, linestyle="--")
    ax.set_xlabel("Lag (days)")
    ax.set_ylabel("Change in daily trips per complaint")
    ax.set_title("Effect of 311 bike-infrastructure complaints on ridership, by lag")
    ax.set_xticks(x)
    ax.set_xticklabels(lag_labels)

    fig.tight_layout()
    path = OUTPUTS / "311-lag-coefficients.png"
    fig.savefig(path, dpi=150)
    print(f"Saved {path}")
    plt.close(fig)


def save_regression_results(model) -> None:
    results = pd.DataFrame(
        {
            "coefficient": model.params,
            "std_err": model.bse,
            "t_value": model.tvalues,
            "p_value": model.pvalues,
        }
    )
    results.index.name = "variable"
    results.to_csv(OUTPUTS / "regression-results.csv")


def save_lag_summary(model) -> None:
    rows = []
    rows.append(
        {
            "lag": 0,
            "variable": "total_snow_cm",
            "coefficient": model.params["total_snow_cm"],
            "ci_low": model.conf_int().loc["total_snow_cm", 0],
            "ci_high": model.conf_int().loc["total_snow_cm", 1],
            "p_value": model.pvalues["total_snow_cm"],
        }
    )
    for i in range(1, MAX_LAG + 1):
        var = f"snow_lag_{i}"
        rows.append(
            {
                "lag": i,
                "variable": var,
                "coefficient": model.params[var],
                "ci_low": model.conf_int().loc[var, 0],
                "ci_high": model.conf_int().loc[var, 1],
                "p_value": model.pvalues[var],
            }
        )
    pd.DataFrame(rows).to_csv(OUTPUTS / "lag-summary.csv", index=False)


def save_311_lag_summary(model) -> None:
    rows = []
    rows.append(
        {
            "lag": 0,
            "variable": "complaints_311",
            "coefficient": model.params["complaints_311"],
            "ci_low": model.conf_int().loc["complaints_311", 0],
            "ci_high": model.conf_int().loc["complaints_311", 1],
            "p_value": model.pvalues["complaints_311"],
        }
    )
    for i in range(1, COMPLAINT_LAGS + 1):
        var = f"complaints_lag_{i}"
        rows.append(
            {
                "lag": i,
                "variable": var,
                "coefficient": model.params[var],
                "ci_low": model.conf_int().loc[var, 0],
                "ci_high": model.conf_int().loc[var, 1],
                "p_value": model.pvalues[var],
            }
        )
    pd.DataFrame(rows).to_csv(OUTPUTS / "311-lag-summary.csv", index=False)


def main() -> int:
    print("Loading merged weather-ridership data...", file=sys.stderr)
    df = load_merged_data()
    print(f"  Loaded {len(df)} days", file=sys.stderr)

    print("Merging snow-on-ground data...", file=sys.stderr)
    snow_grnd = load_snow_on_ground()
    df = pd.merge(df, snow_grnd, on="date", how="left")
    if "snow_on_grnd_cm" in df.columns:
        df["snow_on_grnd_cm"] = df["snow_on_grnd_cm"].fillna(0.0)

    print("Building features (lags, dummies)...", file=sys.stderr)
    df = build_features(df)
    print(f"  {len(df)} rows after dropping NaN from lags", file=sys.stderr)

    print("Running OLS regression...", file=sys.stderr)
    model = run_regression(df)
    print(model.summary(), file=sys.stderr)

    print("Saving outputs...", file=sys.stderr)
    save_regression_results(model)
    save_lag_summary(model)
    save_311_lag_summary(model)

    print("Generating figures...", file=sys.stderr)
    plot_lag_coefficients(model)
    plot_cumulative_effect(model)
    plot_actual_vs_predicted(model, df)
    plot_weather_coefficients(model)
    plot_311_effects(model)

    print("Done.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
