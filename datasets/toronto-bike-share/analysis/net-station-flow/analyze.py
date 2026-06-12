import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
RAW_DIR = SCRIPT_DIR.parent.parent / "raw"
OUTPUTS_DIR = SCRIPT_DIR / "outputs"


def load_data(year: int) -> pd.DataFrame:
    filepath = RAW_DIR / f"bike-share-toronto-ridership-{year}.csv"
    df = pd.read_csv(filepath, low_memory=False)
    df.columns = df.columns.str.strip().str.lower().str.replace(" ", "_")
    if "start_station_name" not in df.columns and "from_station_name" in df.columns:
        df = df.rename(
            columns={
                "from_station_name": "start_station_name",
                "to_station_name": "end_station_name",
            }
        )
    if "start_time" not in df.columns and "trip_start_time" in df.columns:
        df = df.rename(columns={"trip_start_time": "start_time"})
    return df


def compute_net_flow(df: pd.DataFrame) -> pd.DataFrame:
    departures = df["start_station_name"].value_counts().rename("departures")
    arrivals = df["end_station_name"].value_counts().rename("arrivals")
    station_flow = (
        pd.DataFrame({"departures": departures, "arrivals": arrivals})
        .fillna(0)
        .astype(int)
    )
    station_flow.index.name = "station_name"
    station_flow["net_flow"] = station_flow["departures"] - station_flow["arrivals"]
    return station_flow.reset_index()


def plot_top_imbalanced(flow: pd.DataFrame, n: int = 15) -> plt.Figure:
    flow["abs_net"] = flow["net_flow"].abs()
    top = flow.nlargest(n, "abs_net").sort_values("net_flow")

    sns.set_style("whitegrid")
    fig, ax = plt.subplots(figsize=(10, 7))

    colors = ["#d62728" if v > 0 else "#1f77b4" for v in top["net_flow"]]
    ax.barh(top["station_name"], top["net_flow"], color=colors)
    ax.set_xlabel("Net flow (departures − arrivals)")
    ax.set_ylabel("")
    ax.set_title("Bike Share Toronto 2025: Top 15 stations by net bike flow")
    ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"{int(x):,}"))

    from matplotlib.patches import Patch

    legend_elements = [
        Patch(facecolor="#d62728", label="Exporter (departures > arrivals)"),
        Patch(facecolor="#1f77b4", label="Importer (arrivals > departures)"),
    ]
    ax.legend(handles=legend_elements, loc="lower right")

    fig.tight_layout()
    return fig


def main():
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)

    df = load_data(2025)
    flow = compute_net_flow(df)
    flow[["station_name", "departures", "arrivals", "net_flow"]].to_csv(
        OUTPUTS_DIR / "net-station-flow-2025.csv", index=False
    )

    fig = plot_top_imbalanced(flow)
    fig.savefig(OUTPUTS_DIR / "net-station-flow-2025.png", dpi=150)
    plt.close(fig)

    print(f"Wrote {OUTPUTS_DIR / 'net-station-flow-2025.csv'}")
    print(f"Wrote {OUTPUTS_DIR / 'net-station-flow-2025.png'}")


if __name__ == "__main__":
    main()
