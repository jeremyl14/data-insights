import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parents[3]

BUS_DATA = REPO_ROOT / "datasets/ttc-bus-delay/raw/ttc-bus-delay-data-since-2025.csv"
BUS_CODES = REPO_ROOT / "datasets/ttc-bus-delay/raw/ttc-bus-delay-codes.csv"
SUBWAY_DATA = (
    REPO_ROOT / "datasets/ttc-subway-delay/raw/ttc-subway-delay-data-since-2025.csv"
)
OUTPUTS = Path(__file__).resolve().parent / "outputs"

CATEGORY_MAP = {
    "E": "Equipment",
    "M": "Operations",
    "P": "Infrastructure",
    "S": "Safety/Security",
    "T": "Transportation",
}

CATEGORY_PALETTE = {
    "Equipment": "#e41a1c",
    "Operations": "#377eb8",
    "Infrastructure": "#4daf4a",
    "Safety/Security": "#984ea3",
    "Transportation": "#ff7f00",
    "Other": "#999999",
}


def map_category(code: str) -> str:
    if pd.isna(code) or len(code) == 0:
        return "Other"
    first = code.strip()[0].upper()
    return CATEGORY_MAP.get(first, "Other")


def load_bus_data():
    df = pd.read_csv(BUS_DATA, parse_dates=["Date"])
    df = df[df["Date"].dt.year == 2025].copy()
    df["Code"] = df["Code"].astype(str).str.strip()
    df["category"] = df["Code"].apply(map_category)
    return df


def load_bus_codes():
    codes = pd.read_csv(BUS_CODES, encoding_errors="replace")
    codes["CODE"] = codes["CODE"].astype(str).str.strip()
    codes["DESCRIPTION"] = codes["DESCRIPTION"].astype(str).str.strip()
    codes["DESCRIPTION"] = codes["DESCRIPTION"].str.replace(
        r"[^\x20-\x7E]", " - ", regex=True
    )
    codes["DESCRIPTION"] = codes["DESCRIPTION"].str.replace(
        r"[^\x20-\x7E]", " - ", regex=True
    )
    codes["DESCRIPTION"] = codes["DESCRIPTION"].str.replace(
        r"(\s*-\s*){2,}", " - ", regex=True
    )
    codes["DESCRIPTION"] = codes["DESCRIPTION"].str.strip()
    return codes.set_index("CODE")["DESCRIPTION"].to_dict()


def load_subway_data():
    df = pd.read_csv(SUBWAY_DATA, parse_dates=["Date"])
    df = df[df["Date"].dt.year == 2025].copy()
    df["Code"] = df["Code"].astype(str).str.strip()
    df["category"] = df["Code"].apply(map_category)
    return df


def build_bus_code_summary(bus_sig, code_descriptions):
    rows = []
    for code, grp in bus_sig.groupby("Code"):
        rows.append(
            {
                "code": code,
                "description": code_descriptions.get(code, ""),
                "category": map_category(code),
                "count_all": 0,
                "count_significant": len(grp),
                "mean_delay_min": round(grp["Min Delay"].mean(), 2),
                "median_delay_min": round(grp["Min Delay"].median(), 2),
                "total_delay_min": round(grp["Min Delay"].sum(), 1),
                "p95_delay_min": round(grp["Min Delay"].quantile(0.95), 2),
            }
        )
    summary = pd.DataFrame(rows)
    return summary.sort_values("total_delay_min", ascending=False).reset_index(
        drop=True
    )


def fill_count_all(summary, bus_all):
    all_counts = bus_all.groupby("Code").size().to_dict()
    summary["count_all"] = summary["code"].map(all_counts).fillna(0).astype(int)
    return summary


def fig_bus_cause_bubble(summary):
    fig, ax = plt.subplots(figsize=(14, 10))
    sizes = summary["total_delay_min"]
    size_scale = 800 / sizes.max()
    colors = summary["category"].map(CATEGORY_PALETTE)

    ax.scatter(
        summary["count_significant"],
        summary["mean_delay_min"],
        s=sizes * size_scale,
        c=colors,
        alpha=0.7,
        edgecolors="black",
        linewidth=0.5,
    )

    for _, row in summary.iterrows():
        ax.annotate(
            row["code"],
            (row["count_significant"], row["mean_delay_min"]),
            fontsize=7,
            ha="center",
            va="bottom",
        )

    ax.set_xscale("log")
    ax.set_xlabel("Count of significant delays (log scale)", fontsize=12)
    ax.set_ylabel("Mean delay duration (minutes)", fontsize=12)
    ax.set_title(
        "TTC Bus 2025: Delay codes by frequency, severity, and impact", fontsize=14
    )

    legend_elements = [
        plt.scatter([], [], marker="o", color=CATEGORY_PALETTE[cat], label=cat, s=100)
        for cat in CATEGORY_PALETTE
        if cat in summary["category"].values
    ]
    ax.legend(handles=legend_elements, title="Category", fontsize=9)

    fig.tight_layout()
    fig.savefig(OUTPUTS / "bus-cause-bubble.png", dpi=150)
    plt.close(fig)


