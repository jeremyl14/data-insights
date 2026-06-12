# Active stations and network growth

Dataset: `toronto-bike-share`
Author: @jeremyl14
Date: 2026-06-10

## Question

How has the bike-share station network grown over time (full years only), and how does station count relate to ridership growth? What share of trips come from casual vs annual members, and how has that changed?

## Data

- **Primary dataset:** `toronto-bike-share` (2017–2025 trip data)
- **Joins with:** None (station reference not used; "active" defined by trip data)
- **Filters applied:** 2014–2015 demographics file skipped. 2016 skipped (partial year, Jul–Dec only). 2026 not yet available. Empty/blank station names dropped.
- **Snapshot dates:** Raw files as of 2026-06-10.

## Method

- **Tools:** Python 3.13, pandas 2.2, seaborn 0.13, matplotlib 3.8
- **Approach:** For each year 2017–2025, count distinct start station names appearing in the ridership CSV. A station is "active" if at least one trip originated from it that year. Also count total trips per year and break down trips by user type (casual vs member). Produce a dual-axis line chart, a bar chart of casual rider share, and a summary CSV.
- **Key transformations:**
  1. Normalize column names across years (naming conventions vary: `from_station_name` vs `Start Station Name` vs `Start_Station_Name`).
  2. Extract the start station name column after normalization, strip whitespace, drop blanks.
  3. Count distinct station names per year → `active_stations`.
  4. Count total rows per year → `total_trips`.
  5. Normalize `User_Type` labels across years: `Member`/`Annual Member` → `member`, `Casual`/`Casual Member` → `casual`.
  6. Count casual and member trips per year; compute `casual_pct`.
  7. 2016 and 2026 excluded (partial years).
- **Statistical test:** None (descriptive counts).

## How to reproduce

```bash
# 1. (one-time) get the raw data
#    dvc pull datasets/toronto-bike-share/raw/*.dvc

# 2. install deps
pip install -r requirements.txt

# 3. run the analysis
python analyze.py

# 4. view outputs
ls outputs/
```

Expected runtime: ~3–5 minutes on a laptop (reads 30M+ rows).
Expected output: 2 figures + 1 CSV.

## Results

| Year | Active stations | Total trips | Casual share |
|------|----------------|-------------|-------------|
| 2017 | 293 | 1,492,368 | ~17%* |
| 2018 | 359 | 1,922,955 | 18.2% |
| 2019 | 469 | 2,439,517 | 23.8% |
| 2020 | 679 | 2,910,515 | 35.7% |
| 2021 | 733 | 3,571,502 | 40.1% |
| 2022 | 608 | 4,136,461 | 61.9%** |
| 2023 | 592 | 5,118,066 | 93.6%** |
| 2024 | 879 | 6,953,094 | 22.8% |
| 2025 | 1,059 | 7,812,513 | 27.4% |

\* 2017: only ~31% of trips have user_type filled; casual share is of trips with known user_type only and likely underestimates the true share.
\*\* 2022 and 2023: user_type labels are unreliable — see caveats.

**Biggest station-count jumps:**
- 2023→2024: +287 stations (+48.5%) — the largest single-year expansion
- 2019→2020: +210 stations (+44.8%) — significant pre-pandemic expansion
- 2018→2019: +110 stations (+30.6%)
- 2024→2025: +180 stations (+20.5%)

**Notable declines:** Station count dropped from 733 (2021) to 608 (2022, −17.1%) and 592 (2023, −2.6%), likely due to station renaming/consolidation and data entry changes rather than actual removals.

**2017→2025 growth:** Stations grew from 293 to 1,059 — a 3.6× increase over 8 full years.

**Casual rider share:** Excluding unreliable years (2022–2023), casual share of trips grew from ~18% (2018) to ~27% (2025). The 2022 and 2023 user_type labels appear inverted (see caveats below). 2017 casual share (16.8%) is computed from only ~31% of trips that have user_type data and may not be representative.

See `outputs/active-stations-by-year.png` for the dual-axis chart and `outputs/casual-member-share.png` for the casual share bar chart.

## Caveats

- "Active" means a station had at least one trip recorded, not that it existed in the official station list. Some stations may be renamed year to year (e.g., "King/John" → "King St W / John St"); the count treats different spellings as separate stations.
- Station count may differ from official counts due to data entry variations and the rename/re-number that happened in 2019.
- 2016 and 2026 are excluded (partial years).
- 2022 is missing January data in the upstream source, which may slightly undercount active stations.
- The drop in station count from 2021 to 2022–2023 likely reflects naming consolidation rather than physical station removal; ridership continued to grow during this period.
- This analysis uses start station names only; end station names could add a small number of additional stations.
- No station ID matching is done across years (IDs were renumbered in 2019), so the year-over-year comparison is by name, not by unique station identity.
- **2023 user_type labels are unreliable.** The source data labels 93.6% of trips as "Casual Member" — a dramatic and implausible inversion from 2022 (61.9%) and 2024 (22.8%). This is almost certainly a labeling bug in the 2023 upstream data. Casual share for 2023 should not be interpreted as real.
- **2022 user_type labels are also suspect.** The 61.9% casual share in 2022 is higher than any other year except 2023, and given the 2023 labeling bug, 2022 may also be affected. The upstream used "Casual Member"/"Annual Member" labels in 2018–2023; the 2022 ratios may also reflect a partial label swap.
- **2017 user_type coverage is low.** Only ~31% of trips have a user_type value; casual share for 2017 is computed from that subset only and may not be representative.

## Files

- `analyze.py` — main analysis script
- `requirements.txt` — pinned Python deps
- `outputs/` — generated figures and CSVs
  - `active-stations-by-year.png` — dual-axis line chart
  - `casual-member-share.png` — bar chart of casual rider share by year
  - `station-count-by-year.csv` — summary data

---

Author: @jeremyl14, 2026-06-10