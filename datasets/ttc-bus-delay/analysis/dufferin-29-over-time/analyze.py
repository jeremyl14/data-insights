from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

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
    return delay_df, codes_df


def classify_code(code_val):
    if pd.isna(code_val) or str(code_val).strip() == "":
        return "Other"
    first_letter = str(code_val).strip()[0].upper()
    return CATEGORY_MAP.get(first_letter, "Other")


def filter_route_29(df):
    df = df.copy()
    df["Line"] = df["Line"].fillna("Unknown")
    mask = (
        df["Line"].str.startswith("29 ")
        | df["Line"].str.startswith("29C ")
        | df["Line"].str.startswith("929 ")
        | (df["Line"] == "29")
        | (df["Line"] == "929")
    )
    return df[mask].copy()


def prepare_data(delay_df, codes_df):
    df = delay_df.copy()
    df = df[df["Date"] >= "2025-01-01"].copy()
    df["Line"] = df["Line"].fillna("Unknown")
    df = filter_route_29(df)
    df["ym"] = df["Date"].dt.to_period("M")
    df["month_label"] = df["ym"].astype(str)
    df["category"] = df["Code"].apply(classify_code)
    codes_lookup = dict(zip(codes_df["CODE"], codes_df["DESCRIPTION"]))
    df["code_description"] = df["Code"].map(codes_lookup)
    df["is_significant"] = df["Min Delay"] >= 5
    return df


def build_monthly_summary(df):
    sig = df[df["is_significant"]].copy()
    sig_no_zero = sig[sig["Min Delay"] > 0].copy()

    total_events = df.groupby("month_label").size().rename("total_events")
    significant_delays = sig.groupby("month_label").size().rename("significant_delays")

    delay_stats = sig_no_zero.groupby("month_label")["Min Delay"].agg(
        total_delay_min="sum",
        mean_delay_min="mean",
        median_delay_min="median",
    )

    cat_pcts = {}
    for cat_name in CATEGORY_MAP.values():
        cat_min = (
            sig_no_zero[sig_no_zero["category"] == cat_name]
            .groupby("month_label")["Min Delay"]
            .sum()
        )
        pct = cat_min.div(delay_stats["total_delay_min"]).fillna(0)
        col_name = "pct_" + cat_name.lower().replace("/", "_").replace(" ", "_")
        cat_pcts[col_name] = pct

    summary = pd.concat(
        [total_events, significant_delays, delay_stats]
        + [pd.Series(v, name=k) for k, v in cat_pcts.items()],
        axis=1,
    ).fillna(0)

    all_months = sorted(df["month_label"].unique())
    summary = summary.reindex(all_months, fill_value=0)
    summary.index.name = "month_label"
    summary = summary.reset_index()
    return summary


def build_code_monthly_breakdown(df):
    sig_no_zero = df[(df["is_significant"]) & (df["Min Delay"] > 0)].copy()
    breakdown = (
        sig_no_zero.groupby(["month_label", "Code"])
        .agg(
            count=("Min Delay", "size"),
            total_delay_min=("Min Delay", "sum"),
            mean_delay_min=("Min Delay", "mean"),
        )
        .reset_index()
    )
    codes_lookup = dict(zip(df["Code"], df["code_description"]))
    breakdown["description"] = breakdown["Code"].map(codes_lookup)
    breakdown["category"] = breakdown["Code"].apply(classify_code)
    breakdown = breakdown.rename(columns={"Code": "code"})
    breakdown = breakdown.sort_values(
        ["month_label", "total_delay_min"], ascending=[True, False]
    ).reset_index(drop=True)
    return breakdown


def plot_monthly_delay_trend(summary):
    months = summary["month_label"].values
    sig_counts = summary["significant_delays"].values
    total_min = summary["total_delay_min"].values

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 5.5), sharex=True)

    ax1.plot(months, sig_counts, marker="o", color="#2c3e50", linewidth=2, markersize=5)
    mean_sig = sig_counts[sig_counts > 0].mean()
    ax1.axhline(
        mean_sig,
        linestyle="--",
        color="gray",
        alpha=0.7,
        label=f"Mean ({mean_sig:.0f})",
    )
    ax1.set_ylabel("Significant delay count (>=5 min)")
    ax1.set_title("Monthly significant delay count")
    ax1.legend()
    ax1.grid(axis="y", alpha=0.3)
    ax1.tick_params(axis="x", rotation=45)

    ax2.plot(months, total_min, marker="s", color="#e74c3c", linewidth=2, markersize=5)
    mean_min = total_min[total_min > 0].mean()
    ax2.axhline(
        mean_min,
        linestyle="--",
        color="gray",
        alpha=0.7,
        label=f"Mean ({mean_min:.0f})",
    )
    ax2.set_ylabel("Total delay minutes")
    ax2.set_title("Monthly total delay minutes")
    ax2.legend()
    ax2.grid(axis="y", alpha=0.3)
    ax2.tick_params(axis="x", rotation=45)

    fig.suptitle(
        "TTC Bus Route 29 (Dufferin): Monthly delay trend",
        fontsize=13,
        fontweight="bold",
        y=1.02,
    )
    plt.tight_layout()
    fig.savefig(OUTPUT_DIR / "monthly-delay-trend.png", dpi=150, bbox_inches="tight")
    plt.close(fig)


