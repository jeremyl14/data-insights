# TTC Bus Delay Cause Taxonomy

Dataset: `ttc-bus-delay`
Author: @jeremyl14
Date: 2026-06-10

## Question (required)

Which TTC bus delay cause categories and specific codes produce the longest delays, and which are most frequent? How does the cause mix differ between bus and subway?

## Data (required)

- **Primary dataset:** `ttc-bus-delay` ([README](../../README.md))
- **Joins with:** `ttc-subway-delay` ([README](../../../ttc-subway-delay/README.md)) for bus-vs-subway comparison
- **Snapshot dates:** 2025 data from `raw/ttc-bus-delay-data-since-2025.csv` and `raw/ttc-subway-delay-data-since-2025.csv`
- **Filters applied:** 2025 rows only; significant delays only (Min Delay >= 5 minutes) for impact metrics

## Method (required)

- **Tools:** Python 3.12, pandas 2.2, matplotlib 3.9, seaborn 0.13, numpy 2.1
- **Approach:** Map each delay code to a category via its first letter (E=Equipment, M=Operations, P=Infrastructure, S=Safety/Security, T=Transportation, other="Other"). Aggregate significant delays by code and category. Compare bus and subway category shares.
- **Key transformations:**
  1. Filtered both datasets to 2025 rows.
  2. Mapped each `Code` to a category based on first letter.
  3. Joined bus codes to human-readable descriptions from the codes CSV.
  4. Computed per-code statistics: count, mean, median, p95, total delay-minutes.
  5. Computed per-category share of total significant-delay minutes for both bus and subway.
- **Statistical test:** Descriptive analysis; no inferential tests. Total delay-minutes is the primary impact metric.

## How to reproduce (required)

```bash
pip install -r requirements.txt
python analyze.py
```

Expected runtime: ~15 seconds on a laptop
Expected output: 3 figures (PNG) + 2 summary CSVs in `outputs/`

## Results (required)

See `outputs/` for figures and tables.

| Finding | Value |
|---|---|
| Top bus delay code by total minutes | See `outputs/bus-code-summary.csv` |
| Dominant bus category | Operations (M-prefixed codes) |
| Key bus-vs-subway difference | See `outputs/bus-vs-subway-categories.csv` |

## Caveats (required)

- Bus and subway use completely different code sets (46 vs ~200 codes). The first-letter category mapping is a coarse simplification applied to both for comparability.
- **The bus-vs-subway comparison is exploratory and confounded by different reporting conventions.** The subway dataset has 64.5% of rows with Min Delay == 0 (logging artifacts, likely no real delay) vs only 12.7% for bus. This means the category percentages are not measuring the same thing: subway "significant-delay minutes" exclude a much larger fraction of reported events. The comparison shows broad patterns (Operations dominates bus; subway is more evenly spread) but should not be read as a rigorous apples-to-apples benchmark.
- A single incident may generate multiple rows in the raw data, inflating counts.
- 2025 data only for both datasets; seasonal patterns may not generalize.
- No ridership weighting — bus and subway have very different passenger volumes, so total delay-minutes are not directly comparable across modes.
- The "Other" category lumps codes whose first letter is not E/M/P/S/T; it may be heterogeneous.

## Files

- `analyze.py` — main analysis script
- `requirements.txt` — pinned Python deps
- `outputs/` — figures, summary CSVs

---

Author: @jeremyl14, 2026-06-10