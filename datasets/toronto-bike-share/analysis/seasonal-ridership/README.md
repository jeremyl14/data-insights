# Seasonal ridership patterns

Dataset: `toronto-bike-share`
Author: @jeremyl14
Date: 2026-06-10

## Question

How does Bike Share Toronto ridership vary across the year, and how has
the seasonal pattern changed from 2016 to 2026?

## Data

- **Primary dataset:** `toronto-bike-share`
- **Years used:** 2016–2026 (2016 starts in July; 2026 is partial, Jan–Mar)
- **Filters applied:** Rows with timestamps outside 2014–2030 are excluded
  (removes a misparsed year-2000 row in the 2016 file).

## Method

- **Tools:** Python 3.13, pandas 2.2, seaborn 0.13, matplotlib 3.8
- **Approach:** Aggregate individual trips to daily counts per year, then
  compute a 7-day centered moving average per year to smooth day-to-day
  noise. Plot each year as a separate line on a day-of-year axis.
- **Key transformations:**
  1. Normalize column names across years (varying naming conventions).
  2. Parse start time as datetime, filter implausible years.
  3. Group by (year, date) → count trips per day.
  4. Per year, compute 7-day centered rolling average (min 3 observations).
  5. Plot daily rides vs day-of-year with month labels.

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

Expected runtime: ~2–3 minutes on a laptop (loads 30M+ rows across all years).
Expected output: 1 figure + 2 CSVs (daily-rides.csv, yearly-totals.csv).

## Results

| Year | Total trips |
|------|------------|
| 2016 | 367,961 |
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

Ridership has grown every year except the pandemic dip in 2020 (which
still showed growth over 2019 in raw numbers, partly due to expanded
station coverage). The seasonal pattern is consistent: peak in
July–August, trough in January–February.

## Caveats

- 2016 starts in July (partial year); 2026 ends in March (partial year).
  Both are included in the plot but the daily counts and moving averages
  reflect only the months present in the data.
- 2022 is missing January data in the upstream ZIP.
- Single city; not generalizable to other bike-share systems.
- Pandemic-era service reductions (2020–2021) are not annotated in the
  upstream data. Ridership during this period reflects both reduced
  demand and reduced station availability.
- Station coverage expanded significantly in 2022 (new downtown stations).
  Year-over-year growth conflate system expansion with demand growth.

## Files

- `analyze.py` — main script
- `requirements.txt` — pinned Python deps
- `outputs/` — figures and CSVs (generated; `daily-rides.csv` and
  `yearly-totals.csv` are tracked, PNG figures are gitignored)