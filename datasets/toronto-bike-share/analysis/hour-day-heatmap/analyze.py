import pathlib

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

RAW_DIR = pathlib.Path(__file__).resolve().parents[2] / "raw"
OUTPUTS_DIR = pathlib.Path(__file__).resolve().parent / "outputs"

DATA_PATH = RAW_DIR / "bike-share-toronto-ridership-2024.csv"


def load_data():
    df = pd.read_csv(
        DATA_PATH,
        usecols=["Start_Time"],
        parse_dates=["Start_Time"],
    )
    df = df.dropna(subset=["Start_Time"])
    df["hour"] = df["Start_Time"].dt.hour
    df["day_of_week"] = df["Start_Time"].dt.day_name()
    return df


def compute_averages(df):
    counts = df.groupby(["day_of_week", "hour"]).size().reset_index(name="trip_count")
    num_weeks = df["Start_Time"].dt.isocalendar().week.nunique()
    counts["avg_trips"] = counts["trip_count"] / num_weeks
    return counts


def plot_heatmap(pivot):
    fig, ax = plt.subplots(figsize=(16, 5))
    annotations = pivot.map(lambda v: f"{v / 1000:.1f}k")
    sns.heatmap(
        pivot,
        annot=annotations,
        fmt="",
        cmap="YlOrRd",
        linewidths=0.5,
        linecolor="white",
        ax=ax,
    )
    ax.set_xlabel("Hour of Day")
    ax.set_ylabel("Day of Week")
    ax.set_title("Bike Share Toronto 2024: Trips by hour and day of week")
    fig.tight_layout()
    return fig


def main():
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)

    df = load_data()
    averages = compute_averages(df)

    day_order = [
        "Monday",
        "Tuesday",
        "Wednesday",
        "Thursday",
        "Friday",
        "Saturday",
        "Sunday",
    ]
    pivot = averages.pivot(index="day_of_week", columns="hour", values="avg_trips")
    pivot = pivot.reindex(index=day_order)

    fig = plot_heatmap(pivot)
    fig.savefig(OUTPUTS_DIR / "hour-day-heatmap.png", dpi=150)
    plt.close(fig)

    csv_out = averages[["day_of_week", "hour", "avg_trips"]].copy()
    csv_out.to_csv(OUTPUTS_DIR / "hour-day-averages.csv", index=False)

    print(f"Saved {OUTPUTS_DIR / 'hour-day-heatmap.png'}")
    print(f"Saved {OUTPUTS_DIR / 'hour-day-averages.csv'}")


if __name__ == "__main__":
    main()
