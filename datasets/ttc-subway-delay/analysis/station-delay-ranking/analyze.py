import re
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parents[3]
RAW_DIR = REPO_ROOT / "datasets" / "ttc-subway-delay" / "raw"
OUTPUTS = Path(__file__).resolve().parent / "outputs"
OUTPUTS.mkdir(exist_ok=True)

VALID_LINES = {"YU", "BD", "SHP"}
CATEGORY_MAP = {
    "E": "Equipment",
    "M": "Operations",
    "P": "Infrastructure",
    "S": "Safety",
    "T": "Transportation",
}
LINE_COLORS = {"YU": "#003DA5", "BD": "#00843D", "SHP": "#F7941D"}


def load_delay_codes():
    codes = pd.read_excel(
        RAW_DIR / "ttc-subway-delay-codes.xlsx", header=None, skiprows=2
    )
    yu = codes[[2, 3]].dropna()
    yu.columns = ["Code", "Description"]
    srt = codes[[6, 7]].dropna()
    srt.columns = ["Code", "Description"]
    all_codes = pd.concat([yu, srt]).drop_duplicates(subset="Code")
    all_codes["Code"] = all_codes["Code"].str.strip().str.upper()
    all_codes["Description"] = all_codes["Description"].str.strip()
    return dict(zip(all_codes["Code"], all_codes["Description"]))


def normalize_station(name: str) -> str:
    s = name.strip().upper()
    s = re.sub(r"\s*\(.*", "", s)
    s = s.replace(" - SMART", "").replace("-SMART", "")
    s = re.sub(r"\s+", " ", s).strip()
    s = re.sub(
        r"^(APPR?OA?CHING|DEPARTING|ENTERING|EXITING|LEAVING|IN TUNNEL)\s+", "", s
    )
    s = re.sub(
        r"\s+(APPR?OA?CHING|DEPARTING|ENTERING|EXITING|LEAVING|IN TUNNEL)$", "", s
    )
    s = re.sub(r"^(ON THE|TOWARDS|TO)\s+", "", s)
    line_suffix_re = re.compile(r"\s+(YU|YUS|BD|SHP|SRT)\s+STATION$", re.IGNORECASE)
    s = line_suffix_re.sub(" STATION", s)
    s = re.sub(r"\s+(BD|YU|YUS|SHP)$", "", s)
    s = s.strip()
    mappings = {
        "ST GEORGE BD STATION": "ST GEORGE STATION",
        "ST GEORGE YUS STATION": "ST GEORGE STATION",
        "ST GEORGE": "ST GEORGE STATION",
        "KENNEDY BD STATION": "KENNEDY BD STATION",
        "CEDARVALE YU STATION": "CEDARVALE STATION",
        "DAVISVILLE YARD": "DAVISVILLE YARD",
        "GREENWOOD YARD": "GREENWOOD YARD",
        "KEELE YARD": "KEELE YARD",
        "KIPLING": "KIPLING STATION",
        "FINCH": "FINCH STATION",
        "VMC STATION": "VAUGHAN MC STATION",
        "563 SHERBOURNE": "SHERBOURNE STATION",
        "IMPERIAL ST": "IMPERIAL STATION",
        "OSSION STATION": "OSSINGTON STATION",
        "OSSINGTON": "OSSINGTON STATION",
        "BAY": "BAY STATION",
        "VARIOUS LOCATION": "VARIOUS",
        "VARIOUS STATION": "VARIOUS",
        "SUBWAY: LINE 1": "VARIOUS",
        "YONGE BD STATION": "YONGE BD STATION",
    }
    for k, v in mappings.items():
        if s == k:
            return v
    return s


def load_and_prepare():
    df = pd.read_csv(RAW_DIR / "ttc-subway-delay-data-since-2025.csv")
    df["Date"] = pd.to_datetime(df["Date"])
    df = df[df["Date"].dt.year == 2025].copy()
    df = df[df["Line"].isin(VALID_LINES)].copy()
    df = df[df["Min Delay"] > 0].copy()
    df["Station_clean"] = df["Station"].apply(normalize_station)
    df["Code"] = df["Code"].str.strip().str.upper()
    df["category"] = df["Code"].str[0].map(CATEGORY_MAP)
    df.loc[df["category"].isna(), "category"] = "Other"
    code_lookup = load_delay_codes()
    df["code_desc"] = df["Code"].map(code_lookup).fillna("")
    return df


