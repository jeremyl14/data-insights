# Rush Hour Reliability: TTC Bus Delays in 2025

Dataset: `ttc-bus-delay`
Author: jeremyl14
Date: 2026-06-10

## Question (required)

How do bus delay frequency and severity differ between rush hours and off-peak periods, and which routes are most affected during rush hour?

## Data (required)

- **Primary dataset:** `ttc-bus-delay` ([README](../../README.md))
- **Joins with:** none
- **Snapshot dates:** 2025 data only, from `raw/ttc-bus-delay-data-since-2025.csv`
- **Filters applied:** 2025 records only; "significant delay" defined as Min Delay ≥ 5 minutes

## Method (required)

- **Tools:** Python 3.12, pandas, matplotlib, seaborn, numpy
- **Approach:**
  1. Loaded all 2025 TTC bus delay records and classified each as rush hour (07:00–09:59 or 16:00–18:59, weekdays only) or off-peak (everything else).
  2. Filtered to significant delays (Min Delay ≥ 5 min) for severity analysis.
  3. Computed hourly × day-of-week mean delay heatmap, rush vs off-peak comparison with 95% bootstrap CIs, and top-15 routes by rush-hour total delay minutes.
  4. Colored route bars by whether rush mean delay exceeds off-peak mean delay for the same route.
- **Statistical test:** 95% bootstrap confidence intervals (10,000 resamples) on mean delay for rush vs off-peak. CIs overlap, so the difference in mean delay duration is not statistically clear.

## How to reproduce (required)

```bash
pip install -r requirements.txt
python analyze.py
```

Expected runtime: ~30 seconds on a laptop
Expected output: 3 figures + 3 summary CSVs

## Results (required)

| Metric | Rush hour | Off-peak |
|---|---|---|
| Total delays | 16,793 | 46,236 |
| Significant delays (≥5 min) | 14,509 | 39,861 |
| Mean delay (min) | 23.91 | 23.54 |
| 95% CI | [22.91, 24.92] | [23.05, 24.05] |
| Total delay minutes | 346,843 | 938,355 |

Top 5 rush-hour routes by total delay minutes:

| Route | Rush total min | Rush delays | Rush mean (min) |
|---|---|---|---|
| 29 DUFFERIN | 7,958 | 233 | 34.2 |
| 52 LAWRENCE WEST | 7,015 | 349 | 20.1 |
| 102 MARKHAM ROAD | 6,938 | 299 | 23.2 |
| 63 OSSINGTON | 6,442 | 227 | 28.4 |
| 162 LAWRENCE-DONWAY | 5,635 | 24 | 234.8 |

Rush-hour mean delay is slightly higher (23.91 vs 23.54 min) but the 95% CIs overlap, so the difference is not statistically clear.

See `outputs/` for figures and tables.

## Caveats (required)

- Rush hour definition is a fixed window (07:00–09:59 and 16:00–18:59, weekdays only). Actual service patterns may not align perfectly with these windows.
- More delays occur during off-peak hours in absolute count because off-peak covers more hours. Per-hour rates would tell a different story.
- Min Delay == 0 entries inflate delay counts but not duration statistics. They are excluded from significant-delay analysis but included in total counts.
- This analysis uses 2025 data only; results may not generalize to other years.
- ~757 rows have NaN `Line` values and are grouped as "Unknown" rather than dropped.
- No ridership weighting — routes with more passengers have disproportionate impact on riders affected, but we cannot measure that here.
- The 162 LAWRENCE-DONWAY route shows a very high mean delay from only 24 incidents, making that estimate unreliable.

## Files

- `analyze.py` — main analysis script
- `requirements.txt` — pinned Python deps
- `outputs/` — figures and summary CSVs

## Future work

- Normalize delay counts by scheduled service hours per route to get per-trip rates.
- Add per-hour-of-day rate analysis (delays per service hour) rather than raw counts.
- Investigate seasonal or month-over-month trends within 2025.
- Join with ridership data to weight delays by passenger volume.

---

Author: jeremyl14, 2026-06-10