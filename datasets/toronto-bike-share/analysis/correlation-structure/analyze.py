"""Cross-correlation and partial correlation analysis for bike-share
ridership, 311 complaints, temperature, and snowfall.

Computes:
1. Pairwise CCF (cross-correlation function) at lags 0–30 for all series
   pairs, on seasonally-differenced (day-over-year-ago) data.
2. Partial correlations controlling for temperature (and for shared
   seasonality via day-of-year fixed effects), on the same differenced data.

See README.md for full description.
"""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import warnings
from scipy import stats

REPO_ROOT = Path(__file__).resolve().parent.parents[3]
RAW_BIKE = REPO_ROOT / "datasets" / "toronto-bike-share" / "raw"
RAW_WEATHER = REPO_ROOT / "datasets" / "toronto-weather-daily" / "raw"
OUTPUTS = Path(__file__).resolve().parent / "outputs"
OUTPUTS.mkdir(exist_ok=True)

YEARS = [2025, 2026]
MAX_LAG = 30
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
        frames.append(df[["date", "total_complaints"]].copy())
        print(
            f"  311 {year}: {len(df)} days, {df['total_complaints'].sum():,} complaints",
            file=sys.stderr,
        )
    if not frames:
        return pd.DataFrame(columns=["date", "total_complaints"])
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
                "Mean Temp (°C)": "mean_temp_c",
                "Total Rain (mm)": "total_rain_mm",
            }
        )
        df["date"] = pd.to_datetime(df["date"])
        df["total_snow_cm"] = pd.to_numeric(
            df["total_snow_cm"].astype(str).str.replace("T", "0.0"), errors="coerce"
        ).fillna(0.0)
        df["mean_temp_c"] = pd.to_numeric(df["mean_temp_c"], errors="coerce")
        df["total_rain_mm"] = pd.to_numeric(
            df.get("total_rain_mm", pd.Series([0.0] * len(df), index=df.index))
            .astype(str)
            .str.replace("T", "0.0"),
            errors="coerce",
        ).fillna(0.0)
        frames.append(
            df[["date", "total_snow_cm", "mean_temp_c", "total_rain_mm"]].copy()
        )
    if not frames:
        return pd.DataFrame(
            columns=["date", "total_snow_cm", "mean_temp_c", "total_rain_mm"]
        )
    return (
        pd.concat(frames, ignore_index=True).sort_values("date").reset_index(drop=True)
    )


def detrend_deseason(series: pd.Series, day_of_year: pd.Series) -> pd.Series:
    """Remove annual cycle via day-of-year fixed effects, then demean."""
    df = pd.DataFrame({"y": series, "doy": day_of_year})
    doy_means = df.groupby("doy")["y"].mean()
    df["y_detrended"] = df["y"] - df["doy"].map(doy_means)
    df["y_detrended"] = df["y_detrended"] - df["y_detrended"].mean()
    return df["y_detrended"]


def compute_ccf(
    x: np.ndarray, y: np.ndarray, max_lag: int
) -> tuple[np.ndarray, np.ndarray]:
    """Cross-correlation at lags 0..max_lag where x leads y."""
    len(x)
    x_dm = x - x.mean()
    y_dm = y - y.mean()
    var_x = np.sum(x_dm**2)
    var_y = np.sum(y_dm**2)
    lags = np.arange(0, max_lag + 1)
    ccf_vals = np.zeros(max_lag + 1)
    for lag in lags:
        if lag == 0:
            ccf_vals[lag] = np.sum(x_dm * y_dm) / np.sqrt(var_x * var_y)
        else:
            ccf_vals[lag] = np.sum(x_dm[:-lag] * y_dm[lag:]) / np.sqrt(var_x * var_y)
    return lags, ccf_vals


