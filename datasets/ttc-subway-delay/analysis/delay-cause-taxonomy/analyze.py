import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parents[3]
ANALYSIS_DIR = Path(__file__).resolve().parent
RAW_DIR = REPO_ROOT / "datasets" / "ttc-subway-delay" / "raw"
OUTPUTS_DIR = ANALYSIS_DIR / "outputs"

CATEGORY_MAP = {
    "E": "Equipment",
    "M": "Operations",
    "P": "Infrastructure",
    "S": "Safety/Security",
    "T": "Transportation",
}

LINE_NORM = {
    "YU": "YU",
    "YUS": "YU",
    "BD": "BD",
    "SHP": "SHP",
    "SRT": "SHP",
}


def load_delay_data():
    df = pd.read_csv(RAW_DIR / "ttc-subway-delay-data-since-2025.csv")
    df["Date"] = pd.to_datetime(df["Date"])
    df = df[df["Date"].dt.year == 2025].copy()
    df["Code"] = df["Code"].str.strip()
    df["Line_norm"] = df["Line"].map(LINE_NORM)
    known = {"YU", "BD", "SHP"}
    df.loc[~df["Line_norm"].isin(known), "Line_norm"] = "Other"
    df = df[df["Line_norm"] != "Other"].copy()
    df["month"] = df["Date"].dt.to_period("M")
    return df


def load_code_lookup():
    wb_path = RAW_DIR / "ttc-subway-delay-codes.xlsx"
    wb = pd.ExcelFile(wb_path, engine="openpyxl")
    df_raw = wb.parse("Sheet 1", header=None)

    yu_codes = {}
    srt_codes = {}
    for _, row in df_raw.iterrows():
        yu_code = row.iloc[2]
        yu_desc = row.iloc[3]
        srt_code = row.iloc[6]
        srt_desc = row.iloc[7]
        if pd.notna(yu_code) and str(yu_code).strip():
            yu_codes[str(yu_code).strip()] = (
                str(yu_desc).strip() if pd.notna(yu_desc) else ""
            )
        if pd.notna(srt_code) and str(srt_code).strip():
            srt_codes[str(srt_code).strip()] = (
                str(srt_desc).strip() if pd.notna(srt_desc) else ""
            )

    all_codes = {}
    for code, desc in yu_codes.items():
        if code in srt_codes:
            all_codes[code] = {"description": desc, "line_scope": "both"}
        else:
            all_codes[code] = {"description": desc, "line_scope": "YU"}

    for code, desc in srt_codes.items():
        if code not in all_codes:
            all_codes[code] = {"description": desc, "line_scope": "BD"}

    lookup_df = pd.DataFrame.from_dict(all_codes, orient="index").reset_index()
    lookup_df.columns = ["code", "description", "line_scope"]
    return lookup_df


def assign_category(code):
    if pd.isna(code) or not str(code).strip():
        return "Other"
    first = str(code).strip()[0].upper()
    return CATEGORY_MAP.get(first, "Other")


def build_code_summary(df, lookup_df):
    sig = df[df["Min Delay"] >= 5].copy()
    all_stats = (
        df.groupby("Code")
        .agg(
            count_all=("Min Delay", "size"),
            total_delay_min=("Min Delay", "sum"),
        )
        .reset_index()
    )
    sig_stats = (
        sig.groupby("Code")
        .agg(
            count_significant=("Min Delay", "size"),
            mean_delay_min=("Min Delay", "mean"),
            median_delay_min=("Min Delay", "median"),
            p95_delay_min=("Min Delay", lambda x: x.quantile(0.95)),
        )
        .reset_index()
    )
    summary = all_stats.merge(sig_stats, on="Code", how="left")
    summary["count_significant"] = summary["count_significant"].fillna(0).astype(int)
    for col in ["mean_delay_min", "median_delay_min", "p95_delay_min"]:
        summary[col] = summary[col].fillna(0.0)

    summary = summary.merge(lookup_df, left_on="Code", right_on="code", how="left")
    summary["description"] = summary["description"].fillna("")
    summary["line_scope"] = summary["line_scope"].fillna("")
    summary["category"] = summary["Code"].apply(assign_category)
    summary = summary[
        [
            "Code",
            "description",
            "category",
            "line_scope",
            "count_all",
            "count_significant",
            "mean_delay_min",
            "median_delay_min",
            "total_delay_min",
            "p95_delay_min",
        ]
    ].rename(columns={"Code": "code"})
    summary = summary.sort_values("total_delay_min", ascending=False).reset_index(
        drop=True
    )
    return summary


