import pathlib
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

RAW_DIR = pathlib.Path(__file__).resolve().parents[2] / "raw"
OUTPUTS_DIR = pathlib.Path(__file__).resolve().parent / "outputs"
YEARS = range(2016, 2027)


def load_year(year):
    path = RAW_DIR / f"bike-share-toronto-ridership-{year}.csv"
    df = pd.read_csv(path, dtype=str)
    cols = {}
    for raw_col in df.columns:
        norm = raw_col.strip().lower().replace(" ", "_")
        cols[raw_col] = norm
    df = df.rename(columns=cols)
    if "from_station_name" in df.columns:
        station_col = "from_station_name"
    elif "start_station_name" in df.columns:
        station_col = "start_station_name"
    else:
        raise KeyError(f"No departure station column found for year {year}")
    df = df[[station_col]].dropna(subset=[station_col])
    df = df[df[station_col].str.strip() != ""]
    df = df.assign(year=year, station_name=df[station_col].str.strip())
    return df[["year", "station_name"]]


def main():
    frames = []
    for year in YEARS:
        path = RAW_DIR / f"bike-share-toronto-ridership-{year}.csv"
        if not path.exists():
            print(f"Skipping {year}: file not found")
            continue
        frames.append(load_year(year))

    all_trips = pd.concat(frames, ignore_index=True)
    yearly = (
        all_trips.groupby(["year", "station_name"]).size().reset_index(name="trips")
    )

    top_stations = all_trips.groupby("station_name").size().nlargest(10).index.tolist()

    top_yearly = yearly[yearly["station_name"].isin(top_stations)].copy()

    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    top_yearly.to_csv(OUTPUTS_DIR / "top-stations-yearly.csv", index=False)

    sns.set_theme(style="whitegrid")
    fig, ax = plt.subplots(figsize=(12, 7))
    for station in top_stations:
        subset = top_yearly[top_yearly["station_name"] == station]
        ax.plot(subset["year"], subset["trips"], marker="o", label=station)

    ax.set_title("Bike Share Toronto: Top 10 stations by total departures")
    ax.set_xlabel("Year")
    ax.set_ylabel("Departures")
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"{int(x):,}"))
    ax.legend(bbox_to_anchor=(1.02, 1), loc="upper left", borderaxespad=0)
    fig.tight_layout()
    fig.savefig(OUTPUTS_DIR / "top-stations-over-time.png", dpi=150)
    plt.close(fig)
    print(f"Saved figure: {OUTPUTS_DIR / 'top-stations-over-time.png'}")
    print(f"Saved CSV: {OUTPUTS_DIR / 'top-stations-yearly.csv'}")


if __name__ == "__main__":
    main()