def plot_monthly_cause_mix(summary, df):
    sig_no_zero = df[(df["is_significant"]) & (df["Min Delay"] > 0)].copy()
    cat_monthly = (
        sig_no_zero.groupby(["month_label", "category"])["Min Delay"]
        .sum()
        .unstack(fill_value=0)
    )
    all_months = sorted(df["month_label"].unique())
    for cat in CATEGORY_MAP.values():
        if cat not in cat_monthly.columns:
            cat_monthly[cat] = 0
    cat_monthly = cat_monthly.reindex(all_months, fill_value=0)
    cat_order = [c for c in CATEGORY_MAP.values() if c in cat_monthly.columns]
    cat_monthly = cat_monthly[cat_order]

    palette = {
        "Equipment": "#e74c3c",
        "Operations": "#3498db",
        "Infrastructure": "#2ecc71",
        "Safety/Security": "#f39c12",
        "Transportation": "#9b59b6",
    }

    fig, ax = plt.subplots(figsize=(14, 6))
    bottom = np.zeros(len(all_months))
    for cat in cat_order:
        vals = cat_monthly[cat].values
        ax.bar(
            all_months,
            vals,
            bottom=bottom,
            label=cat,
            color=palette[cat],
            edgecolor="white",
            linewidth=0.5,
        )
        bottom += vals

    ax.set_ylabel("Total delay minutes")
    ax.set_xlabel("Month")
    ax.set_title(
        "TTC Bus Route 29: Delay cause mix over time", fontsize=12, fontweight="bold"
    )
    ax.legend(title="Category", loc="upper left", fontsize=9)
    ax.grid(axis="y", alpha=0.3)
    ax.tick_params(axis="x", rotation=45)
    plt.tight_layout()
    fig.savefig(OUTPUT_DIR / "monthly-cause-mix.png", dpi=150)
    plt.close(fig)


def plot_top_codes_heatmap(df):
    sig_no_zero = df[(df["is_significant"]) & (df["Min Delay"] > 0)].copy()
    code_total = (
        sig_no_zero.groupby("Code")["Min Delay"].sum().sort_values(ascending=False)
    )
    top_codes = code_total.head(8).index.tolist()

    codes_lookup = dict(zip(df["Code"], df["code_description"]))
    top_labels = []
    for code in top_codes:
        desc = codes_lookup.get(code, code)
        desc = desc.encode("ascii", errors="replace").decode("ascii")
        top_labels.append(f"{code}: {desc}")

    all_months = sorted(df["month_label"].unique())

    heatmap_data = []
    for code in top_codes:
        row = []
        for m in all_months:
            month_code = sig_no_zero[
                (sig_no_zero["Code"] == code) & (sig_no_zero["month_label"] == m)
            ]
            row.append(month_code["Min Delay"].sum())
        heatmap_data.append(row)

    heatmap_df = pd.DataFrame(heatmap_data, index=top_labels, columns=all_months)

    fig, ax = plt.subplots(figsize=(14, 5))
    sns.heatmap(
        heatmap_df,
        annot=True,
        fmt=".0f",
        cmap="YlOrRd",
        linewidths=0.5,
        ax=ax,
        cbar_kws={"label": "Total delay minutes"},
    )
    ax.set_xlabel("Month")
    ax.set_ylabel("Delay code")
    ax.set_title(
        "TTC Bus Route 29: Top delay codes by month", fontsize=12, fontweight="bold"
    )
    ax.tick_params(axis="x", rotation=45)
    plt.tight_layout()
    fig.savefig(OUTPUT_DIR / "top-codes-monthly.png", dpi=150)
    plt.close(fig)


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    delay_df, codes_df = load_data()
    df = prepare_data(delay_df, codes_df)

    print(f"Route 29 rows: {len(df)}")
    print(f"Route 29 significant delays: {df['is_significant'].sum()}")
    print(f"Route 29 lines found: {df['Line'].unique().tolist()}")
    print(f"Date range: {df['Date'].min().date()} to {df['Date'].max().date()}")
    print(f"Months: {sorted(df['month_label'].unique())}")

    summary = build_monthly_summary(df)
    code_breakdown = build_code_monthly_breakdown(df)

    summary.to_csv(OUTPUT_DIR / "monthly-summary.csv", index=False)
    code_breakdown.to_csv(OUTPUT_DIR / "code-monthly-breakdown.csv", index=False)

    plot_monthly_delay_trend(summary)
    plot_monthly_cause_mix(summary, df)
    plot_top_codes_heatmap(df)

    print("\n=== Monthly summary ===")
    print(
        summary[
            ["month_label", "total_events", "significant_delays", "total_delay_min"]
        ].to_string(index=False)
    )

    print("\n=== Top 5 delay codes (total delay minutes) ===")
    sig_no_zero = df[(df["is_significant"]) & (df["Min Delay"] > 0)]
    top_codes = (
        sig_no_zero.groupby("Code")["Min Delay"]
        .sum()
        .sort_values(ascending=False)
        .head(5)
    )
    codes_lookup = dict(zip(df["Code"], df["code_description"]))
    for code, mins in top_codes.items():
        print(f"  {code} ({codes_lookup.get(code, '?')}): {mins:.0f} min")

    print("\n=== Worst and best month by total delay minutes ===")
    valid_months = summary[summary["total_delay_min"] > 0]
    if len(valid_months) > 0:
        worst = valid_months.loc[valid_months["total_delay_min"].idxmax()]
        best = valid_months.loc[valid_months["total_delay_min"].idxmin()]
        print(f"  Worst: {worst['month_label']} ({worst['total_delay_min']:.0f} min)")
        print(f"  Best:  {best['month_label']} ({best['total_delay_min']:.0f} min)")


if __name__ == "__main__":
    main()