def build_category_monthly(df):
    sig = df[df["Min Delay"] >= 5].copy()
    sig["category"] = sig["Code"].apply(assign_category)
    monthly = (
        sig.groupby(["month", "Line_norm", "category"])
        .agg(count=("Min Delay", "size"), total_delay_min=("Min Delay", "sum"))
        .reset_index()
    )
    line_totals = (
        sig.groupby(["month", "Line_norm"])
        .agg(line_total=("Min Delay", "sum"))
        .reset_index()
    )
    monthly = monthly.merge(line_totals, on=["month", "Line_norm"])
    monthly["pct_of_line_total"] = (
        monthly["total_delay_min"] / monthly["line_total"] * 100
    ).round(2)
    monthly["month"] = monthly["month"].astype(str)
    monthly = monthly.rename(columns={"Line_norm": "line"})
    monthly = monthly[
        ["month", "line", "category", "count", "total_delay_min", "pct_of_line_total"]
    ]
    return monthly


def plot_bubble_chart(code_summary, top_n=20):
    top = code_summary.head(top_n).copy()
    fig, ax = plt.subplots(figsize=(14, 10))
    cat_colors = {
        "Equipment": "#1f77b4",
        "Operations": "#ff7f0e",
        "Infrastructure": "#2ca02c",
        "Safety/Security": "#d62728",
        "Transportation": "#9467bd",
        "Other": "#7f7f7f",
    }
    for cat in top["category"].unique():
        subset = top[top["category"] == cat]
        ax.scatter(
            subset["count_significant"],
            subset["mean_delay_min"],
            s=subset["total_delay_min"] / top["total_delay_min"].max() * 2000,
            c=cat_colors.get(cat, "#7f7f7f"),
            alpha=0.7,
            edgecolors="black",
            linewidths=0.5,
            label=cat,
        )
    for _, row in top.iterrows():
        ax.annotate(
            row["code"],
            (row["count_significant"], row["mean_delay_min"]),
            fontsize=8,
            ha="center",
            va="bottom",
        )
    ax.set_xscale("log")
    ax.set_xlabel("Count of significant delays (log scale, Min Delay >= 5 min)")
    ax.set_ylabel("Mean delay duration (minutes)")
    ax.set_title("TTC Subway 2025: Delay codes by frequency, severity, and impact")
    ax.legend(title="Category", bbox_to_anchor=(1.02, 1), loc="upper left")
    plt.tight_layout()
    fig.savefig(OUTPUTS_DIR / "cause-bubble-chart.png", dpi=150)
    plt.close(fig)


def plot_top_codes_by_minutes(code_summary, top_n=15):
    top = code_summary.head(top_n).copy()
    top["label"] = top.apply(
        lambda r: f"{r['code']} - {r['description']}"
        if r["description"]
        else r["code"],
        axis=1,
    )
    cat_colors = {
        "Equipment": "#1f77b4",
        "Operations": "#ff7f0e",
        "Infrastructure": "#2ca02c",
        "Safety/Security": "#d62728",
        "Transportation": "#9467bd",
        "Other": "#7f7f7f",
    }
    fig, ax = plt.subplots(figsize=(12, 8))
    colors = [cat_colors.get(c, "#7f7f7f") for c in top["category"]]
    ax.barh(top["label"][::-1], top["total_delay_min"][::-1], color=colors[::-1])
    ax.set_xlabel("Total delay-minutes")
    ax.set_title("TTC Subway 2025: Top 15 delay codes by total minutes of delay")
    handles = [
        plt.Rectangle((0, 0), 1, 1, color=cat_colors[cat])
        for cat in [
            "Equipment",
            "Operations",
            "Infrastructure",
            "Safety/Security",
            "Transportation",
            "Other",
        ]
        if cat in top["category"].values
    ]
    labels = [
        cat
        for cat in [
            "Equipment",
            "Operations",
            "Infrastructure",
            "Safety/Security",
            "Transportation",
            "Other",
        ]
        if cat in top["category"].values
    ]
    ax.legend(handles, labels, title="Category", loc="lower right")
    plt.tight_layout()
    fig.savefig(OUTPUTS_DIR / "top-codes-by-minutes.png", dpi=150)
    plt.close(fig)


