# TTC Subway 2025: Station Delay Ranking & Cause Breakdown

Dataset: `ttc-subway-delay`
Author: jeremyl14
Date: 2026-06-10

## Question (required)

Which TTC subway stations accumulate the most delay minutes, and what drives delays at the worst ones? This analysis ranks stations by total delay minutes (all delays > 0 min) and breaks down the causes (Equipment, Operations, Infrastructure, Safety, Transportation) at the top offenders. A separate "significant delays" count (≥5 min) is provided for reference.

## Data (required)

- **Primary dataset:** `ttc-subway-delay` ([README](../../README.md))
- **Joins with:** TTC delay-code lookup (`ttc-subway-delay-codes.xlsx`) for human-readable code descriptions
- **Snapshot dates:** 2025-01-01 through 2025-12-31 (from `ttc-subway-delay-data-since-2025.csv`)
- **Filters applied:**
  - Year 2025 only
  - Lines YU, BD, SHP only (excludes ambiguous values like YU/BD, SRT, bus-route codes)
  - `Min Delay > 0` (zero-minute records are logging artifacts)
  - "Significant delay" = `Min Delay >= 5` minutes

## Method (required)

- **Tools:** Python 3, pandas, matplotlib, seaborn, openpyxl
- **Approach:**
  1. Loaded 2025 delay CSV and filtered to YU/BD/SHP lines with `Min Delay > 0`.
  2. Normalized station names: stripped whitespace, uppercased, removed parenthetical suffixes (e.g., "(PLATFOR", "(APPROAC"), removed " - SMART" suffixes, and merged obvious variants (e.g., "ST GEORGE BD STATION" / "ST GEORGE YUS STATION" → "ST GEORGE STATION"; "VMC STATION" → "VAUGHAN MC STATION").
  3. Classified each delay code by its first letter: E=Equipment, M=Operations, P=Infrastructure, S=Safety, T=Transportation. Joined to the XLSX code lookup for descriptions.
  4. Aggregated total delay minutes per station, then ranked stations. Computed category-level breakdowns.
  5. Produced two figures and two summary CSVs.
- **Key transformations:**
  1. Station name normalization via regex stripping of parenthetical content and manual mapping of known variants.
  2. Code-category mapping from first letter of `Code` field.
  3. Aggregated `Min Delay` sum per station, per line, per category.
- **Statistical test:** Descriptive ranking only; no inferential tests.

## How to reproduce (required)

```bash
# 1. (one-time) install deps
pip install -r requirements.txt

# 2. run the analysis
python analyze.py

# 3. view outputs
open outputs/top-stations-by-delay.png
open outputs/station-cause-breakdown.png
```

Expected runtime: ~10 seconds on a laptop
Expected output: 2 figures + 2 summary CSVs

## Results (required)

| Finding | Value |
|---|---|
| Top station by total delay min | EGLINTON STATION (YU) — 2,822 min |
| 2nd | SHEPPARD WEST STATION (YU) — 2,221 min |
| 3rd | WILSON STATION (YU) — 2,192 min |
| 4th | KIPLING STATION (BD) — 2,134 min |
| 5th | KENNEDY STATION (BD) — 2,067 min |
| Total significant-delay events | 4,923 |
| Total significant-delay minutes | 56,463 |
| Unique stations after normalization | 224 |

Equipment delays dominate at most top stations, followed by Operations and Infrastructure.

## Caveats (required)

- **Attribution vs. causation:** A delay logged at a station does not mean the station *caused* it. The incident may have originated elsewhere and been recorded at the nearest station.
- **Duplicate incidents:** The same incident may generate multiple rows if it affects adjacent stations.
- **Zero-minute records excluded:** `Min Delay == 0` records are logging artifacts and were excluded.
- **Station name normalization is approximate:** Despite manual mapping of known variants, some stations may still be split across multiple normalized names (e.g., typos, unusual abbreviations).
- **2025 only:** Results may not generalize to other years; 2025 data may reflect construction or seasonal effects.
- **Line filtering:** Ambiguous line values (e.g., YU/BD) were excluded; these represent ~400 records that could shift rankings if reassigned.
- **No passenger-weighting:** This analysis weights by delay minutes, not by passenger volume. A 10-minute delay at BLOOR-YONGE affects far more riders than one at BESSARION.
- **Code categories are coarse:** The first-letter mapping lumps diverse causes together; the XLSX lookup provides finer-grained descriptions.

## Files

- `analyze.py` — main analysis script
- `requirements.txt` — pinned Python deps
- `outputs/top-stations-by-delay.png` — horizontal bar chart of top 20 stations
- `outputs/station-cause-breakdown.png` — stacked bar chart of top 10 stations by cause
- `outputs/station-delay-summary.csv` — per-station summary with category percentages
- `outputs/station-cause-breakdown.csv` — per-station per-category breakdown

## Future work

- Passenger-volume weighting using TTC ridership data.
- Time-of-day and day-of-week breakdown to see if peak-hour delays differ.
- Year-over-year comparison once 2026 data accumulates.
- Finer-grained code analysis within each category.

---

Author: jeremyl14, 2026-06-10