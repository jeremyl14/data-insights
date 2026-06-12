import pathlib
import sys

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parents[3]
DATA_DIR = REPO_ROOT / "datasets" / "toronto-bike-share" / "raw"
OUTPUTS_DIR = pathlib.Path(__file__).resolve().parent / "outputs"

YEARS = [2024, 2025, 2026]
MONTH_NAMES = [
    "Jan",
    "Feb",
    "Mar",
    "Apr",
    "May",
    "Jun",
    "Jul",
    "Aug",
    "Sep",
    "Oct",
    "Nov",
    "Dec",
]


USER_TYPE_MAP = {
    "Member": "member",
    "Annual Member": "member",
    "Casual": "casual",
    "Casual Member": "casual",
}


def load_year(year: int) -> pd.DataFrame:
    path = DATA_DIR / f"bike-share-toronto-ridership-{year}.csv"
    if not path.exists():
        print(f"WARN: {path} not found; skipping {year}", file=sys.stderr)
        return pd.DataFrame(columns=["year", "month", "bike_model", "user_type"])
    print(f"Loading {year}...")
    df = pd.read_csv(path, low_memory=False)
    df.columns = [
        c.strip().lower().replace(" ", "_").replace("__", "_") for c in df.columns
    ]
    rename_map = {}
    for c in df.columns:
        if c == "trip_start_time":
            rename_map[c] = "start_time"
    df = df.rename(columns=rename_map)
    has_start = "start_time" in df.columns
    has_model = "bike_model" in df.columns
    has_user = "user_type" in df.columns
    if not has_start or not has_model:
        print(
            f"WARN: {year} missing start_time or bike_model column; skipping",
            file=sys.stderr,
        )
        return pd.DataFrame(columns=["year", "month", "bike_model", "user_type"])
    keep_cols = ["start_time", "bike_model"]
    if has_user:
        keep_cols.append("user_type")
    df = df[keep_cols].copy()
    dt = pd.to_datetime(df["start_time"], errors="coerce")
    valid = (
        dt.notna() & df["bike_model"].notna() & dt.dt.year.between(year - 1, year + 1)
    )
    df = df.loc[valid].copy()
    df["year"] = dt.loc[valid].dt.year.astype(int)
    df["month"] = dt.loc[valid].dt.month.astype(int)
    df["bike_model"] = df["bike_model"].str.strip()
    if "user_type" in df.columns:
        df["user_type"] = df["user_type"].str.strip().map(USER_TYPE_MAP)
    else:
        df["user_type"] = None
    return df[["year", "month", "bike_model", "user_type"]]


