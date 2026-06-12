import pathlib

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

DATA_DIR = pathlib.Path(__file__).resolve().parent.parent.parent / "raw"
OUTPUTS_DIR = pathlib.Path(__file__).resolve().parent / "outputs"
YEARS = range(2016, 2027)

USER_TYPE_MAP = {
    "Annual Member": "Member",
    "Casual Member": "Casual",
    "Member": "Member",
    "Casual": "Casual",
}


def load_year(year: int) -> pd.DataFrame:
    path = DATA_DIR / f"bike-share-toronto-ridership-{year}.csv"
    df = pd.read_csv(path, low_memory=False)
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]
    df = df.rename(columns={"trip_start_time": "start_time"})
    df["user_type"] = df["user_type"].map(USER_TYPE_MAP)
    dt = pd.to_datetime(df["start_time"], errors="coerce")
    valid = (
        dt.notna() & df["user_type"].notna() & dt.dt.year.between(year - 1, year + 1)
    )
    df = df.loc[valid].copy()
    df["year"] = dt.loc[valid].dt.year.astype(int)
    df["month"] = dt.loc[valid].dt.month.astype(int)
    return df[["year", "month", "user_type"]]


def main() -> None:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)

    frames = []
    for year in YEARS:
        path = DATA_DIR / f"bike-share-toronto-ridership-{year}.csv"
        if not path.exists():
            print(f"Skipping {year}: file not found")
            continue
        print(f"Loading {year}...")
        frames.append(load_year(year))

    df = pd.concat(frames, ignore_index=True)

    monthly = (
        df.groupby(["year", "month", "user_type"]).size().reset_index(name="trips")
    )
    monthly.to_csv(OUTPUTS_DIR / "monthly-by-user-type.csv", index=False)

    yearly = df.groupby(["year", "user_type"]).size().reset_index(name="trips")
    yearly.to_csv(OUTPUTS_DIR / "yearly-user-type-totals.csv", index=False)

    monthly["date"] = pd.to_datetime(
        monthly["year"].astype(str) + "-" + monthly["month"].astype(str) + "-01"
    )
    monthly = monthly.sort_values(["user_type", "date"])
    monthly["trips_smooth"] = monthly.groupby("user_type")["trips"].transform(
        lambda s: s.rolling(window=3, center=True, min_periods=1).mean()
    )

    sns.set_theme(style="whitegrid")
    fig, ax = plt.subplots(figsize=(14, 6))
    sns.lineplot(
        data=monthly,
        x="date",
        y="trips_smooth",
        hue="user_type",
        ax=ax,
        linewidth=2,
    )
    ax.set_title("Bike Share Toronto: Monthly ridership by user type", fontsize=16)
    ax.set_xlabel("Date", fontsize=12)
    ax.set_ylabel("Monthly trips (3-month rolling avg)", fontsize=12)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"{x:,.0f}"))
    ax.legend(title="User type", fontsize=11, title_fontsize=12)
    fig.tight_layout()
    fig.savefig(OUTPUTS_DIR / "user-type-monthly.png", dpi=150)
    print(f"Saved figure to {OUTPUTS_DIR / 'user-type-monthly.png'}")
    print("Done.")


if __name__ == "__main__":
    main()
