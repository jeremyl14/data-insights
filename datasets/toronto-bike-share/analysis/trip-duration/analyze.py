import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import os
import re

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
RAW_DIR = os.path.join(SCRIPT_DIR, "..", "..", "raw")
OUTPUTS_DIR = os.path.join(SCRIPT_DIR, "outputs")
os.makedirs(OUTPUTS_DIR, exist_ok=True)

DURATION_COLS = {"trip_duration", "trip_duration_seconds", "trip__duration"}
USER_TYPE_COLS = {"user_type", "user__type"}


def normalize_col(c):
    c = c.strip().lower().replace(" ", "_")
    c = re.sub(r"__+", "_", c)
    return c


def load_year(year):
    fname = f"bike-share-toronto-ridership-{year}.csv"
    path = os.path.join(RAW_DIR, fname)
    if not os.path.exists(path):
        return None
    usecols = []
    header = pd.read_csv(path, nrows=0).columns.tolist()
    norm_map = {orig: normalize_col(orig) for orig in header}
    for orig, norm in norm_map.items():
        if norm in DURATION_COLS or norm in USER_TYPE_COLS:
            usecols.append(orig)
    if not any(norm_map[c] in DURATION_COLS for c in usecols):
        return None
    df = pd.read_csv(path, usecols=usecols)
    df.columns = [normalize_col(c) for c in df.columns]
    if "trip_duration_seconds" in df.columns:
        duration_col = "trip_duration_seconds"
    elif "trip__duration" in df.columns:
        duration_col = "trip__duration"
    elif "trip_duration" in df.columns:
        duration_col = "trip_duration"
    else:
        return None
    df = df.rename(columns={duration_col: "trip_duration"})
    df = df.dropna(subset=["trip_duration"])
    median_val = df["trip_duration"].median()
    if median_val > 100:
        df["duration_minutes"] = df["trip_duration"] / 60.0
    else:
        df["duration_minutes"] = df["trip_duration"].astype(float)
    df = df[df["duration_minutes"].between(30 / 60, 24 * 60)]
    has_user_type = "user_type" in df.columns
    if has_user_type:
        df["user_type"] = df["user_type"].str.strip().str.title()
        ut_map = {"Annual Member": "Member", "Casual Member": "Casual"}
        df["user_type"] = df["user_type"].replace(ut_map)
        df.loc[~df["user_type"].isin(["Member", "Casual"]), "user_type"] = "Other"
    df["year"] = year
    return df


# --- Primary analysis: 2025 ---
df_2025 = load_year(2025)
df_2025 = df_2025.dropna(subset=["user_type"])
df_plot = df_2025[df_2025["user_type"].isin(["Member", "Casual"])].copy()

sns.set_style("whitegrid")

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))

for ut in ["Member", "Casual"]:
    subset = df_plot[df_plot["user_type"] == ut]
    sns.histplot(
        subset["duration_minutes"],
        bins=60,
        kde=True,
        alpha=0.5,
        label=ut,
        ax=ax1,
        stat="density",
        binrange=(0, 60),
    )

ax1.set_xlim(0, 60)
ax1.set_title("Trip duration distribution by user type")
ax1.set_xlabel("Trip duration (minutes)")
ax1.set_ylabel("Density")
ax1.legend()

sns.boxplot(
    data=df_plot[df_plot["duration_minutes"] <= 60],
    x="user_type",
    y="duration_minutes",
    order=["Member", "Casual"],
    ax=ax2,
)
ax2.set_title("Trip duration by user type")
ax2.set_ylabel("Trip duration (minutes)")
ax2.set_xlabel("")

fig.suptitle("Bike Share Toronto 2025: Trip duration analysis", fontsize=14, y=1.02)
fig.tight_layout()
fig.savefig(
    os.path.join(OUTPUTS_DIR, "trip-duration-by-user-type.png"),
    dpi=150,
    bbox_inches="tight",
)
plt.close(fig)

stats = (
    df_plot.groupby("user_type")["duration_minutes"]
    .agg(
        [
            "count",
            "mean",
            "median",
            lambda s: s.quantile(0.25),
            lambda s: s.quantile(0.75),
        ]
    )
    .reset_index()
)
stats.columns = [
    "user_type",
    "count",
    "mean_minutes",
    "median_minutes",
    "p25_minutes",
    "p75_minutes",
]
stats.to_csv(os.path.join(OUTPUTS_DIR, "trip-duration-stats.csv"), index=False)
print("2025 stats:")
print(stats.to_string(index=False))

# --- Yearly comparison: 2016-2026 ---
yearly_records = []
for year in range(2016, 2027):
    df_y = load_year(year)
    if df_y is None:
        print(f"  Skipping {year}: no trip duration column")
        continue
    has_user_type = "user_type" in df_y.columns
    if has_user_type:
        for ut in ["Member", "Casual"]:
            subset = df_y[df_y["user_type"] == ut]
            if len(subset) == 0:
                continue
            yearly_records.append(
                {
                    "year": year,
                    "user_type": ut,
                    "count": len(subset),
                    "median_minutes": round(subset["duration_minutes"].median(), 2),
                    "p25_minutes": round(subset["duration_minutes"].quantile(0.25), 2),
                    "p75_minutes": round(subset["duration_minutes"].quantile(0.75), 2),
                }
            )
    else:
        yearly_records.append(
            {
                "year": year,
                "user_type": "All",
                "count": len(df_y),
                "median_minutes": round(df_y["duration_minutes"].median(), 2),
                "p25_minutes": round(df_y["duration_minutes"].quantile(0.25), 2),
                "p75_minutes": round(df_y["duration_minutes"].quantile(0.75), 2),
            }
        )
    print(f"  Processed {year}")

yearly_df = pd.DataFrame(yearly_records)
yearly_df.to_csv(
    os.path.join(OUTPUTS_DIR, "trip-duration-yearly-stats.csv"), index=False
)
print("\nYearly stats:")
print(yearly_df.to_string(index=False))

# --- Yearly trend figure ---
fig2, ax3 = plt.subplots(figsize=(10, 6))
for ut in ["Member", "Casual"]:
    subset = yearly_df[yearly_df["user_type"] == ut]
    if len(subset) == 0:
        continue
    ax3.plot(subset["year"], subset["median_minutes"], marker="o", label=ut)

ax3.set_xlabel("Year")
ax3.set_ylabel("Median trip duration")
ax3.set_title("Bike Share Toronto: Median trip duration by year")
ax3.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"{x:.0f} min"))
ax3.set_xticks(range(2016, 2027))
ax3.legend()
fig2.tight_layout()
fig2.savefig(
    os.path.join(OUTPUTS_DIR, "trip-duration-yearly-trend.png"),
    dpi=150,
    bbox_inches="tight",
)
plt.close(fig2)

print("\nDone.")
