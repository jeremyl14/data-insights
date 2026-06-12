# Ridership Time Series

Dataset: `toronto-bike-share`
Author: @jeremyl14
Date: 2026-06-11

## Question

What does Bike Share Toronto daily ridership look like on a single continuous time axis from 2017 to 2026?

## Data

- **Primary dataset:** `toronto-bike-share` ([README](../../README.md))
- **Joins with:** 311 bike infrastructure complaints (2025 only, from `raw/311-bike-infrastructure-daily-2025.csv`)
- **Snapshot dates:** Raw ridership CSVs as of 2026-06-10
- **Filters applied:**
- Years 2017–2026 (2016 partial Jul–Dec excluded; 2026 Jan–Mar included)
- Rows with unparseable start_time dropped

## Method

- **Tools:** Python 3, pandas, seaborn, matplotlib
- **Approach:**
  1. Loaded each year's ridership CSV, normalized column names.
  2. Counted trips per calendar date across all years.
  3. Computed a 7-day centered moving average to smooth day-to-day noise.
  4. Plotted daily trips (shaded area) and moving average (line) on a continuous date axis with alternating year bands and annual total annotations.
  5. Overlaid 311 bike infrastructure complaints for 2025 as bars on a secondary y-axis (orange).
- **Statistical test:** None — descriptive time series.

## How to reproduce

```bash
pip install -r requirements.txt
python analyze.py
```

Expected runtime: ~2–3 minutes (loads ~36M rows)
Expected output: 1 figure (PNG) + 3 CSVs in `outputs/`

## Results

| Year | Total trips |
|------|------------|
| 2017 | 826,915 |
| 2018 | 1,922,955 |
| 2019 | 2,439,517 |
| 2020 | 2,911,059 |
| 2021 | 3,575,182 |
| 2022 | 4,300,240 |
| 2023 | 5,713,141 |
| 2024 | 6,953,094 |
| 2025 | 7,812,520 |
| 2026 | 552,073 (Jan–Mar only) |

Ridership has grown every year from 2017 to 2025. The seasonal
oscillation (summer peak, winter trough) amplifies over time as the
system expands. The 2020 pandemic year still shows growth in raw counts,
but this conflates system expansion with demand recovery. Alternating year
bands with annual total annotations (e.g. 0.8M, 1.9M, ... 7.8M) make
the growth trajectory easy to read at a glance.

The 311 overlay for 2025 shows bike infrastructure complaint spikes in
February (peak: 50 complaints on Feb 19) and December, coinciding with
winter snow events. These are mostly "Bike Lane Winter Maintenance
Required" complaints — indicating uncleared bike lanes during snow
periods.

## Caveats

- 2022 is missing January data from the upstream ZIP, so its annual total undercounts by ~1 month.
- Year-over-year growth conflates system expansion (new stations, more bikes) with increased per-station demand. This is a system-level metric, not a demand metric.
- The 2020–2021 pandemic period had station closures; ridership reflects both reduced demand and reduced availability.
- 2026 is partial-year (Jan–Mar only) and appears as the trailing edge of the plot.
- No adjustment for station coverage or fleet size. A per-station or per-bike normalization would show a different pattern.
- The official open data lags 2–3 months; third-party sources (BikeRacoon) provide more timely estimates but those are inferred from station availability changes, not official trip records (~2% undercount).
- 311 data is only available for 2025; it is shown on a secondary axis to provide context for winter ridership dips, not for direct comparison with ridership volume.
- 311 complaint volume reflects public reporting behavior, not necessarily the severity of the problem. Low complaint counts could mean good service or low awareness, not just good clearing.

## Files

- `analyze.py` — main analysis script
- `requirements.txt` — Python dependencies
- `outputs/ridership-time-series.png` — daily ridership with year bands and annual totals
- `outputs/daily-rides.csv` — daily trip counts
- `outputs/cumulative-by-year.csv` — cumulative trips by year and day-of-year
- `outputs/summary.csv` — yearly totals