# Net station flow — Bike Share Toronto 2025

Dataset: `toronto-bike-share`
Author: jeremy
Date: 2026-06-10

## Question (required)

Which bike-share stations in Toronto have the largest imbalance between departures and arrivals in 2025? Stations that export bikes (more departures than arrivals) may be located at hilltops or transit hubs, while stations that import bikes (more arrivals than departures) may sit at downhill destinations or popular endpoints.

## Data (required)

- **Primary dataset:** `toronto-bike-share` ([README](../../README.md))
- **Joins with:** None
- **Snapshot dates:** `raw/bike-share-toronto-ridership-2025.csv`
- **Filters applied:** 2025 data only; no trip-duration or station-name filters applied

## Method (required)

- **Tools:** Python 3.12, pandas 2.2, matplotlib 3.8, seaborn 0.13
- **Approach:** For each station, count departures (trip starts) and arrivals (trip ends), then compute net flow = departures − arrivals. Rank stations by absolute net flow and display the top 15 most imbalanced.
- **Key transformations:**
  1. Loaded 2025 ridership CSV; normalized column names to `start_station_name`, `end_station_name`.
  2. Counted departures per station (`start_station_name` value counts) and arrivals per station (`end_station_name` value counts).
  3. Joined into a single table, filled missing stations with zero, computed `net_flow = departures − arrivals`.
  4. Selected top 15 stations by `|net_flow|` for the chart.
- **Statistical test:** Descriptive only; no inferential statistics.

## How to reproduce (required)

```bash
pip install -r requirements.txt
python analyze.py
```

Expected runtime: ~30 seconds on a laptop
Expected output: 1 figure (`outputs/net-station-flow-2025.png`) + 1 summary CSV (`outputs/net-station-flow-2025.csv`)

## Results (required)

Run `analyze.py` to populate. The CSV contains columns: `station_name`, `departures`, `arrivals`, `net_flow`.

See `outputs/` for figures and tables.

## Caveats (required)

- Net flow does not account for rebalancing operations (staff moving bikes between stations), which would reduce apparent imbalances.
- Station names may change across the year; this analysis treats names as-is without deduplication (e.g., minor spelling variants count as separate stations).
- A single city's bike-share system; not generalizable to other systems.
- 2025 data only; seasonal patterns may cause different stations to appear imbalanced in different months.
- The analysis counts all trips equally regardless of user type (annual member vs. casual).
- **NaN end stations:** ~924 trips in 2025 have a missing `end_station_name`. These trips are counted as departures from their origin station but are **not** counted as arrivals at any destination. This biases net flow toward "exporter" status for stations that are origins of these trips. The effect is small (~0.01% of trips) but systematic.

## Files

- `analyze.py` — main analysis script
- `requirements.txt` — pinned Python deps
- `outputs/` — figures and summary CSV

## Future work

- Month-by-month net flow to identify seasonal patterns.
- Merge with station elevation data to test the "hilltop exporter" hypothesis.
- Compare net flow by user type (casual vs. annual member).

---

Author: jeremy, 2026-06-10