# TTC Bus Route Delay Ranking

Dataset: `ttc-bus-delay`
Author: analyst
Date: 2026-06-10

## Question (required)

Which TTC bus routes accumulate the most delay in 2025, and what categories of cause (equipment, operations, infrastructure, safety, transportation) drive delays on the worst routes?

## Data (required)

- **Primary dataset:** `ttc-bus-delay` ([README](../../README.md))
- **Joins with:** `raw/ttc-bus-delay-codes.csv` on Code → CODE for delay-code descriptions
- **Snapshot dates:** `raw/ttc-bus-delay-data-since-2025.csv` (2025 data)
- **Filters applied:**
  - Date year == 2025 only
  - `Min Delay == 0` excluded from delay-minute totals (counted in total_events only)
  - "Significant delay" defined as `Min Delay >= 5` minutes
  - Route number extracted from the `Line` column (first integer) for grouping

## Method (required)

- **Tools:** Python 3.12, pandas 2.2, matplotlib 3.9, seaborn 0.13
- **Approach:** Filtered 2025 TTC bus delay records, classified each delay code into a cause category by its first letter (E=Equipment, M=Operations, P=Infrastructure, S=Safety, T=Transportation), then aggregated total significant-delay minutes by route and by route × category.
- **Key transformations:**
  1. Parsed `Date` column, filtered to year 2025.
  2. Extracted route number from `Line` (e.g. "102 MARKHAM ROAD" → 102) for grouping; used full `Line` value for display.
  3. Classified `Code` into cause categories by first letter; joined to codes CSV for descriptions.
  4. Flagged "significant delays" as `Min Delay >= 5`; excluded `Min Delay == 0` from delay-minute totals.
  5. Computed per-route summary: total events, significant-delay count, total/mean/median delay minutes, and percentage breakdown by cause category.
  6. Produced two horizontal bar charts (top 20 by total delay, top 15 stacked by cause) and two summary CSVs.
- **Statistical test:** Descriptive only — no inferential tests. Percentages represent composition of delay minutes by cause category per route.

## How to reproduce (required)

```bash
# 1. (one-time) install deps
pip install -r requirements.txt

# 2. run the analysis
python analyze.py

# 3. view outputs
open outputs/top-routes-by-delay.png
open outputs/route-cause-breakdown.png
```

Expected runtime: ~15 seconds on a laptop
Expected output: 2 figures + 2 summary CSVs

## Results (required)

See `outputs/` for figures and CSVs.

| Metric | Value |
|---|---|
| Top routes | Dominated by high-frequency routes (e.g. 36, 52, 32) |
| Largest cause category | Equipment and Operations account for the majority of delay minutes |
| Unique routes in 2025 | Reported by script output |
| Total significant delays | Reported by script output |

## Caveats (required)

- A delay logged at a stop (Station column) does not mean the stop caused it — the `Station` field refers to the bus stop/terminal where the delay was recorded, not the root cause location.
- The same incident may generate multiple rows in the dataset (e.g. one per vehicle or per code).
- `Min Delay == 0` records are excluded from delay-minute totals but counted in total_events; these are logging artifacts, not real delays.
- Route names in the `Line` column may have variants (typos, abbreviations) that cause the same physical route to appear under multiple names. ~757 rows (including ~75 significant delays) have NaN `Line` values and are grouped as "Unknown".
- No ridership weighting: a route with 100k daily riders and the same delay-minutes as one with 1k daily riders looks identical in these rankings. Per-ride or per-trip metrics would require ridership data not available here.
- This analysis covers 2025 only and may not be representative of other years.
- Cause categories are coarse (first letter of code); some codes may be misclassified by this heuristic.

## Files

- `analyze.py` — main analysis script
- `requirements.txt` — pinned Python deps
- `outputs/` — figures and summary CSVs
  - `top-routes-by-delay.png` — horizontal bar chart of top 20 routes
  - `route-cause-breakdown.png` — stacked bar chart of top 15 routes by cause
  - `route-delay-summary.csv` — per-route summary statistics
  - `route-cause-breakdown.csv` — per-route per-category breakdown

## Future work

- Weight delay minutes by ridership or trip count for a per-ride delay metric.
- Time-series view: how do the worst routes change month by month?
- Drill into specific delay codes within the dominant categories on the worst routes.
- Compare 2025 patterns to prior years if data becomes available.

---

Author: analyst, 2026-06-10