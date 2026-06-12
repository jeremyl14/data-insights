# User Type Trends in Bike Share Toronto

Dataset: `toronto-bike-share`
Author: data-insights-analyst
Date: 2026-06-10

## Question (required)

How has the split between Member and Casual riders evolved over time in Toronto's bike share system? Are casual rides growing faster or slower than annual memberships?

## Data (required)

- **Primary dataset:** `toronto-bike-share` ([README](../../README.md))
- **Joins with:** None
- **Snapshot dates:** `raw/bike-share-toronto-ridership-{year}.csv` for years 2016--2026 (2014--2015 excluded: no user_type column)
- **Filters applied:** Rows with missing or unparseable start timestamps dropped; user_type values normalized ("Annual Member" -> "Member", "Casual Member" -> "Casual")

## Method (required)

- **Tools:** Python 3, pandas 2.2, matplotlib 3.8, seaborn 0.13
- **Approach:** Loaded each yearly ridership CSV, normalized column names to lowercase-with-underscores, mapped user_type values to a consistent Member/Casual taxonomy, extracted year and month from the trip start timestamp, counted trips per (year, month, user_type), then plotted a 3-month centered rolling average as two time-series lines.
- **Key transformations:**
  1. Renamed `trip_start_time` -> `start_time` so both column variants merge cleanly.
  2. Mapped `"Annual Member"` and `"Casual Member"` (2019--2023) to `"Member"` / `"Casual"` to match 2016--2018 and 2024--2026 terminology.
  3. Computed a 3-month centered rolling mean per user type to smooth seasonal noise.
- **Statistical test:** None; this is a descriptive time-series plot, not an inferential analysis.

## How to reproduce (required)

```bash
pip install -r requirements.txt
python analyze.py
```

Expected runtime: ~2 minutes on a laptop (years 2020+ have >1M rows each)
Expected output: 1 figure + 2 summary CSVs

## Results (required)

Run analyze.py to populate.

See `outputs/` for figures and tables.

## Caveats (required)

- User-type labeling changed across years; "Annual Member" (2019--2023) is assumed equivalent to "Member" (2016--2018, 2024--2026), and "Casual Member" is assumed equivalent to "Casual". The underlying membership product may have changed (e.g. new pass types introduced), so the mapping may not be exact.
- 2020 ridership was heavily impacted by COVID-19 lockdowns; the drop and recovery pattern in that year should not be compared to baseline years without context.
- Data for 2026 is partial (year-to-date at snapshot time), so the most recent months will be incomplete.
- No weather, holiday, or station-coverage covariates are included; seasonal patterns likely reflect weather more than user-type preference shifts.
- The rolling average masks within-month variation and edge effects at series boundaries.

## Files

- `analyze.py` — main analysis script
- `requirements.txt` — pinned Python deps
- `outputs/` — figures and summary CSVs

---

Author: data-insights-analyst, 2026-06-10