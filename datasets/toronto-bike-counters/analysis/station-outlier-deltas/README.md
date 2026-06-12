# Station Outlier Deltas: Which bike counters diverged most from their historical baseline in 2025?

Dataset: `toronto-bike-counters`
Author: jeremyl14
Date: 2026-06-10

## Question (required)

Which counter locations had the largest unexpected changes in 2025 relative to their own historical baseline? Flag stations with outlier deltas — big jumps or drops that cannot be explained by normal seasonal variation.

## Data (required)

- **Primary dataset:** `toronto-bike-counters` ([README](../../README.md))
- **Joins with:** none
- **Snapshot dates:** 2026-06-10 (daily counts + locations from `raw/`)
- **Filters applied:**
  - Only active counters (blank `date_decommissioned` in locations file)
  - Directions merged per location (EB+WB, NB+SB summed)
  - At least 3 prior years of data per month required for baseline
  - Days where one direction in a pair is missing data are excluded from merged totals
  - At least 15 days of 2025 data per month required

## Method (required)

- **Tools:** Python 3, pandas, numpy, matplotlib, seaborn
- **Approach:** For each active counter location (directions merged), compute a per-month historical baseline (mean and std of daily volume) using all years before 2025. For each month in 2025 with sufficient data, compute the delta (actual daily mean vs historical monthly mean) and a z-score (delta / historical std). Flag months where |z-score| > 2 as outliers.
- **Key transformations:**
  1. Filtered locations to active counters only (blank `date_decommissioned`).
  2. Merged direction pairs (EB+WB, NB+SB) by summing daily volumes per location per date. Excluded days where one direction in a pair has no data to prevent structural artifacts.
  3. Computed per-location, per-month, per-year mean daily volume for all pre-2025 years.
  4. Aggregated historical baseline: mean and std of yearly monthly means, requiring >= 3 prior years.
  5. Computed 2025 actual mean daily volume per location per month, requiring >= 15 days.
  6. Calculated delta = actual − historical mean, z-score = delta / historical std.
  7. Flagged |z| > 2 as outliers.
- **Statistical test:** Z-score threshold |z| > 2. With only 3+ prior years per baseline, this is a descriptive flag, not a formal hypothesis test.

## How to reproduce (required)

```bash
pip install -r requirements.txt
python analyze.py
```

Expected runtime: 15 seconds on a laptop
Expected output: 2 figures (PNG) + 2 CSVs in `outputs/`

## Results (required)

1 outlier month-event across 1 location after filtering:

| Finding | Value |
|---|---|
| Only outlier | Keele St, south of Sheppard Ave W M12: z = −2.36, delta = −6.5 bikes/day below baseline |
| Direction-filtered | Sheppard Ave W / Sentinel Rd excluded from analysis because one direction counter went offline mid-2025 |
| Qualifying locations | Only 2 locations had >= 3 prior years of direction-complete data |
| Yonge St corridor | No months flagged as outliers in 2025 (traffic appears within historical range) |

See `outputs/` for figures and tables.

## Caveats (required)

- Z-scores assume roughly normal monthly volumes; actual distributions may be skewed, especially for low-volume counters where a small absolute change produces a large z-score.
- Historical baselines require >= 3 prior years. With only 3 prior years, sample standard deviations are noisy and z-scores should be interpreted descriptively, not as formal statistical tests — the |z| > 2 threshold does not have its usual 95% confidence meaning with such small samples.
- 2025 data is partial (through ~April for most counters) — only months with sufficient data (>= 15 days) are included.
- Days where one direction counter in a pair reports no data are excluded from merged totals. This prevents a structural artifact where summing only one direction produces an apparent traffic drop. The Sheppard Ave W / Sentinel Rd WB counter went offline after May 2025; months after that are excluded from the merged total.
- Counter gaps/offline periods could make a month look like an outlier when it is just missing data. Days with only one direction reporting are excluded to prevent this artifact.
- Infrastructure changes (new bike lanes, road closures) can cause genuine structural breaks that look like outliers. The Bloor St W / Palmerston Blvd extreme positives may reflect such a change.
- Merging directions (EB+WB, NB+SB) assumes both directions are present; days where one direction is missing are excluded to prevent the sum dropping by ~50% for structural reasons.

## Files

- `analyze.py` — main analysis script
- `requirements.txt` — Python deps
- `outputs/` — figures and CSVs

## Future work

- Filter out counters with suspiciously low 2025 days-count before computing z-scores to reduce offline-counter false positives.
- Use a rolling or weighted baseline that downweights pandemic years (2020–2021).
- Add weather covariates to distinguish weather-driven drops from structural ones.
- Investigate the Bloor St W / Palmerston Blvd surge with infrastructure change data.

---

Author: jeremyl14, 2026-06-10