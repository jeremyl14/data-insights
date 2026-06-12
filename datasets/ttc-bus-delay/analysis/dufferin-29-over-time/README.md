# TTC Bus Route 29 (Dufferin): Delay Trends Over Time

Dataset: `ttc-bus-delay`
Author: jeremyl14
Date: 2026-06-10

## Question (required)

How does the 29 Dufferin bus route's delay performance change over time? Is it getting worse, better, or stable — and what's driving the changes?

## Data (required)

- **Primary dataset:** `ttc-bus-delay` ([README](../../README.md))
- **Joins with:** `raw/ttc-bus-delay-codes.csv` on Code → CODE for delay-code descriptions
- **Snapshot dates:** `raw/ttc-bus-delay-data-since-2025.csv` (snapshot 2026-06-10)
- **Filters applied:**
  - Date >= 2025-01-01 (full available range through 2026-04-30)
  - Route 29 Dufferin: `Line` starts with "29 ", "29C ", "929 ", or exact match "29"/"929" (catches express and short-turn variants)
  - `Line` NaN filled with "Unknown" before filtering
  - "Significant delay" = `Min Delay >= 5` minutes
  - `Min Delay == 0` excluded from delay-minute totals

## Method (required)

- **Tools:** Python 3.12, pandas, matplotlib, seaborn, numpy
- **Approach:** Filtered TTC bus delay records (Jan 2025 – Apr 2026) to Route 29 Dufferin variants, classified each delay code into a cause category by its first letter (E=Equipment, M=Operations, P=Infrastructure, S=Safety/Security, T=Transportation), then aggregated delay metrics by year-month. Produced trend charts, a cause-mix stacked bar, and a top-codes heatmap.
- **Key transformations:**
  1. Parsed `Date` column, filtered to Date >= 2025-01-01.
  2. Filled NaN `Line` with "Unknown"; filtered to rows where `Line` starts with "29 ", "29C ", "929 ", or exact match "29"/"929".
  3. Classified `Code` into cause categories by first letter; joined to codes CSV for descriptions.
  4. Flagged "significant delays" as `Min Delay >= 5`; excluded `Min Delay == 0` from delay-minute totals.
  5. Computed per-year-month summary: total events, significant-delay count, total/mean/median delay minutes, and percentage breakdown by cause category.
  6. Built a code × month breakdown for the top 8 delay codes by total delay minutes.
- **Statistical test:** Descriptive only — no inferential tests. Percentages represent composition of delay minutes by cause category per month.

## How to reproduce (required)

```bash
# 1. (one-time) install deps
pip install -r requirements.txt

# 2. run the analysis
python analyze.py

# 3. view outputs
open outputs/monthly-delay-trend.png
open outputs/monthly-cause-mix.png
open outputs/top-codes-monthly.png
```

Expected runtime: ~10 seconds on a laptop
Expected output: 3 figures + 2 summary CSVs

## Results (required)

| Finding | Value |
|---|---|
| Date range | Jan 2025 – Apr 2026 (16 months) |
| Trend | Apparent decline from spring to fall is driven almost entirely by MFDV (On Diversion); non-MFDV delay minutes are flat (~1,200–1,900 min/month) across all 16 months. The July "drop" is the absence of diversions, not improved service. |
| Peak month | 2025-03 (8,087 total delay min; 6,351 from MFDV alone) |
| Lowest month | 2026-04 (1,221 total delay min; 243 from MFDV) |
| Top delay code | MFDV (On Diversion) — 27,928 min, dominant across all months |
| 2nd-largest code | EFO (Other Equipment) — 4,740 min |
| 3rd-largest code | TFCNO (No Operator Available) — 3,077 min |
| Dominant category | Operations (60–88% of delay minutes per month) |
| Category shift | Operations share declines from ~84% in spring 2025 to ~40–55% in fall, but this is driven by MFDV (On Diversion) declining; the remaining cause mix is relatively stable |
| Context | RapidTO priority bus lanes installed Nov–Dec 2025 (King to Dundas); northern segment (Dundas to Bloor) scheduled Apr–May 2026. MFDV spikes align with construction periods. |

See `outputs/` for figures and CSVs.

## Caveats (required)

- **16 months of data** — Jan 2025 through Apr 2026. Early 2026 months are partial and may not be representative of a full year.
- **No ridership or trip-count normalization** — routes with more service naturally have more delays in absolute terms. Monthly changes may reflect service-level changes rather than reliability changes.
- **Route name matching is approximate** — the filter catches "29 DUFFERIN", "29C DUFFERIN", "929 DUFFERIN EXPRESS", and several variants, but could miss rare typos or non-standard entries; some rows appear with truncated names (e.g. "929 DUFFERIN EXPRESS (").
- **MFDV (On Diversion) dominates** — this single code accounts for the majority of delay minutes and likely reflects planned route diversions (construction, events) rather than unplanned service failures. Interpretations of "getting worse" should separate diversion delays from other causes.
- **Code categories are coarse** — the first-letter mapping lumps disparate codes together; "EFO" (Other Equipment) and "MFO" (Other Operations) are catch-all buckets.
- **The RapidTO Dufferin Street project** (approved by City Council in July 2025, Item EX25.4) installed priority bus lanes from King St W to Dundas St W in November–December 2025, with the northern segment (Dundas to Bloor/Dufferin Station) scheduled for April–May 2026. Construction and lane closures likely contributed to diversion delays (MFDV) during this period. The March 2025 spike coincides with pre-construction planning and early work. See: https://www.toronto.ca/services-payments/streets-parking-transportation/transportation-projects/rapidto/rapidto-dufferin-street/
- **Same incident may generate multiple rows** (one per vehicle or per code), inflating counts.
- **`Min Delay == 0` records** are excluded from delay-minute totals but counted in total_events; these are logging artifacts.

## Files

- `analyze.py` — main analysis script
- `requirements.txt` — pinned Python deps
- `outputs/` — figures and summary CSVs
  - `monthly-delay-trend.png` — dual-panel line chart of significant delay count and total delay minutes by month
  - `monthly-cause-mix.png` — stacked bar chart of delay cause categories by month
  - `top-codes-monthly.png` — heatmap of top 8 delay codes by month
  - `monthly-summary.csv` — per-month summary statistics
  - `code-monthly-breakdown.csv` — per-code per-month breakdown

## Future work

- Normalize by ridership or scheduled trip count to distinguish reliability from volume effects.
- Separate MFDV (On Diversion) from other Operations codes to isolate planned vs unplanned delays.
- Compare Route 29 against other high-frequency routes to determine if trends are route-specific or system-wide.
- Investigate the March 2025 spike with external context (construction projects, service advisories).
- Compare delays before and after RapidTO lane installation (Nov 2025) to evaluate whether priority lanes reduced Route 29 delays.

---

Author: jeremyl14, 2026-06-10