def main() -> None:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)

    frames = []
    for year in YEARS:
        df = load_year(year)
        frames.append(df)
    df = pd.concat(frames, ignore_index=True)

    monthly = (
        df.groupby(["year", "month", "bike_model"]).size().reset_index(name="trips")
    )

    pivot = monthly.pivot_table(
        index=["year", "month"],
        columns="bike_model",
        values="trips",
        fill_value=0,
    ).reset_index()

    ebike_models = {"EFIT", "EFIT G5", "ASTRO"}
    known_models = {"ICONIC", "EFIT", "EFIT G5", "ASTRO"}
    for col in known_models:
        if col not in pivot.columns:
            pivot[col] = 0

    [c for c in pivot.columns if c not in known_models and c not in ("year", "month")]
    pivot["iconic_trips"] = pivot["ICONIC"]
    pivot["efit_trips"] = pivot["EFIT"]
    pivot["efit_g5_trips"] = pivot["EFIT G5"]
    pivot["astro_trips"] = pivot["ASTRO"]
    pivot["ebike_trips"] = (
        pivot["efit_trips"] + pivot["efit_g5_trips"] + pivot["astro_trips"]
    )
    pivot["total_trips"] = pivot["iconic_trips"] + pivot["ebike_trips"]
    pivot["ebike_share"] = pivot["ebike_trips"] / pivot["total_trips"]

    max_month_by_year = df.groupby("year")["month"].max().to_dict()
    pivot["is_partial_year"] = pivot["year"].map(
        lambda y: max_month_by_year.get(y, 12) < 12
    )

    user_monthly = (
        df[df["user_type"].notna()]
        .groupby(["year", "month", "user_type", "bike_model"])
        .size()
        .reset_index(name="trips")
    )
    is_ebike = user_monthly["bike_model"].isin(ebike_models)
    user_ebike = (
        user_monthly[is_ebike]
        .groupby(["year", "month", "user_type"])["trips"]
        .sum()
        .reset_index(name="ebike_trips_ut")
    )
    user_total = (
        user_monthly.groupby(["year", "month", "user_type"])["trips"]
        .sum()
        .reset_index(name="total_trips_ut")
    )
    user_share = user_ebike.merge(
        user_total, on=["year", "month", "user_type"], how="outer"
    )
    user_share["ebike_trips_ut"] = user_share["ebike_trips_ut"].fillna(0)
    user_share["user_ebike_share"] = (
        user_share["ebike_trips_ut"] / user_share["total_trips_ut"]
    )

    member_share = user_share[user_share["user_type"] == "member"][
        ["year", "month", "user_ebike_share"]
    ].rename(columns={"user_ebike_share": "member_ebike_share"})
    casual_share = user_share[user_share["user_type"] == "casual"][
        ["year", "month", "user_ebike_share"]
    ].rename(columns={"user_ebike_share": "casual_ebike_share"})
    pivot = pivot.merge(member_share, on=["year", "month"], how="left")
    pivot = pivot.merge(casual_share, on=["year", "month"], how="left")

    pivot = pivot.sort_values(["year", "month"])
    pivot.to_csv(OUTPUTS_DIR / "bike-model-monthly.csv", index=False)
    print(f"Saved CSV to {OUTPUTS_DIR / 'bike-model-monthly.csv'}")

    yearly = (
        pivot.groupby("year")
        .agg(
            {
                "iconic_trips": "sum",
                "efit_trips": "sum",
                "efit_g5_trips": "sum",
                "total_trips": "sum",
                "is_partial_year": "first",
                "member_ebike_share": "mean",
                "casual_ebike_share": "mean",
            }
        )
        .reset_index()
    )
    yearly["ebike_share"] = (yearly["efit_trips"] + yearly["efit_g5_trips"]) / yearly[
        "total_trips"
    ]
    print("\n=== Yearly summary ===")
    for _, row in yearly.iterrows():
        partial = " (PARTIAL YEAR)" if row["is_partial_year"] else ""
        print(
            f"  {int(row['year'])}: e-bike share = {row['ebike_share']:.1%}, "
            f"total trips = {int(row['total_trips']):,}{partial}"
        )

    pivot["date"] = pd.to_datetime(
        pivot["year"].astype(str) + "-" + pivot["month"].astype(str) + "-01"
    )

    sns.set_theme(style="whitegrid")
    fig, ax1 = plt.subplots(figsize=(14, 7))

    ax1.stackplot(
        pivot["date"],
        pivot["iconic_trips"],
        pivot["efit_trips"],
        pivot["efit_g5_trips"],
        pivot["astro_trips"],
        labels=[
            "ICONIC (standard)",
            "EFIT (e-bike)",
            "EFIT G5 (e-bike)",
            "ASTRO (e-bike)",
        ],
        colors=["#4C72B0", "#DD8452", "#C44E52", "#8C564B"],
        alpha=0.85,
    )
    ax1.set_ylabel("Monthly trips", color="#4C72B0")
    ax1.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"{x / 1e6:.1f}M"))
    ax1.tick_params(axis="y", labelcolor="#4C72B0")

    ax2 = ax1.twinx()
    ax2.grid(False)
    ax2.plot(
        pivot["date"],
        pivot["ebike_share"] * 100,
        color="#2ca02c",
        linewidth=2.5,
        marker="o",
        markersize=4,
        label="E-bike share (%)",
    )
    ax2.set_ylabel("E-bike share (%)", color="#2ca02c")
    ax2.tick_params(axis="y", labelcolor="#2ca02c")
    ax2.set_ylim(bottom=0)

    import matplotlib.dates as mdates

    ax1.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
    ax1.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
    plt.setp(ax1.xaxis.get_majorticklabels(), rotation=45, ha="right")

    partial = pivot[pivot["is_partial_year"]]
    if len(partial) > 0:
        last_partial = partial.iloc[-1]
        ax1.axvline(
            last_partial["date"], color="#999999", linestyle="--", linewidth=0.8
        )
        ax1.text(
            last_partial["date"],
            ax1.get_ylim()[1] * 0.95,
            "2026 partial\n(Jan–Mar)",
            fontsize=8,
            color="#666666",
            ha="left",
            va="top",
        )

    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(
        lines1 + lines2, labels1 + labels2, loc="upper left", fontsize=10, frameon=True
    )

    ax1.set_title(
        "Bike Share Toronto: Trip counts by bike model and e-bike share (2024–2026)",
        fontsize=14,
        fontweight="bold",
    )

    fig.tight_layout()
    fig.savefig(OUTPUTS_DIR / "bike-model-share.png", dpi=150)
    print(f"\nSaved figure to {OUTPUTS_DIR / 'bike-model-share.png'}")

    plot_ebike_by_user_type(pivot)

    plt.close("all")
    print("Done.")


def plot_ebike_by_user_type(pivot: pd.DataFrame) -> None:
    plot_df = pivot[
        pivot["member_ebike_share"].notna() & pivot["casual_ebike_share"].notna()
    ].copy()
    if plot_df.empty:
        print("No user type e-bike data to plot.")
        return

    sns.set_theme(style="whitegrid", font_scale=1.1)
    fig, ax = plt.subplots(figsize=(14, 6))

    ax.plot(
        plot_df["date"],
        plot_df["casual_ebike_share"] * 100,
        color="#d62728",
        linewidth=2,
        marker="o",
        markersize=4,
        label="Casual riders",
    )
    ax.plot(
        plot_df["date"],
        plot_df["member_ebike_share"] * 100,
        color="#1f77b4",
        linewidth=2,
        marker="s",
        markersize=4,
        label="Annual members",
    )

    ax.set_xlabel("Month")
    ax.set_ylabel("E-bike share (%)")
    ax.set_ylim(bottom=0)

    import matplotlib.dates as mdates

    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
    plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha="right")

    ax.legend(fontsize=10, frameon=True, framealpha=0.9)
    ax.set_title("E-bike share by rider type (%)", fontsize=14, fontweight="bold")

    fig.tight_layout()
    path = OUTPUTS_DIR / "ebike-share-by-user-type.png"
    fig.savefig(path, dpi=150)
    print(f"Saved {path}")


if __name__ == "__main__":
    main()