def build_station_summary(df):
    def cat_pct(g):
        cats = g.groupby("category")["Min Delay"].sum()
        total = cats.sum()
        return {
            f"pct_{c.lower()}": cats.get(c, 0) / total * 100 if total > 0 else 0
            for c in [
                "Infrastructure",
                "Operations",
                "Safety",
                "Equipment",
                "Transportation",
            ]
        }

    rows = []
    for (station, line), g in df.groupby(["Station_clean", "Line"]):
        sig = g[g["Min Delay"] >= 5]
        pcts = cat_pct(g)
        rows.append(
            {
                "station": station,
                "line": line,
                "total_delays": len(g),
                "significant_delays": len(sig),
                "total_delay_min": g["Min Delay"].sum(),
                "mean_delay_min": round(g["Min Delay"].mean(), 1),
                "median_delay_min": g["Min Delay"].median(),
                **pcts,
            }
        )
    return pd.DataFrame(rows).sort_values("total_delay_min", ascending=False)


def build_cause_breakdown(df):
    rows = []
    for (station, line), g in df.groupby(["Station_clean", "Line"]):
        for cat, cg in g.groupby("category"):
            rows.append(
                {
                    "station": station,
                    "line": line,
                    "category": cat,
                    "count": len(cg),
                    "total_delay_min": cg["Min Delay"].sum(),
                    "mean_delay_min": round(cg["Min Delay"].mean(), 1),
                }
            )
    return pd.DataFrame(rows)


def plot_top_stations(summary, top_n=20):
    top = summary.head(top_n).sort_values("total_delay_min")
    fig, ax = plt.subplots(figsize=(10, 8))
    colors = [LINE_COLORS.get(ln, "#999999") for ln in top["line"]]
    ax.barh(top["station"], top["total_delay_min"], color=colors)
    for i, (val, line) in enumerate(zip(top["total_delay_min"], top["line"])):
        ax.text(val + 5, i, f"{int(val):,}", va="center", fontsize=8)
    ax.set_xlabel("Total delay minutes")
    ax.set_title(
        "TTC Subway 2025: Top 20 stations by total delay minutes (all delays > 0 min)"
    )
    handles = [
        plt.Rectangle((0, 0), 1, 1, color=LINE_COLORS[ln]) for ln in ["YU", "BD", "SHP"]
    ]
    ax.legend(
        handles,
        ["Yonge-University", "Bloor-Danforth", "Sheppard"],
        title="Line",
        loc="lower right",
    )
    ax.set_xlim(0, top["total_delay_min"].max() * 1.12)
    plt.tight_layout()
    fig.savefig(OUTPUTS / "top-stations-by-delay.png", dpi=150)
    plt.close(fig)


def plot_cause_breakdown(cause, summary, top_n=10):
    top_stations = summary.head(top_n)["station"].tolist()
    summary.head(top_n)["line"].tolist()
    top_cause = cause[cause["station"].isin(top_stations)].copy()
    station_order = list(reversed(top_stations))
    top_cause["station"] = pd.Categorical(
        top_cause["station"], categories=top_stations, ordered=True
    )
    top_cause = top_cause.sort_values("station")

    pivot = top_cause.pivot_table(
        index="station",
        columns="category",
        values="total_delay_min",
        fill_value=0,
        observed=False,
    )
    pivot = pivot.reindex([s for s in station_order if s in pivot.index])
    cat_colors = {
        "Equipment": "#E69F00",
        "Operations": "#56B4E9",
        "Infrastructure": "#009E73",
        "Safety": "#D55E00",
        "Transportation": "#CC79A7",
        "Other": "#999999",
    }
    fig, ax = plt.subplots(figsize=(10, 7))
    pivot.plot(
        kind="barh",
        stacked=True,
        ax=ax,
        color=[cat_colors.get(c, "#999999") for c in pivot.columns],
    )
    ax.set_xlabel("Total delay minutes")
    ax.set_title("TTC Subway 2025: What causes delays at the worst stations?")
    ax.legend(title="Cause category", bbox_to_anchor=(1.02, 1), loc="upper left")
    plt.tight_layout()
    fig.savefig(OUTPUTS / "station-cause-breakdown.png", dpi=150)
    plt.close(fig)


def main():
    df = load_and_prepare()
    summary = build_station_summary(df)
    cause = build_cause_breakdown(df)
    summary.to_csv(OUTPUTS / "station-delay-summary.csv", index=False)
    cause.to_csv(OUTPUTS / "station-cause-breakdown.csv", index=False)
    plot_top_stations(summary)
    plot_cause_breakdown(cause, summary)

    print("=== Top 5 stations by total delay minutes ===")
    print(
        summary[["station", "line", "total_delay_min"]].head(5).to_string(index=False)
    )

    sig = df[df["Min Delay"] >= 5]
    print(
        f"\n=== 2025 Significant delays: {len(sig):,} events, {sig['Min Delay'].sum():,.0f} total minutes ==="
    )
    print(
        f"=== Unique stations after normalization: {df['Station_clean'].nunique()} ==="
    )


if __name__ == "__main__":
    main()
