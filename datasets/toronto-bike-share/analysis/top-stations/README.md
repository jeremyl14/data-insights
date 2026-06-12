# Top Stations by Total Departures Over Time

Dataset: `toronto-bike-share`
Author: jeremy
Date: 2026-06-10

## Question (required)

Which 10 Bike Share Toronto stations have the highest total departure count across 2016–2026, and how has each station's annual ridership changed over that period?

## Data (required)

- **Primary dataset:** `toronto-bike-share` (see [README](../../README.md))
- **Joins with:** none
- **Snapshot dates:** raw CSVs for years 2016–2026
- **Filters applied:** rows with missing or blank departure station names are dropped

## Method (required)

- **Tools:** Python 3, pandas 2.2, matplotlib 3.8, seaborn 0.13
- **Approach:** For each year from 2016 to 2026, load the ridership CSV, normalize column names (strip whitespace, lowercase, replace spaces with underscores), and identify the departure station column (`from_station_name` or `start_station_name`). Count departures per station per year. Sum total departures across all years to select the top 10 stations. Plot each top station's annual trip count as a line over time.
- **Key transformations:**
  1. Column name normalization to handle schema changes across years.
  2. Group by (year, station_name) and count rows to get annual departures.
  3. Rank stations by total departures across all years; select top 10.
  4. Line plot of annual departures per top-10 station.
- **Statistical test:** none (descriptive summary)

## How to reproduce (required)

```bash
pip install -r requirements.txt
python analyze.py
```

Expected runtime: ~30 seconds on a laptop
Expected output: 1 figure + 1 summary CSV

## Results (required)

Run analyze.py to populate.

| Finding | Value |
|---|---|
| Top station (all years combined) | (see CSV) |
| Year range | 2016–2026 |

See `outputs/` for figures and tables.

## Caveats (required)

- Column names and schemas vary across years; the analysis normalizes them, but subtle mismatches (e.g. trailing whitespace in station names) could split counts for the same physical station.
- Station names may change between years (renames, relocations) without a crosswalk, so the same physical station may appear under different names.
- The analysis counts departures only; arrival counts are not considered.
- 2020 ridership was significantly affected by COVID-19; year-over-year comparisons should account for this.
- Some years may have partial data (e.g. if the dataset was mid-year); totals reflect what is in the raw files.
- Station name "NULL" or blank entries are excluded; this may undercount trips where the station was not recorded.

## Files

- `analyze.py` — main analysis script
- `requirements.txt` — pinned Python deps
- `outputs/` — figures, tables, summary CSVs

## Future work

- Merge station names that refer to the same location (using station ID crosswalk if available).
- Add arrival counts for a fuller picture of station activity.
- Normalize by number of docks per station to get utilization rates.

---

Author: jeremy, 2026-06-10