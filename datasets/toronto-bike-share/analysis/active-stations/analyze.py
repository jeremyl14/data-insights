"""Active stations analysis for Bike Share Toronto.

Count distinct start station names per year from trip data (2017-2025),
with name normalization to handle SMART stations and encoding artifacts.
Also computes casual vs member trip breakdown with a separate figure.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

REPO_ROOT = Path(__file__).resolve().parent.parents[3]
RAW_DIR = REPO_ROOT / "datasets" / "toronto-bike-share" / "raw"
OUTPUTS = Path(__file__).resolve().parent / "outputs"
OUTPUTS.mkdir(exist_ok=True)

YEARS = list(range(2017, 2026))

USER_TYPE_MAP = {
    "Member": "member",
    "Annual Member": "member",
    "Casual": "casual",
    "Casual Member": "casual",
}


def normalize_station_name(name: str) -> str:
    if not isinstance(name, str):
        return ""
    name = name.strip()
    name = re.sub(r"\s*-\s*SMART\s*$", "", name)
    name = name.replace("GÇô", "s").replace("û", "s").replace("æ", "s")
    name = re.sub(r"\s*/\s*", "/", name)
    name = re.sub(r"\s*-\s*", " ", name)
    name = name.replace(".", "")
    name = name.lower().strip()
    return name


def normalize_user_type(df: pd.DataFrame) -> pd.DataFrame:
    if "user_type" not in df.columns:
        return df
    df["user_type"] = df["user_type"].str.strip().map(USER_TYPE_MAP)
    return df


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


def find_start_station_col(df: pd.DataFrame) -> str | None:
    candidates = ["from_station_name", "start_station_name"]
    for c in candidates:
        if c in df.columns:
            return c
    for c in df.columns:
        if "station_name" in c and ("start" in c or "from" in c):
            return c
    return None


def load_year(year: int) -> pd.DataFrame | None:
    path = RAW_DIR / f"bike-share-toronto-ridership-{year}.csv"
    if not path.exists():
        print(f"WARN: {path} not found; skipping {year}", file=sys.stderr)
        return None

    with open(path, "r") as f:
        header = f.readline().strip()

    raw_cols = [
        c.strip().lower().replace(" ", "_").replace("__", "_")
        for c in header.split(",")
    ]
    rename_map = {}
    for c in header.split(","):
        clean = c.strip().lower().replace(" ", "_").replace("__", "_")
        if clean == "trip_start_time":
            rename_map[clean] = "start_time"
        elif clean == "trip_stop_time":
            rename_map[clean] = "end_time"

    station_col_raw = None
    for orig, clean in zip(header.split(","), raw_cols):
        clean2 = rename_map.get(clean, clean)
        if clean2 in ("from_station_name", "start_station_name"):
            station_col_raw = orig.strip()
            break

    if station_col_raw is None:
        for orig, clean in zip(header.split(","), raw_cols):
            clean2 = rename_map.get(clean, clean)
            if "station_name" in clean2 and ("start" in clean2 or "from" in clean2):
                station_col_raw = orig.strip()
                break

    if station_col_raw is None:
        print(f"WARN: No start station name column found for {year}", file=sys.stderr)
        return None

    user_type_col_raw = None
    for orig, clean in zip(header.split(","), raw_cols):
        if clean == "user_type":
            user_type_col_raw = orig.strip()
            break

    usecols_raw = [station_col_raw]
    if user_type_col_raw is not None:
        usecols_raw.append(user_type_col_raw)

    df = pd.read_csv(path, usecols=usecols_raw, low_memory=False)
    df = normalize_columns(df)

    col = find_start_station_col(df)
    if col is None:
        print(
            f"WARN: No start station column for {year} after normalization",
            file=sys.stderr,
        )
        return None

    keep = [col]
    if "user_type" in df.columns:
        keep.append("user_type")
    df = df[keep].copy()
    df.columns = ["station_name"] + (["user_type"] if "user_type" in df.columns else [])
    df["station_name"] = df["station_name"].apply(normalize_station_name)
    df = df[df["station_name"] != ""]
    df["year"] = year

    if "user_type" in df.columns:
        df = normalize_user_type(df)

    return df


def main() -> int:
    records = []
    for year in YEARS:
        df = load_year(year)
        if df is None:
            continue
        n_stations = df["station_name"].nunique()
        n_trips = len(df)

        casual_trips = 0
        member_trips = 0
        if "user_type" in df.columns:
            ut_counts = df["user_type"].value_counts()
            casual_trips = int(ut_counts.get("casual", 0))
            member_trips = int(ut_counts.get("member", 0))

        records.append(
            {
                "year": year,
                "active_stations": n_stations,
                "total_trips": n_trips,
                "casual_trips": casual_trips,
                "member_trips": member_trips,
                "casual_pct": round(casual_trips / (casual_trips + member_trips), 4)
                if (casual_trips + member_trips) > 0
                else None,
                "is_partial_year": False,
            }
        )
        print(f"  {year}: {n_stations} stations, {n_trips:,} trips", file=sys.stderr)

    if not records:
        print("No data found. Run `dvc pull` first.", file=sys.stderr)
        return 1

    summary = pd.DataFrame(records)
    summary.to_csv(OUTPUTS / "station-count-by-year.csv", index=False)
    print(f"Wrote {len(summary)} rows to outputs/station-count-by-year.csv")

    plot_active_stations(summary)
    plot_casual_member_share(summary)
    return 0


def plot_active_stations(summary: pd.DataFrame) -> None:
    sns.set_theme(style="whitegrid", font_scale=1.1)

    fig, ax1 = plt.subplots(figsize=(12, 6))

    color_stations = "#1f77b4"
    color_trips = "#d62728"

    ax1.plot(
        summary["year"],
        summary["active_stations"],
        marker="o",
        color=color_stations,
        linewidth=2,
        markersize=6,
        label="Active stations",
    )

    ax1.set_xlabel("Year")
    ax1.set_ylabel("Active stations", color=color_stations)
    ax1.tick_params(axis="y", labelcolor=color_stations)
    ax1.set_xticks(summary["year"].astype(int))
    ax1.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"{x:,.0f}"))

    ax2 = ax1.twinx()
    ax2.grid(False)

    ax2.plot(
        summary["year"],
        summary["total_trips"] / 1e6,
        marker="s",
        color=color_trips,
        linewidth=2,
        markersize=5,
        label="Annual trips",
    )

    ax2.set_ylabel("Annual trips (millions)", color=color_trips)
    ax2.tick_params(axis="y", labelcolor=color_trips)

    prev = None
    for _, row in summary.iterrows():
        y = row["year"]
        s = row["active_stations"]
        if prev is not None:
            diff = s - prev
            pct = diff / prev * 100
            if abs(diff) >= 50:
                ax1.annotate(
                    f"+{diff}\n({pct:+.0f}%)",
                    xy=(y, s),
                    xytext=(0, 10),
                    textcoords="offset points",
                    fontsize=8,
                    color=color_stations,
                    ha="center",
                    fontweight="bold",
                )
        prev = s

    fig.suptitle(
        "Bike Share Toronto: Active stations and annual trips (2017–2025)",
        fontsize=13,
        fontweight="bold",
        y=0.98,
    )

    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(
        lines1 + lines2,
        labels1 + labels2,
        loc="upper left",
        fontsize=9,
        frameon=True,
        framealpha=0.9,
    )

    fig.tight_layout(rect=[0, 0, 1, 0.94])
    path = OUTPUTS / "active-stations-by-year.png"
    fig.savefig(path, dpi=150)
    print(f"Saved {path}")
    plt.close(fig)


def plot_casual_member_share(summary: pd.DataFrame) -> None:
    plot_df = summary[summary["casual_pct"].notna()].copy()

    sns.set_theme(style="whitegrid", font_scale=1.1)
    fig, ax = plt.subplots(figsize=(12, 6))

    colors = []
    for y in plot_df["year"]:
        if y == 2023:
            colors.append("#ff7f0e")
        elif y == 2022:
            colors.append("#ff7f0e")
        else:
            colors.append("#1f77b4")

    ax.bar(plot_df["year"], plot_df["casual_pct"] * 100, color=colors, width=0.7)

    for _, row in plot_df.iterrows():
        label = f"{row['casual_pct']:.1%}"
        if row["year"] in (2022, 2023):
            label += "\n⚠ unreliable"
        ax.text(
            row["year"],
            row["casual_pct"] * 100 + 0.8,
            label,
            ha="center",
            va="bottom",
            fontsize=9,
            fontweight="bold" if row["year"] in (2022, 2023) else "normal",
            color="#ff7f0e" if row["year"] in (2022, 2023) else "#1f77b4",
        )

    ax.set_xlabel("Year")
    ax.set_ylabel("Casual rider share (%)")
    ax.set_xticks(plot_df["year"].astype(int))
    ax.set_ylim(0, max(plot_df["casual_pct"] * 100) * 1.25)

    ax.text(
        0.02,
        0.97,
        "Orange bars = 2022–2023 (user_type labels unreliable in source data)",
        transform=ax.transAxes,
        fontsize=8,
        color="#ff7f0e",
        va="top",
    )

    ax.set_title(
        "Bike Share Toronto: Casual rider share of total trips (2017–2025)",
        fontsize=13,
        fontweight="bold",
    )

    fig.tight_layout()
    path = OUTPUTS / "casual-member-share.png"
    fig.savefig(path, dpi=150)
    print(f"Saved {path}")
    plt.close(fig)


if __name__ == "__main__":
    sys.exit(main())