def fig_bus_top_codes(summary):
    top15 = summary.head(15).copy()
    top15["label"] = top15["code"] + " — " + top15["description"]
    top15 = top15.sort_values("total_delay_min")

    fig, ax = plt.subplots(figsize=(12, 8))
    colors = top15["category"].map(CATEGORY_PALETTE)
    ax.barh(
        top15["label"],
        top15["total_delay_min"],
        color=colors,
        edgecolor="black",
        linewidth=0.5,
    )

    ax.set_xlabel("Total delay-minutes (significant delays)", fontsize=12)
    ax.set_title(
        "TTC Bus 2025: Top 15 delay codes by total minutes of delay", fontsize=14
    )

    legend_elements = [
        plt.scatter([], [], marker="s", color=CATEGORY_PALETTE[cat], label=cat, s=100)
        for cat in CATEGORY_PALETTE
        if cat in top15["category"].values
    ]
    ax.legend(handles=legend_elements, title="Category", fontsize=9)

    fig.tight_layout()
    fig.savefig(OUTPUTS / "bus-top-codes.png", dpi=150)
    plt.close(fig)


def build_category_comparison(bus_sig, subway_sig):
    bus_cat = bus_sig.groupby("category")["Min Delay"].sum()
    subway_cat = subway_sig.groupby("category")["Min Delay"].sum()

    all_cats = sorted(set(bus_cat.index) | set(subway_cat.index))
    rows = []
    bus_total = bus_cat.sum()
    subway_total = subway_cat.sum()
    for cat in all_cats:
        bt = bus_cat.get(cat, 0)
        st = subway_cat.get(cat, 0)
        rows.append(
            {
                "category": cat,
                "bus_total_min": round(bt, 1),
                "bus_pct": round(100 * bt / bus_total, 1) if bus_total > 0 else 0,
                "subway_total_min": round(st, 1),
                "subway_pct": round(100 * st / subway_total, 1)
                if subway_total > 0
                else 0,
            }
        )
    return pd.DataFrame(rows)


def fig_bus_vs_subway_categories(comparison):
    sorted(set(comparison["category"]))
    fig, axes = plt.subplots(1, 2, figsize=(14, 6), sharey=True)

    for ax, mode, pct_col in [
        (axes[0], "Bus", "bus_pct"),
        (axes[1], "Subway", "subway_pct"),
    ]:
        if mode == "Bus":
            data = comparison.sort_values("bus_pct", ascending=True)
        else:
            data = comparison.sort_values("subway_pct", ascending=True)
        colors = data["category"].map(CATEGORY_PALETTE)
        ax.barh(
            data["category"],
            data[pct_col],
            color=colors,
            edgecolor="black",
            linewidth=0.5,
        )
        ax.set_xlabel("Share of total significant-delay minutes (%)", fontsize=11)
        ax.set_title(f"{mode}", fontsize=13, fontweight="bold")

    fig.suptitle("TTC 2025: Delay cause mix — Bus vs Subway", fontsize=14, y=1.02)
    fig.tight_layout()
    fig.savefig(OUTPUTS / "bus-vs-subway-categories.png", dpi=150, bbox_inches="tight")
    plt.close(fig)


def main():
    OUTPUTS.mkdir(parents=True, exist_ok=True)

    print("Loading bus data...")
    bus_all = load_bus_data()
    code_descriptions = load_bus_codes()
    bus_sig = bus_all[bus_all["Min Delay"] >= 5].copy()
    print(f"  Bus: {len(bus_all)} total rows, {len(bus_sig)} significant delays")

    print("Loading subway data...")
    subway_all = load_subway_data()
    subway_sig = subway_all[subway_all["Min Delay"] >= 5].copy()
    print(
        f"  Subway: {len(subway_all)} total rows, {len(subway_sig)} significant delays"
    )

    print("Building bus code summary...")
    summary = build_bus_code_summary(bus_sig, code_descriptions)
    summary = fill_count_all(summary, bus_all)
    summary.to_csv(OUTPUTS / "bus-code-summary.csv", index=False)

    print("Building category comparison...")
    comparison = build_category_comparison(bus_sig, subway_sig)
    comparison.to_csv(OUTPUTS / "bus-vs-subway-categories.csv", index=False)

    print("Generating figures...")
    fig_bus_cause_bubble(summary)
    fig_bus_top_codes(summary)
    fig_bus_vs_subway_categories(comparison)

    print("\n=== Top 5 bus delay codes by total delay-minutes ===")
    top5 = summary.head(5)
    for _, row in top5.iterrows():
        print(
            f"  {row['code']:10s} {row['description']:50s}  {row['total_delay_min']:>10.1f} min"
        )

    print("\n=== Bus category breakdown (% of total delay-minutes) ===")
    cat_totals = bus_sig.groupby("category")["Min Delay"].sum()
    cat_pcts = (100 * cat_totals / cat_totals.sum()).sort_values(ascending=False)
    for cat, pct in cat_pcts.items():
        print(f"  {cat:20s} {pct:5.1f}%")

    print("\n=== Bus vs Subway cause mix ===")
    print(comparison.to_string(index=False))

    print("\nDone.")


if __name__ == "__main__":
    main()
