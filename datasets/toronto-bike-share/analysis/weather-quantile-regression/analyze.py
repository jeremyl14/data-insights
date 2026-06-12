"""Quantile regression: how temperature, rain, and snow affect bike-share
ridership at different points in the distribution (low, median, high days).

Fits quantile regression at tau = 0.25, 0.5, 0.75 using the same
distributed-lag specification as the OLS weather-lag-regression analysis.
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
OUTPUTS = SCRIPT_DIR / "outputs"
OUTPUTS.mkdir(exist_ok=True)

MAX_LAG = 14
QUANTILES = [0.25, 0.5, 0.75]


def load_merged_data() -> pd.DataFrame:
    merged = pd.read_csv(WEATHER_RIDERSHIP_DIR / "weather-ridership-2025.csv")
    merged["date"] = pd.to_datetime(merged["date"])
    return merged


def load_snow_on_ground() -> pd.DataFrame:
    if not WEATHER_RAW.exists():
        print(f"ERROR: Weather data not found at {WEATHER_RAW}", file=sys.stderr)
        sys.exit(1)
    df = pd.read_csv(WEATHER_RAW)
    df.columns = [c.strip() for c in df.columns]
    df = df.rename(
        columns={"Date/Time": "date", "Snow on Grnd (cm)": "snow_on_grnd_cm"}
    )
    df["date"] = pd.to_datetime(df["date"])
    if "snow_on_grnd_cm" in df.columns:
        df["snow_on_grnd_cm"] = pd.to_numeric(
            df["snow_on_grnd_cm"].astype(str).str.replace("T", "0.0"), errors="coerce"
        ).fillna(0.0)
        return df[["date", "snow_on_grnd_cm"]].copy()
    return pd.DataFrame({"date": pd.to_datetime(df["date"]), "snow_on_grnd_cm": 0.0})


def build_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy().sort_values("date").reset_index(drop=True)
    for lag in range(1, MAX_LAG + 1):
        df[f"snow_lag_{lag}"] = df["total_snow_cm"].shift(lag)
    df["day_of_week"] = df["date"].dt.dayofweek
    df["month"] = df["date"].dt.month
    df = df.dropna().reset_index(drop=True)
    return df


def build_exog(df: pd.DataFrame) -> pd.DataFrame:
    exog_cols = ["total_rain_mm", "total_snow_cm", "temp_mean_c"]
    for lag in range(1, MAX_LAG + 1):
        exog_cols.append(f"snow_lag_{lag}")
    dow_dummies = pd.get_dummies(
        df["day_of_week"], prefix="dow", drop_first=True
    ).astype(float)
    month_dummies = pd.get_dummies(df["month"], prefix="month", drop_first=True).astype(
        float
    )
    exog = pd.concat([df[exog_cols].astype(float), dow_dummies, month_dummies], axis=1)
    return sm.add_constant(exog)


def run_quantile_regression(y: pd.Series, exog: pd.DataFrame, tau: float):
    model = sm.QuantReg(y, exog).fit(q=tau, max_iter=5000)
    return model


def plot_weather_by_quantile(results: dict[float, sm.QuantRegResults]) -> None:
    vars_of_interest = {
        "temp_mean_c": ("Temperature (per \u00b0C)", "#e34a33"),
        "total_rain_mm": ("Rain (per mm)", "#4a90d9"),
        "total_snow_cm": ("Same-day snow (per cm)", "#888888"),
    }
    rows = []
    for tau, model in results.items():
        for var, (label, _) in vars_of_interest.items():
            ci = model.conf_int().loc[var]
            rows.append(
                {
                    "quantile": tau,
                    "variable": label,
                    "coefficient": model.params[var],
                    "ci_low": ci[0],
                    "ci_high": ci[1],
                    "p_value": model.pvalues[var],
                }
            )
    df_plot = pd.DataFrame(rows)

    fig, axes = plt.subplots(1, 3, figsize=(14, 5), sharey=False)
    for ax, (var, (label, base_color)) in zip(axes, vars_of_interest.items()):
        sub = df_plot[df_plot["variable"] == label]
        x = sub["quantile"].values
        y = sub["coefficient"].values
        err_low = y - sub["ci_low"].values
        err_high = sub["ci_high"].values - y
        colors = [base_color if p < 0.05 else "#cccccc" for p in sub["p_value"]]
        ax.errorbar(
            x,
            y,
            yerr=[err_low, err_high],
            fmt="o-",
            color=base_color,
            markersize=7,
            capsize=4,
            linewidth=1.5,
            zorder=3,
        )
        for i, (xi, yi, c) in enumerate(zip(x, y, colors)):
            ax.plot(xi, yi, "o", color=c, markersize=8, zorder=4)
        ax.axhline(0, color="#999999", linewidth=0.8, linestyle="--")
        ax.set_xlabel("Quantile")
        ax.set_title(label, fontsize=10)
        ax.set_xticks(QUANTILES)
        ax.set_xticklabels(["Q25", "Q50", "Q75"])

    fig.suptitle(
        "Weather effects on ridership by quantile\n(filled = significant at p < 0.05, open = not significant)",
        fontsize=11,
        y=1.02,
    )
    fig.tight_layout()
    path = OUTPUTS / "quantile-weather-effects.png"
    fig.savefig(path, dpi=150, bbox_inches="tight")
    print(f"Saved {path}")
    plt.close(fig)


def plot_snow_lags_by_quantile(results: dict[float, sm.QuantRegResults]) -> None:
    lag_labels = ["lag_0"] + [f"lag_{i}" for i in range(1, MAX_LAG + 1)]
    var_names = ["total_snow_cm"] + [f"snow_lag_{i}" for i in range(1, MAX_LAG + 1)]
    x = list(range(len(lag_labels)))

    palette = {0.25: "#4a90d9", 0.5: "#333333", 0.75: "#e34a33"}

    fig, ax = plt.subplots(figsize=(12, 6))
    for tau, model in results.items():
        coefs = [model.params[v] for v in var_names]
        ci_lows = [model.conf_int().loc[v, 0] for v in var_names]
        ci_highs = [model.conf_int().loc[v, 1] for v in var_names]
        err_low = [c - lo for c, lo in zip(coefs, ci_lows)]
        err_high = [hi - c for c, hi in zip(coefs, ci_highs)]
        ax.errorbar(
            x,
            coefs,
            yerr=[err_low, err_high],
            fmt="o-",
            color=palette[tau],
            markersize=5,
            capsize=3,
            linewidth=1.2,
            label=f"Q{int(tau * 100)}",
            alpha=0.85,
            zorder=3,
        )

    ax.axhline(0, color="#999999", linewidth=0.8, linestyle="--")
    ax.set_xlabel("Days after snowfall")
    ax.set_ylabel("Change in daily trips per 1 cm snow")
    ax.set_title("Snow lag effects by quantile")
    ax.set_xticks(x)
    ax.set_xticklabels([str(i) for i in x])
    ax.legend(frameon=False, fontsize=10)

    fig.tight_layout()
    path = OUTPUTS / "quantile-snow-lags.png"
    fig.savefig(path, dpi=150)
    print(f"Saved {path}")
    plt.close(fig)


def plot_cumulative_snow_by_quantile(results: dict[float, sm.QuantRegResults]) -> None:
    var_names = ["total_snow_cm"] + [f"snow_lag_{i}" for i in range(1, MAX_LAG + 1)]
    x = list(range(MAX_LAG + 1))
    palette = {0.25: "#4a90d9", 0.5: "#333333", 0.75: "#e34a33"}

    fig, ax = plt.subplots(figsize=(10, 6))
    for tau, model in results.items():
        coefs = [model.params[v] for v in var_names]
        cumulative = np.cumsum(coefs)
        ax.step(
            x,
            cumulative,
            where="mid",
            color=palette[tau],
            linewidth=1.8,
            label=f"Q{int(tau * 100)}",
            zorder=3,
        )

    ax.axhline(0, color="#999999", linewidth=0.8, linestyle="--")
    ax.set_xlabel("Days after snowfall (cumulative)")
    ax.set_ylabel("Cumulative trip reduction per 1 cm snow")
    ax.set_title("Cumulative snow effect by quantile")
    ax.set_xticks(x)
    ax.legend(frameon=False, fontsize=10)

    fig.tight_layout()
    path = OUTPUTS / "quantile-cumulative-snow.png"
    fig.savefig(path, dpi=150)
    print(f"Saved {path}")
    plt.close(fig)


def save_results(results: dict[float, sm.QuantRegResults]) -> None:
    rows = []
    for tau, model in results.items():
        for var in model.params.index:
            ci = model.conf_int().loc[var]
            rows.append(
                {
                    "quantile": tau,
                    "variable": var,
                    "coefficient": model.params[var],
                    "ci_low": ci[0],
                    "ci_high": ci[1],
                    "p_value": model.pvalues[var],
                }
            )
    df_results = pd.DataFrame(rows)
    df_results.to_csv(OUTPUTS / "quantile-coefficients.csv", index=False)

    summary_rows = []
    vars_key = ["temp_mean_c", "total_rain_mm", "total_snow_cm"]
    for tau, model in results.items():
        row = {"quantile": tau, "pseudo_r2": model.prsquared}
        snow_coefs = [model.params["total_snow_cm"]] + [
            model.params[f"snow_lag_{i}"] for i in range(1, MAX_LAG + 1)
        ]
        row["cumulative_snow"] = sum(snow_coefs)
        for v in vars_key:
            row[f"{v}_coef"] = model.params[v]
            row[f"{v}_p"] = model.pvalues[v]
        summary_rows.append(row)
    pd.DataFrame(summary_rows).to_csv(OUTPUTS / "summary.csv", index=False)


def main() -> int:
    print("Loading merged weather-ridership data...", file=sys.stderr)
    df = load_merged_data()
    print(f"  Loaded {len(df)} days", file=sys.stderr)

    print("Merging snow-on-ground data...", file=sys.stderr)
    snow_grnd = load_snow_on_ground()
    df = pd.merge(df, snow_grnd, on="date", how="left")
    if "snow_on_grnd_cm" in df.columns:
        df["snow_on_grnd_cm"] = df["snow_on_grnd_cm"].fillna(0.0)

    print("Building features...", file=sys.stderr)
    df = build_features(df)
    print(f"  {len(df)} rows after lag trimming", file=sys.stderr)

    exog = build_exog(df)
    y = df["ridership"].astype(float)

    results = {}
    for tau in QUANTILES:
        print(f"Fitting quantile regression at tau={tau}...", file=sys.stderr)
        model = run_quantile_regression(y, exog, tau)
        results[tau] = model
        print(f"  Pseudo R² = {model.prsquared:.3f}", file=sys.stderr)
        temp_coef = model.params["temp_mean_c"]
        rain_coef = model.params["total_rain_mm"]
        snow_coef = model.params["total_snow_cm"]
        print(
            f"  Temp: {temp_coef:+.0f}, Rain: {rain_coef:+.0f}, Snow: {snow_coef:+.0f}",
            file=sys.stderr,
        )

    save_results(results)
    plot_weather_by_quantile(results)
    plot_snow_lags_by_quantile(results)
    plot_cumulative_snow_by_quantile(results)

    print("Done.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
