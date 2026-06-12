import re
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parents[3]
RAW_DIR = REPO_ROOT / "datasets" / "ttc-bus-delay" / "raw"
OUTPUT_DIR = Path(__file__).resolve().parent / "outputs"

CATEGORY_MAP = {
    "E": "Equipment",
    "M": "Operations",
    "P": "Infrastructure",
    "S": "Safety/Security",
    "T": "Transportation",
}


def load_data():
    delay_df = pd.read_csv(
        RAW_DIR / "ttc-bus-delay-data-since-2025.csv", parse_dates=["Date"]
    )
    codes_df = pd.read_csv(RAW_DIR / "ttc-bus-delay-codes.csv")
    delay_df["Date"] = pd.to_datetime(delay_df["Date"])
    return delay_df, codes_df


def extract_route_number(line_val):
    if pd.isna(line_val):
        return None
    match = re.match(r"(\d+)", str(line_val).strip())
    return int(match.group(1)) if match else None


def classify_code(code_val):
    if pd.isna(code_val) or str(code_val).strip() == "":
        return "Other"
    first_letter = str(code_val).strip()[0].upper()
    return CATEGORY_MAP.get(first_letter, "Other")


def prepare_data(delay_df, codes_df):
    df = delay_df.copy()
    df = df[df["Date"].dt.year == 2025].copy()
    df["Line"] = df["Line"].fillna("Unknown")
    df["category"] = df["Code"].apply(classify_code)
    codes_lookup = dict(zip(codes_df["CODE"], codes_df["DESCRIPTION"]))
    df["code_description"] = df["Code"].map(codes_lookup)
    df["is_significant"] = df["Min Delay"] >= 5
    n_unknown = (df["Line"] == "Unknown").sum()
    if n_unknown > 0:
        print(f"Note: {n_unknown} rows have NaN Line, grouped as 'Unknown'")
    return df


def build_route_summary(df):
    total_events = df.groupby("Line").size().rename("total_events")
    sig = df[df["is_significant"]].copy()
    sig_no_zero = sig[sig["Min Delay"] > 0]
    delay_stats = sig_no_zero.groupby("Line")["Min Delay"].agg(
        total_delay_min="sum",
        mean_delay_min="mean",
        median_delay_min="median",
    )
    significant_counts = sig.groupby("Line").size().rename("significant_delays")
    cat_pcts = []
    for cat_name in CATEGORY_MAP.values():
        pct = (
            sig_no_zero[sig_no_zero["category"] == cat_name]
            .groupby("Line")["Min Delay"]
            .sum()
            .div(delay_stats["total_delay_min"])
            .fillna(0)
            .rename(f"pct_{cat_name.lower()}")
        )
        cat_pcts.append(pct)
    summary = pd.concat(
        [total_events, significant_counts, delay_stats] + cat_pcts, axis=1
    ).fillna(0)
    summary = summary.sort_values("total_delay_min", ascending=False)
    summary.index.name = "route"
    summary = summary.reset_index()
    return summary


def build_cause_breakdown(df):
    sig_no_zero = df[(df["is_significant"]) & (df["Min Delay"] > 0)].copy()
    breakdown = (
        sig_no_zero.groupby(["Line", "category"])
        .agg(
            count=("Min Delay", "size"),
            total_delay_min=("Min Delay", "sum"),
            mean_delay_min=("Min Delay", "mean"),
        )
        .reset_index()
    )
    breakdown = breakdown.rename(columns={"Line": "route", "category": "category"})
    breakdown = breakdown.sort_values(["total_delay_min"], ascending=False).reset_index(
        drop=True
    )
    return breakdown