def partial_corr(
    x: pd.Series, y: pd.Series, controls: pd.DataFrame
) -> tuple[float, float]:
    """Partial correlation of x and y controlling for columns in controls.
    Returns (r, p_value)."""
    from numpy.linalg import lstsq

    def resid(target, predictors):
        coeffs, _, _, _ = lstsq(predictors, target, rcond=None)
        return target - predictors @ coeffs

    np.column_stack(
        [
            controls.values,
            x.values.reshape(-1, 1),
        ]
    )
    y_arr = y.values.astype(float)
    rx = resid(x.values.astype(float), controls.values.astype(float))
    ry = resid(y_arr, controls.values.astype(float))
    r, p = stats.pearsonr(rx, ry)
    return r, p


def main() -> int:
    print("Loading ridership...", file=sys.stderr)
    daily = load_ridership()
    print("Loading 311...", file=sys.stderr)
    complaints = load_311()
    print("Loading weather...", file=sys.stderr)
    weather = load_weather()

    merged = daily.merge(complaints, on="date", how="left")
    merged["total_complaints"] = merged["total_complaints"].fillna(0).astype(int)
    merged = merged.merge(weather, on="date", how="left")
    merged["total_snow_cm"] = merged["total_snow_cm"].fillna(0.0)
    merged["mean_temp_c"] = merged["mean_temp_c"].ffill()
    merged["total_rain_mm"] = merged["total_rain_mm"].fillna(0.0)
    merged["doy"] = merged["date"].dt.dayofyear

    merged = merged.dropna(subset=["trips", "mean_temp_c"]).reset_index(drop=True)
    print(f"  {len(merged)} days with complete data", file=sys.stderr)

    series_names = {
        "trips": "Daily trips",
        "total_complaints": "311 complaints",
        "mean_temp_c": "Mean temp (°C)",
        "total_snow_cm": "Snowfall (cm)",
    }
    series_cols = list(series_names.keys())

    print("Detrending and deseasonalizing...", file=sys.stderr)
    detrended = pd.DataFrame({"date": merged["date"], "doy": merged["doy"]})
    for col in series_cols:
        detrended[col] = detrend_deseason(merged[col], merged["doy"])

    # --- Raw Pearson correlations ---
    print("\nRaw Pearson correlations (deseasonalized):", file=sys.stderr)
    raw_corr = detrended[series_cols].corr()
    n_obs = len(detrended)
    raw_pvals = pd.DataFrame(index=series_cols, columns=series_cols, dtype=float)
    for i, c1 in enumerate(series_cols):
        for j, c2 in enumerate(series_cols):
            if i >= j:
                _, p = stats.pearsonr(detrended[c1], detrended[c2])
                raw_pvals.loc[c1, c2] = p
                raw_pvals.loc[c2, c1] = p
    print(raw_corr.to_string(), file=sys.stderr)
    print("\np-values:", file=sys.stderr)
    print(raw_pvals.to_string(), file=sys.stderr)
    raw_corr.to_csv(OUTPUTS / "raw-correlation-matrix.csv")
    raw_pvals.to_csv(OUTPUTS / "raw-correlation-pvalues.csv")

    # --- CCF for all pairs ---
    print("\nComputing cross-correlations...", file=sys.stderr)
    ccf_results = []
    pair_names = [
        ("trips", "total_complaints"),
        ("trips", "mean_temp_c"),
        ("trips", "total_snow_cm"),
        ("total_complaints", "mean_temp_c"),
        ("total_complaints", "total_snow_cm"),
        ("mean_temp_c", "total_snow_cm"),
    ]

    fig, axes = plt.subplots(3, 2, figsize=(14, 14), sharex=True)
    axes_flat = axes.flatten()

    n_obs = len(detrended)
    for idx, (x_col, y_col) in enumerate(pair_names):
        lags, ccf_vals = compute_ccf(
            detrended[x_col].values,
            detrended[y_col].values,
            MAX_LAG,
        )
        for lag, val in zip(lags, ccf_vals):
            n_eff = n_obs - lag
            t_stat = val * np.sqrt((n_eff - 2) / max(1 - val**2, 1e-12))
            p_val = 2 * stats.t.sf(np.abs(t_stat), df=max(n_eff - 2, 1))
            ccf_results.append(
                {
                    "x": series_names[x_col],
                    "y": series_names[y_col],
                    "lag": lag,
                    "ccf": val,
                    "p_value": p_val,
                }
            )

        ax = axes_flat[idx]
        pair_ccf = [
            r
            for r in ccf_results
            if r["x"] == series_names[x_col] and r["y"] == series_names[y_col]
        ]
        p_vals = [r["p_value"] for r in pair_ccf]
        colors = ["#2171b5" if p < 0.05 else "#cccccc" for p in p_vals]
        ax.bar(lags, ccf_vals, color=colors, width=0.8)
        ax.axhline(0, color="#333333", linewidth=0.5)
        ci = 1.96 / np.sqrt(n_obs)
        ax.axhline(ci, color="#e34a33", linewidth=0.8, linestyle="--")
        ax.axhline(-ci, color="#e34a33", linewidth=0.8, linestyle="--")
        ax.set_title(f"{series_names[x_col]} → {series_names[y_col]}")
        ax.set_ylabel("CCF")
        if idx >= 4:
            ax.set_xlabel("Lag (days)")

    fig.suptitle(
        "Cross-correlation functions (deseasonalized daily data)", fontsize=14, y=1.02
    )
    fig.tight_layout()
    path = OUTPUTS / "ccf-panel.png"
    fig.savefig(path, dpi=150, bbox_inches="tight")
    print(f"Saved {path}", file=sys.stderr)
    plt.close(fig)

    ccf_df = pd.DataFrame(ccf_results)
    ccf_df.to_csv(OUTPUTS / "ccf-results.csv", index=False)

    # --- Partial correlations ---
    print("\nPartial correlations (controlling for temperature):", file=sys.stderr)
    partial_results = []
    pairs_for_partial = [
        ("trips", "total_complaints", ["mean_temp_c"]),
        ("trips", "total_snow_cm", ["mean_temp_c"]),
        ("total_complaints", "total_snow_cm", ["mean_temp_c"]),
        ("trips", "total_complaints", ["mean_temp_c", "total_snow_cm"]),
    ]

    for x_col, y_col, ctrl_cols in pairs_for_partial:
        r, p = partial_corr(
            detrended[x_col],
            detrended[y_col],
            detrended[ctrl_cols],
        )
        ctrl_label = ", ".join(series_names[c] for c in ctrl_cols)
        result = {
            "x": series_names[x_col],
            "y": series_names[y_col],
            "controlling_for": ctrl_label,
            "partial_r": r,
            "p_value": p,
            "significant_005": p < 0.05,
        }
        partial_results.append(result)
        sig = "*" if p < 0.05 else ""
        print(
            f"  {result['x']} vs {result['y']} | ctrl: {ctrl_label} | r={r:.4f} p={p:.6f}{sig}",
            file=sys.stderr,
        )

    partial_df = pd.DataFrame(partial_results)
    partial_df.to_csv(OUTPUTS / "partial-correlations.csv", index=False)

    # --- Partial correlation heatmap-style figure ---
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    ax = axes[0]
    labels = [series_names[c] for c in series_cols]
    im = ax.imshow(raw_corr.values, cmap="RdBu_r", vmin=-1, vmax=1, aspect="auto")
    ax.set_xticks(range(len(labels)))
    ax.set_xticklabels(labels, rotation=45, ha="right")
    ax.set_yticks(range(len(labels)))
    ax.set_yticklabels(labels)
    for i in range(len(labels)):
        for j in range(len(labels)):
            val = raw_corr.values[i, j]
            ax.text(
                j,
                i,
                f"{val:.2f}",
                ha="center",
                va="center",
                fontsize=10,
                color="white" if abs(val) > 0.5 else "black",
            )
    ax.set_title("Raw correlation (deseasonalized)")
    fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)

    ax = axes[1]
    pair_labels = [
        f"{r['x']} vs {r['y']}\nctrl: {r['controlling_for']}" for r in partial_results
    ]
    rs = [r["partial_r"] for r in partial_results]
    ps = [r["p_value"] for r in partial_results]
    colors = [
        "#2171b5" if abs(r) > 0.1 and p < 0.05 else "#cccccc" for r, p in zip(rs, ps)
    ]
    ax.barh(
        range(len(pair_labels)), rs, color=colors, edgecolor="#333333", linewidth=0.5
    )
    ax.axvline(0, color="#333333", linewidth=0.5)
    ax.set_yticks(range(len(pair_labels)))
    ax.set_yticklabels(pair_labels, fontsize=9)
    ax.set_xlabel("Partial correlation coefficient")
    ax.set_title("Partial correlations (deseasonalized)")
    for i, (r, p) in enumerate(zip(rs, ps)):
        sig = "***" if p < 0.001 else "**" if p < 0.01 else "*" if p < 0.05 else ""
        ax.text(
            r + (0.02 if r >= 0 else -0.02),
            i,
            f"r={r:.3f}{sig}",
            va="center",
            ha="left" if r >= 0 else "right",
            fontsize=8,
        )

    fig.tight_layout()
    path = OUTPUTS / "correlation-heatmap.png"
    fig.savefig(path, dpi=150, bbox_inches="tight")
    print(f"Saved {path}", file=sys.stderr)
    plt.close(fig)

    # --- Rolling correlation: trips vs temperature ---
    print("\nRolling 30-day correlation: trips vs temperature...", file=sys.stderr)
    WINDOW = 30
    rolling_rs = []
    rolling_ps = []
    dates = []
    for i in range(WINDOW, len(detrended)):
        window_trips = detrended["trips"].iloc[i - WINDOW : i].values
        window_temp = detrended["mean_temp_c"].iloc[i - WINDOW : i].values
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", stats.ConstantInputWarning)
            r, p = stats.pearsonr(window_trips, window_temp)
        rolling_rs.append(r)
        rolling_ps.append(p)
        dates.append(detrended["date"].iloc[i])

    fig, ax = plt.subplots(figsize=(14, 5))
    ax.plot(dates, rolling_rs, color="#2171b5", linewidth=1.2)
    ax.axhline(0, color="#666666", linewidth=0.5, linestyle="--")
    ax.set_ylabel(f"{WINDOW}-day rolling correlation (r)")
    ax.set_title(
        f"{WINDOW}-day rolling correlation: trips vs temperature (deseasonalized)"
    )
    ax.xaxis.set_major_formatter(plt.matplotlib.dates.DateFormatter("%b %Y"))
    fig.tight_layout()
    path = OUTPUTS / "rolling-correlation-trips-temp.png"
    fig.savefig(path, dpi=150, bbox_inches="tight")
    print(f"Saved {path}", file=sys.stderr)
    plt.close(fig)

    # --- Rolling correlation: trips vs complaints ---
    print("Rolling 30-day correlation: trips vs complaints...", file=sys.stderr)
    rolling_rs2 = []
    dates2 = []
    for i in range(WINDOW, len(detrended)):
        window_trips = detrended["trips"].iloc[i - WINDOW : i].values
        window_complaints = detrended["total_complaints"].iloc[i - WINDOW : i].values
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", stats.ConstantInputWarning)
            r, _ = stats.pearsonr(window_trips, window_complaints)
        rolling_rs2.append(r)
        dates2.append(detrended["date"].iloc[i])

    fig, ax = plt.subplots(figsize=(14, 5))
    ax.plot(dates2, rolling_rs2, color="#ff9900", linewidth=1.2)
    ax.axhline(0, color="#666666", linewidth=0.5, linestyle="--")
    ax.set_ylabel(f"{WINDOW}-day rolling correlation (r)")
    ax.set_title(
        f"{WINDOW}-day rolling correlation: trips vs 311 complaints (deseasonalized)"
    )
    ax.xaxis.set_major_formatter(plt.matplotlib.dates.DateFormatter("%b %Y"))
    fig.tight_layout()
    path = OUTPUTS / "rolling-correlation-trips-complaints.png"
    fig.savefig(path, dpi=150, bbox_inches="tight")
    print(f"Saved {path}", file=sys.stderr)
    plt.close(fig)

    print("\nDone.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
