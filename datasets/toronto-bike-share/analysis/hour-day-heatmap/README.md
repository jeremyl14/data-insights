# Bike Share Toronto: Trips by Hour and Day of Week

Dataset: `toronto-bike-share`
Author: analyst
Date: 2026-06-10

## Question (required)

How does bike-share trip volume in Toronto vary by hour of day and day of week? Are weekday commuting peaks visible, and how do weekend patterns differ?

## Data (required)

- **Primary dataset:** `toronto-bike-share` (link to its README)
- **Joins with:** none
- **Snapshot dates:** `raw/bike-share-toronto-ridership-2024.csv`
- **Filters applied:** 2024 data only; rows with missing start times are dropped. This analysis is **2024-only** because column names vary across years and the script uses the 2024 naming convention (`Start_Time`). Extending to other years would require column normalization (see dataset README).

## Method (required)

- **Tools:** Python 3.12, pandas 2.2, matplotlib 3.8, seaborn 0.13
- **Approach:** Load all 2024 trip records, extract hour (0-23) and day-of-week (Mon-Sun) from each trip's start time, count trips per (day, hour) cell, divide by the number of ISO weeks in the dataset to get average trips per hour per day-of-week, and display as a heatmap with annotated cell values (in thousands).
- **Key transformations:**
  1. Parsed `Start_Time` column as datetime.
  2. Extracted `hour` and `day_of_week`.
  3. Grouped by (day_of_week, hour) and counted trips.
  4. Divided by number of distinct ISO weeks to get per-week averages.
  5. Pivoted into a 7x24 matrix for the heatmap.
- **Statistical test:** None; this is a descriptive summary.

## How to reproduce (required)

```bash
pip install -r requirements.txt
python analyze.py
```

Expected runtime: ~30 seconds on a laptop
Expected output: 1 figure + 1 summary CSV

## Results (required)

Run `analyze.py` to populate.

See `outputs/` for figures and tables.

## Caveats (required)

- Single city and single year; patterns may not generalize to other bike-share systems or other years.
- No weather or holiday adjustment; holidays falling on weekdays will look like weekend patterns.
- Average is computed over ISO weeks present in the dataset; partial weeks at year boundaries (week 1 and week 52) may slightly skew counts for Monday (week 1 is partial) and other edge days. 2024 is a leap year with 366 days spanning 53 ISO weeks.
- Trips with missing or unparsable start times are excluded (a small fraction).
- Hour-of-day is local time (Eastern); no daylight-saving adjustment beyond what the timestamp encodes.
- No filtering for trip quality (e.g., very short or very long trips are included).

## Files

- `analyze.py` — main analysis script
- `requirements.txt` — pinned Python deps
- `outputs/` — figures, tables, summary CSVs

## Future work

- Overlay weather data to explain deviations from the typical pattern.
- Compare multiple years to detect trends.
- Add holiday flag to separate holiday weekdays from regular weekdays.

---

Author: analyst, 2026-06-10