def plot_top_routes_by_delay(summary, top_n=20):
    top = summary.head(top_n).copy()
    top = top.iloc[::-1]
    top_cause = []
    for _, row in top.iterrows():
        cats = {
            "Equipment": row.get("pct_equipment", 0),
            "Operations": row.get("pct_operations", 0),
            "Infrastructure": row.get("pct_infrastructure", 0),
            "Safety": row.get("pct_safety", 0),
            "Transportation": row.get("pct_transportation", 0),
        }
        top_cause.append(max(cats, key=cats.get))
    top["dominant_cause"] = top_cause
    palette = {
        "Equipment": "#e74c3c",
        "Operations": "#3498db",
        "Infrastructure": "#2ecc71",
        "Safety": "#f39c12",
        "Transportation": "#9b59b6",
    }
    fig, ax = plt.subplots(figsize=(12, 9))
    colors = top["dominant_cause"].map(palette)
    ax.barh(
        top["route"],
        top["total_delay_min"],
        color=colors,
        edgecolor="white",
        linewidth=0.5,
    )
    from matplotlib.patches import Patch

    legend_elements = [Patch(facecolor=v, label=k) for k, v in palette.items()]
    ax.legend(
        handles=legend_elements,
        title="Dominant cause category",
        loc="lower right",
        fontsize=9,
    )
    ax.set_xlabel("Total delay minutes (≥5 min delays, excl. Min Delay == 0)")
    ax.set_title("TTC Bus 2025: Top 20 routes by total delay minutes (≥5 min delays)")
    ax.tick_params(axis="y", labelsize=8)
    plt.tight_layout()
    fig.savefig(OUTPUT_DIR / "top-routes-by-delay.png", dpi=150)
    plt.close(fig)


def plot_route_cause_breakdown(summary, breakdown, top_n=15):
    top_routes = summary.head(top_n)["route"].tolist()
    bd = breakdown[breakdown["route"].isin(top_routes)].copy()
    route_order = summary.head(top_n)["route"].tolist()
    bd["route"] = pd.Categorical(bd["route"], categories=route_order, ordered=True)
    bd = bd.sort_values("route")
    bd_pivot = bd.pivot_table(
        index="route",
        columns="category",
        values="total_delay_min",
        fill_value=0,
        observed=False,
    )
    bd_pivot = bd_pivot.reindex(route_order)
    bd_pivot = bd_pivot.iloc[::-1]
    palette = {
        "Equipment": "#e74c3c",
        "Operations": "#3498db",
        "Infrastructure": "#2ecc71",
        "Safety": "#f39c12",
        "Transportation": "#9b59b6",
    }
    fig, ax = plt.subplots(figsize=(12, 9))
    categories = [c for c in palette if c in bd_pivot.columns]
    left = pd.Series(0, index=bd_pivot.index)
    for cat in categories:
        if cat in bd_pivot.columns:
            vals = bd_pivot[cat]
            ax.barh(
                bd_pivot.index,
                vals,
                left=left,
                color=palette[cat],
                label=cat,
                edgecolor="white",
                linewidth=0.5,
            )
            left = left + vals.fillna(0)
    ax.set_xlabel("Total delay minutes (≥5 min delays, excl. Min Delay == 0)")
    ax.set_title("TTC Bus 2025: What causes delays on the worst routes?")
    ax.legend(title="Cause category", loc="lower right", fontsize=9)
    ax.tick_params(axis="y", labelsize=8)
    plt.tight_layout()
    fig.savefig(OUTPUT_DIR / "route-cause-breakdown.png", dpi=150)
    plt.close(fig)


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    delay_df, codes_df = load_data()
    df = prepare_data(delay_df, codes_df)
    summary = build_route_summary(df)
    breakdown = build_cause_breakdown(df)
    summary.to_csv(OUTPUT_DIR / "route-delay-summary.csv", index=False)
    breakdown.to_csv(OUTPUT_DIR / "route-cause-breakdown.csv", index=False)
    plot_top_routes_by_delay(summary)
    plot_route_cause_breakdown(summary, breakdown)
    print("=== Top 10 routes by total delay minutes ===")
    print(summary.head(10)[["route", "total_delay_min"]].to_string(index=False))
    print("\n=== Total significant delays in 2025 ===")
    print(summary["significant_delays"].astype(int).sum())
    print("\n=== Number of unique routes ===")
    print(df["Line"].nunique())
    print("\n=== Category breakdown (total delay minutes) ===")
    sig_no_zero = df[(df["is_significant"]) & (df["Min Delay"] > 0)]
    cat_breakdown = (
        sig_no_zero.groupby("category")["Min Delay"].sum().sort_values(ascending=False)
    )
    for cat, val in cat_breakdown.items():
        print(f"  {cat}: {val:,.0f} min")


if __name__ == "__main__":
    main()
