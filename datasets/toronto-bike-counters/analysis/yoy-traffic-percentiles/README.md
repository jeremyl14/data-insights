# Toronto Bike Counters 2025: Year-over-Year Traffic Percentiles

Dataset: `toronto-bike-counters`
Author: jeremyl14
Date: 2026-06-10

## Question (required)

How does each counter's 2025 daily cycling volume compare to its own history? Which locations are seeing record-high traffic in 2025, and which are below their historical norms?

## Data (required)

- **Primary dataset:** `toronto-bike-counters` ([README](../../README.md))
- **Joins with:** None
- **Snapshot dates:** Daily counts and locations files fetched 2026-06-10
- **Filters applied:** Excluded retired counters (where `date_decommissioned` is not blank). Required >= 100 days of data per year for a year to count. Required >= 3 prior years of data for a counter to qualify for percentile ranking. Only active counters included.

## Method (required)

- **Tools:** Python 3.12, pandas 2.2, matplotlib 3.9, seaborn 0.13, numpy 2.1
- **Approach:** For each active counter direction and for combined-direction pairs (EB+WB or NB+SB), computed the mean daily volume for each calendar year with >= 100 days of data. The 2025 percentile rank is the fraction of prior years with a lower mean daily volume. For example, if a counter has 3 prior years and 2025 is the highest, its percentile is 3/3 = 100%. Combined-direction volumes are the sum of both directions' daily means.
- **Key transformations:**
  1. Filtered out retired counters from the locations file.
  2. Grouped daily counts by `location_dir_id` and year; computed mean daily volume and day count per year.
  3. Dropped years with < 100 days of data (incomplete coverage).
  4. Paired EB/WB and NB/SB counters at the same `location_name` into combined entries by summing daily means.
  5. For each qualifying group (>= 3 prior years + valid 2025), computed the percentile rank of 2025 within its own history.
- **Statistical test:** No formal test — percentile ranking is descriptive. With only 3 prior years per counter, sample sizes are too small for robust inference.

## How to reproduce (required)

```bash
# 1. (one-time) install deps
pip install -r requirements.txt

# 2. run the analysis
python analyze.py

# 3. view outputs
open outputs/percentile-rank-chart.png
open outputs/directional-breakdown.png
```

Expected runtime: ~5 seconds on a laptop
Expected output: 2 figures + 2 summary CSVs + 1 excluded-counters CSV

## Results (required)

Only 2 out of 17 active counter locations had sufficient data (>= 3 prior years + >= 100 days in 2025) to compute a meaningful percentile rank. Most Toronto bike counters were installed in 2022-2023 and have only 2 prior years of data.

| Location | Direction | Rank | Percentile | 2025 Mean/Day | Hist Avg/Day | Change vs Avg |
|---|---|---|---|---|---|---|
| Keele St, south of Sheppard Ave W | Combined | 3/3 | 66.7% | 37.2 | 36.1 | +3.1% |
| Keele St, north of Four Winds Dr | Combined | 2/3 | 33.3% | 68.0 | 76.9 | -11.6% |
| Keele St, south of Sheppard Ave W | Northbound | 3/3 | 66.7% | 20.5 | 19.6 | +4.3% |
| Keele St, south of Sheppard Ave W | Southbound | 3/3 | 66.7% | 16.7 | 16.5 | +1.6% |
| Keele St, north of Four Winds Dr | Southbound | 3/3 | 66.7% | 40.3 | 39.2 | +2.8% |
| Keele St, north of Four Winds Dr | Northbound | 1/3 | 0.0% | 27.7 | 37.7 | -26.6% |

- **Record highs:** None — no counter ranked 1st out of all its prior years.
- **Below average:** Keele St north of Four Winds Dr (Combined: 33rd percentile; Northbound direction: 0th percentile, its lowest year on record).
- 30 counter-directions excluded for insufficient data (see `outputs/excluded-counters.csv`).

See `outputs/` for figures and tables.

## Caveats (required)

- **Most counters excluded:** 15 of 17 active locations were excluded because they had fewer than 3 prior years of data. This analysis only covers 2 locations in the Keele St area — it does not represent city-wide trends.
- **2025 is a full year in this snapshot:** The data includes all of 2025 (364/365 days), so seasonal bias is not a concern for 2025 specifically. However, 2026 data (through April only) is excluded from the percentile analysis.
- **Small sample sizes:** Percentile ranks are based on only 3 prior years per counter. A rank of "3/3" (100th percentile) or "1/3" (0th percentile) could easily shift with one more year of data. These percentiles are not statistically robust.
- **Counter gaps/offline periods:** Years with < 100 days of data are dropped, but counter downtime within qualifying years may still bias means (e.g., if a counter was offline during a low-traffic month, its annual mean would be inflated).
- **Retired counters excluded:** The longest-running location (Bloor St at Castle Frank Rd, 1994-2019) was decommissioned and is excluded. There is no counter in the dataset with more than ~3-4 prior years.
- **Technology differences:** Some older retired counters used "Induction - Other" technology; all active counters use Eco-Counter. Year-over-year comparisons are within-counter, so technology differences don't affect percentiles, but they limit cross-counter comparisons.
- **Seasonal composition:** For years where a counter came online mid-year, the mean daily volume reflects only the months the counter was active. For example, a counter activated in June would have a higher annual mean (summer months only) than a full-year mean.
- **Combined-direction sums:** The combined (EB+WB or NB+SB) percentile ranks double-count traffic at each location — a cyclist passing both loops is counted twice. This is intentional (it reflects total counter passes) but means combined volumes are not cyclist counts.

## Files

- `analyze.py` — main analysis script
- `requirements.txt` — pinned Python deps
- `outputs/` — figures, tables, summary CSVs
  - `percentile-rank-chart.png` — horizontal bar chart of 2025 percentile ranks
  - `directional-breakdown.png` — yearly mean volumes for top qualifying locations
  - `percentile-ranks.csv` — all qualifying counter percentile ranks
  - `yearly-means.csv` — yearly mean daily volumes for all active counters
  - `excluded-counters.csv` — list of excluded counters and reasons

## Future work

- Re-run in future years as more counters accumulate 3+ prior years — the analysis will become more informative as the time series grows.
- Consider month-over-month comparison (e.g., Jan-Apr 2025 vs Jan-Apr of prior years) to control for partial-year effects if future snapshots don't have a complete 2025.
- Add a seasonal adjustment (e.g., compute percentile within-month) to account for winter/summer traffic differences.
- Include retired counters' historical data as context (separate percentile calculation) once enough active counters have longer histories.

---

Author: jeremyl14, 2026-06-10