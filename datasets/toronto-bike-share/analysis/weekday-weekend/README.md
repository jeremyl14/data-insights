# Weekday vs weekend daily ridership

Dataset: `toronto-bike-share`
Author: jeremy
Date: 2026-06-10

## Question (required)

How does Bike Share Toronto ridership differ between weekdays and weekends over time, and has that gap changed as the system has grown?

## Data (required)

- **Primary dataset:** `toronto-bike-share` ([README](../../README.md))
- **Joins with:** none
- **Snapshot dates:** `raw/bike-share-toronto-ridership-{2016..2026}.csv`
- **Filters applied:** Rows with unparseable start timestamps are dropped.

## Method (required)

- **Tools:** Python 3.12, pandas 2.2, matplotlib 3.8, seaborn 0.13
- **Approach:** Load all ridership CSVs (2016-2026), normalizing column names to snake_case. Classify each trip as weekday or weekend based on the day-of-week of `trip_start_time`/`start_time`. Group by (year, month, is_weekend) and compute total trips and average daily trips (total trips divided by the count of distinct calendar days in that group). Plot a 3-month centered rolling average of avg daily trips for weekday and weekend, using the seaborn whitegrid theme.
- **Key transformations:**
  1. Column names normalized: strip whitespace, lowercase, replace spaces with underscores.
  2. Datetime column identified as `trip_start_time` or `start_time` after normalization.
  3. `is_weekend` = Saturday or Sunday (dayofweek >= 5).
  4. Monthly avg daily trips = total trips in that month-group / number of distinct calendar days in that month-group.
  5. 3-month centered rolling average applied for smoothing.

## How to reproduce (required)

```bash
pip install -r requirements.txt
python analyze.py
```

Expected runtime: 1-2 minutes on a laptop
Expected output: 1 figure (`weekday-weekend-monthly.png`) + 2 CSVs

## Results (required)

Run analyze.py to populate.

## Caveats (required)

- 2016 data starts in July; months before that are absent, not zero.
- 2026 data is partial (year-to-date at time of snapshot).
- 2020 ridership was severely affected by COVID-19 lockdowns; comparisons across that period should be interpreted carefully.
- `avg_daily_trips` divides by the number of distinct calendar days in the group (weekday vs weekend days in that month), so months with missing days (e.g. partial data at start/end of year) will undercount.
- No weather or holiday adjustments; weekday ridership on statutory holidays is classified as weekday but behaves more like weekend.
- Column naming and encoding vary across years; normalization handles known variants but may miss edge cases.

## Files

- `analyze.py` - main analysis script
- `requirements.txt` - pinned Python deps
- `outputs/` - figures and summary CSVs

---

Author: jeremy, 2026-06-10