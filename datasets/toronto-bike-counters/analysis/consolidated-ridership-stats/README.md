# Consolidated Ridership Stats

Dataset: `toronto-bike-counters`
Author: jeremyl14
Date: 2026-06-10

## Question (required)

What does Toronto cycling traffic look like across all permanent counters in aggregate? How does ridership vary by season, by day of week, and how has it grown (or shrunk) year-over-year when comparing the same set of counters?

## Data (required)

- **Primary dataset:** `toronto-bike-counters` ([README](../../README.md))
- **Joins with:** None
- **Snapshot dates:** Daily counts file snapshot dated 2026-06-10
- **Filters applied:**
  - Only active counters (blank `date_decommissioned` in locations file)
  - EB/WB and NB/SB direction pairs merged by summing `daily_volume` per `location_name` per date
  - 2026 excluded from annual summary (partial year, Jan–Apr only)
  - Like-for-like YoY requires counters active ≥ 200 days in both consecutive years

## Method (required)

- **Tools:** Python 3, pandas, matplotlib, numpy
- **Approach:**
  1. Loaded the daily counts and locations CSVs. Filtered to active counters only (blank `date_decommissioned`).
  2. Merged direction pairs by grouping on `location_name` + `dt` and summing `daily_volume`, yielding total daily volume per location.
  3. Computed monthly mean daily volume per location-year-month, and annual totals per location.
  4. For the seasonality chart: plotted month (1–12) vs. mean daily volume, one line per year (2022–2025), faceted by the top 4 locations by 2024 total volume.
  5. For the day-of-week chart: computed mean daily volume by day name for 2024 only, faceted by the same top 4 locations.
  6. For YoY growth: for each consecutive year pair, identified locations with ≥ 200 days of data in both years, summed their annual volumes, and computed percent change.
- **Statistical test:** No formal tests — this is a descriptive summary, not an inferential analysis.

## How to reproduce (required)

```bash
pip install -r requirements.txt
python analyze.py
```

Expected runtime: ~15 seconds on a laptop
Expected output: 3 figures (PNG) + 3 summary CSVs in `outputs/`

## Results (required)

| Year | Active counters | Total volume | Mean daily/counter | YoY % change* |
|------|----------------|-------------|-------------------|---------------|
| 2022 | 11 | 309,725 | 318.0† | — |
| 2023 | 14 | 4,259,427 | 959.5 | +62.1% |
| 2024 | 14 | 5,546,380 | 1,157.7 | +43.7% |
| 2025 | 17 | 6,915,984 | 1,410.3 | −7.7% |

*YoY % change is like-for-like only (same set of counters active >= 200 days in both years). Total volume and mean daily/counter include all active counters. The total volume grew from 5.5M to 6.9M (+25%) while the like-for-like subset declined 7.7% — the difference is driven by new counters adding volume.

†2022 data starts in May; mean daily/counter is not comparable to full-year figures.

The "always-on" subset (counters with >= 340 days in both year-pairs) shows -4.9% for 2025 (8 locations), indicating that ~3pp of the like-for-like decline is counter downtime and ~5pp is real. The decline is concentrated on Sherbourne (-8 to -15%) and Yonge/St Clair (-7%); Bloor/Palmerston grew +4%.

- **Peak month:** September 2025 at Bloor St W, west of Huron St (mean daily volume: 6,369)
- **Weekend/weekday ratio:** 0.82 (weekend mean: 931, weekday mean: 1,134)

See `outputs/` for figures and tables.

## Caveats (required)

- Like-for-like YoY comparisons only include counters active for ≥ 200 days in both consecutive years. This means the 2022→2023 comparison uses a smaller set of counters than 2023→2024, and the denominator changes across year pairs.
- The always-on subset uses ≥ 340 days in both years of each pair. The location set varies by pair (7 locations for 2023→2024, 8 for 2024→2025) because new counters qualify as they age in.
- 2022 data starts in May (not January), so its total volume and seasonal pattern are incomplete. This is reflected in the charts but not adjusted for.
- 2026 is excluded from the annual summary and YoY growth (partial year through April only).
- Daily volumes are raw counts, not normalized by counter uptime. If a counter was offline for part of a month, its "mean daily volume" for that month will be biased upward (only days with data contribute).
- The "top 4 locations" are selected by 2024 total volume. A different year or metric could yield a different set.
- The 2025 YoY decline (−7.7% like-for-like, −4.9% always-on) is partly weather-driven: February 2025 was exceptionally cold, with volumes down ~50% vs 2024 at most counters. The remaining decline is concentrated on the Sherbourne corridor (−8 to −15%) and Yonge/St Clair (−7%); Bloor/Palmerston grew +4%.

## Files

- `analyze.py` — main analysis script
- `requirements.txt` — Python dependencies
- `outputs/monthly-seasonality.png` — line chart of monthly patterns
- `outputs/day-of-week.png` — bar chart of 2024 weekday/weekend patterns
- `outputs/yoy-growth.png` — bar chart of year-over-year growth rates

- `outputs/always-on-yoy.csv` — always-on subset YoY figures
- `outputs/annual-summary.csv` — year-level summary table
- `outputs/monthly-by-location.csv` — monthly statistics per location

## Future work

- Normalize monthly volumes by counter uptime (days with data vs. calendar days) to reduce gap bias.
- Add a precipitation/temperature covariate to explain seasonal and interannual variation.
- Break out commuter vs. recreational patterns using hour-of-day from the 15-minute data.
- Add a heatmap of volume by location and month for a full overview.

---

Author: jeremyl14, 2026-06-10