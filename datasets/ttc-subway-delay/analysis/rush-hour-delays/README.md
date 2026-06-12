# Rush Hour vs Off-Peak Subway Delays on Lines 1 (YU) and 2 (BD)

Dataset: `ttc-subway-delay`
Author: jeremyl14
Date: 2026-06-10

## Question (required)

How do delay frequency, severity, and cause differ between rush hours and off-peak times, on Line 1 (YU) vs Line 2 (BD)?

## Data (required)

- **Primary dataset:** `ttc-subway-delay` ([README](../../README.md))
- **Joins with:** none
- **Snapshot dates:** `raw/ttc-subway-delay-data-since-2025.csv` (fetched 2026-06-10)
- **Filters applied:** Year 2025 only; Lines YU and BD only (excludes SHP, YU/BD, blank); significant delay threshold ≥ 5 min; rush hours = weekdays 07:00–09:59 and 16:00–18:59

## Method (required)

- **Tools:** Python 3.12, pandas, numpy, matplotlib, seaborn
- **Approach:**
  1. Loaded TTC subway delay data for 2025, filtered to YU and BD lines.
  2. Classified each delay as "rush" (weekday 07:00–09:59 or 16:00–18:59) or "off-peak" (all other times).
  3. Defined "significant delay" as Min Delay ≥ 5 minutes.
  4. Produced a heatmap of mean delay duration by hour and day for significant delays (one panel per line).
  5. Produced a grouped bar chart comparing rush vs off-peak significant delay count and mean duration, with 95% bootstrap CIs on the mean.
  6. Produced a monthly line chart of significant delay rate (significant / total) for each line × period combination.
  7. Exported summary CSVs for hourly breakdown and rush/off-peak comparison.
- **Statistical test:** 95% bootstrap confidence intervals (1000 iterations) on mean delay duration for significant delays, by line and period.

## How to reproduce (required)

```bash
pip install -r requirements.txt
python analyze.py
```

Expected runtime: ~30 seconds on a laptop
Expected output: 3 figures (PNG) + 2 summary CSVs

## Results (required)

See `outputs/` for figures and tables.

| Metric | YU rush | YU off-peak | BD rush | BD off-peak |
|---|---|---|---|---|
| Significant delay count | 606 | 2,223 | 421 | 1,450 |
| Mean delay (min) | 11.75 | 11.45 | 10.90 | 11.47 |
| 95% CI on mean | [10.15, 13.87] | [10.38, 12.71] | [9.86, 12.06] | [10.74, 12.29] |

## Caveats (required)

- Rush hour definition is a fixed 07:00–09:59 / 16:00–18:59 window on weekdays; actual peak ridership varies by direction (northbound vs southbound AM rush, etc.).
- More delays are reported during service hours because more trains run; raw counts favor rush periods even if per-train rates are similar.
- `Min Delay` of 0 inflates denominators in the significant delay rate — these are reported events where duration was not recorded or was under 1 minute. The rate uses all reported events (including 0-min) as the denominator, so it understates the true proportion of delays that are serious.
- The `Bound` column is ~35% null, so direction-stratified analysis is underpowered and not attempted here.
- Analysis is limited to 2025 data only; seasonal and year-over-year trends cannot be assessed.

## Files

- `analyze.py` — main analysis script
- `requirements.txt` — pinned Python deps
- `outputs/` — figures and summary CSVs
- `outputs/.gitignore` — excludes generated PNGs from git, keeps CSVs

## Future work

- Add direction (Bound) stratification once data completeness improves.
- Compare with 2014–2024 historical data for year-over-year trends.
- Investigate delay codes (cause) by period and line.
- Per-station analysis of worst-affected stops.

---

Author: jeremyl14, 2026-06-10