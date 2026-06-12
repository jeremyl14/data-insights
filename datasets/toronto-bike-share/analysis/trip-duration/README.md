# Trip duration analysis

Dataset: `toronto-bike-share`
Author: analyst
Date: 2026-06-10

## Question (required)

How does trip duration differ between Member and Casual users of Bike Share Toronto in 2025? Has the pattern changed across years (2016-2026)?

## Data (required)

- **Primary dataset:** `toronto-bike-share` ([README](../../README.md))
- **Joins with:** None
- **Snapshot dates:** 2016-2026 ridership CSVs
- **Filters applied:** Trips shorter than 30 seconds or longer than 24 hours excluded as implausible. Only Member and Casual user types retained for user-type breakdowns. 2014-2015 excluded (no trip duration column).

## Method (required)

- **Tools:** Python 3.12, pandas 2.2, seaborn 0.13, matplotlib 3.8
- **Approach:**
  1. **2025 primary analysis:** Loaded 2025 ridership data, normalized column names, auto-detected duration unit (median > 100 implies seconds; converted to minutes), filtered implausible durations, and produced a density histogram and box plot comparing Member vs Casual trip durations (capped at 60 minutes for visibility). Computed summary statistics by user type.
  2. **Yearly comparison (2016-2026):** Loaded all available year files, normalized column names (handling variations: `trip_duration_seconds` in 2016-2018, `Trip  Duration` in 2019-2023 which normalizes to `trip__duration`, `Trip_Duration` in 2024-2026), converted durations to minutes using the same auto-detection logic, and computed median trip duration by year and user type. Produced a line plot and a summary CSV.
- **Key transformations:**
  1. Normalized column names (lowercase, underscores, collapsed double underscores from `"Trip  Duration"`).
  2. Auto-detected duration unit: median > 100 implies seconds; converted to minutes.
  3. Filtered durations outside [30s, 24h].
  4. Standardized user_type to title case.
- **Statistical test:** Descriptive comparison; no formal hypothesis test.

## How to reproduce (required)

```bash
pip install -r requirements.txt
python analyze.py
```

Expected runtime: ~10 minutes on a laptop (38M rows across all years)
Expected output: 2 figures + 2 summary CSVs

## Results (required)

Run analyze.py to populate.

| Finding | Value |
|---|---|
| 2025 Member median duration | (run analyze.py) |
| 2025 Casual median duration | (run analyze.py) |

See `outputs/` for figures and tables.

## Caveats (required)

- Duration unit was inferred (seconds vs minutes) based on median value; if upstream changes the column unit, results will shift.
- Column names vary across years: 2016-2018 use `trip_duration_seconds`, 2019-2023 use `Trip  Duration` (with double space), and 2024-2026 use `Trip_Duration`. The script normalizes all variants, but double-underscore artifacts from the double-space column are collapsed automatically.
- Trips under 30 seconds are likely false starts or dock errors; trips over 24 hours are likely forgotten bikes. Both are excluded, which may undercount extreme usage patterns.
- The 60-minute cap on visualizations excludes long tail observations; summary statistics are computed on the full filtered range.
- User type classification (Member vs Casual) is as reported by the system; it may not reflect actual membership status at trip time.
- The yearly comparison covers 2016-2026; 2014-2015 are excluded because they lack a trip duration column. 2016 has user_type but only Member and Casual labels.
- 2026 data is partial-year (Jan-May approximately), so its median will not be comparable to full years.

## Files

- `analyze.py` — main analysis script
- `requirements.txt` — pinned Python deps
- `outputs/` — figures and summary CSVs
  - `trip-duration-by-user-type.png` — 2025 distribution + box plot
  - `trip-duration-yearly-trend.png` — median trip duration by year (2016-2026)
  - `trip-duration-stats.csv` — 2025 summary statistics by user type
  - `trip-duration-yearly-stats.csv` — yearly summary statistics by user type

## Future work

- Add hourly or day-of-week breakdowns.
- Investigate the relationship between trip duration and station distance.
- Add confidence intervals to the yearly trend via bootstrap.

---

Author: analyst, 2026-06-10