def plot_category_monthly_share(cat_monthly):
    lines = ["YU", "BD", "SHP"]
    line_labels = {
        "YU": "Yonge-University (YU)",
        "BD": "Bloor-Danforth (BD)",
        "SHP": "Scarborough (SHP)",
    }
    cat_order = [
        "Equipment",
        "Operations",
        "Infrastructure",
        "Safety/Security",
        "Transportation",
        "Other",
    ]
    cat_colors = {
        "Equipment": "#1f77b4",
        "Operations": "#ff7f0e",
        "Infrastructure": "#2ca02c",
        "Safety/Security": "#d62728",
        "Transportation": "#9467bd",
        "Other": "#7f7f7f",
    }
    fig, axes = plt.subplots(1, 3, figsize=(18, 6), sharey=True)
    for ax, line in zip(axes, lines):
        line_data = cat_monthly[cat_monthly["line"] == line].copy()
        if line_data.empty:
            ax.set_title(line_labels.get(line, line))
            ax.text(
                0.5, 0.5, "No data", ha="center", va="center", transform=ax.transAxes
            )
            continue
        pivot = line_data.pivot_table(
            index="month",
            columns="category",
            values="pct_of_line_total",
            aggfunc="sum",
            fill_value=0,
        )
        for cat in cat_order:
            if cat not in pivot.columns:
                pivot[cat] = 0
        pivot = pivot[cat_order]
        pivot.plot(
            kind="bar",
            stacked=True,
            ax=ax,
            color=[cat_colors[c] for c in cat_order],
            legend=False,
            width=0.8,
        )
        ax.set_title(line_labels.get(line, line))
        ax.set_xlabel("")
        ax.set_ylabel("% of significant-delay minutes" if ax == axes[0] else "")
        ax.set_xticklabels(
            [x.get_text()[:7] for x in ax.get_xticklabels()],
            rotation=45,
            ha="right",
            fontsize=8,
        )
    handles = [plt.Rectangle((0, 0), 1, 1, color=cat_colors[c]) for c in cat_order]
    fig.legend(
        handles,
        cat_order,
        title="Category",
        loc="lower center",
        ncol=6,
        bbox_to_anchor=(0.5, -0.02),
    )
    fig.suptitle(
        "TTC Subway 2025: Delay cause mix by month and line", fontsize=14, y=1.02
    )
    plt.tight_layout()
    fig.savefig(
        OUTPUTS_DIR / "category-monthly-share.png", dpi=150, bbox_inches="tight"
    )
    plt.close(fig)


def main():
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    df = load_delay_data()
    lookup_df = load_code_lookup()
    code_summary = build_code_summary(df, lookup_df)
    cat_monthly = build_category_monthly(df)

    code_summary.to_csv(OUTPUTS_DIR / "code-summary.csv", index=False)
    cat_monthly.to_csv(OUTPUTS_DIR / "category-monthly.csv", index=False)

    plot_bubble_chart(code_summary)
    plot_top_codes_by_minutes(code_summary)
    plot_category_monthly_share(cat_monthly)

    print("=== Top 5 delay codes by total delay-minutes ===")
    top5 = code_summary.head(5)
    for _, row in top5.iterrows():
        desc = row["description"] if row["description"] else "(no description)"
        print(f"  {row['code']}: {desc} — {row['total_delay_min']:.0f} min")

    print(
        "\n=== Category breakdown (% of total delay-minutes, significant delays only) ==="
    )
    sig = df[df["Min Delay"] >= 5].copy()
    sig["category"] = sig["Code"].apply(assign_category)
    cat_totals = sig.groupby("category")["Min Delay"].sum()
    for cat, total in cat_totals.sort_values(ascending=False).items():
        pct = total / cat_totals.sum() * 100
        print(f"  {cat}: {total:.0f} min ({pct:.1f}%)")

    unmatched = code_summary[code_summary["description"] == ""]
    print(f"\n=== Unmatched codes: {len(unmatched)} ===")
    if len(unmatched) > 0:
        print(f"  Codes: {', '.join(unmatched['code'].tolist())}")


if __name__ == "__main__":
    main()
