# TTC Subway Delay Cause Taxonomy

Dataset: `ttc-subway-delay`
Author: jeremyl14
Date: 2026-06-10

## Question (required)

Which TTC subway delay cause categories and specific codes produce the longest delays, and which are most frequent? Which delay categories are most amenable to capital vs. operational intervention?

## Data (required)

- **Primary dataset:** `ttc-subway-delay` (see [README](../../README.md))
- **Joins with:** None
- **Snapshot dates:** 2025-01-01 through 2025-12-31 (from `raw/ttc-subway-delay-data-since-2025.csv`)
- **Filters applied:** Year 2025 only; rows with `Line` not matching YU/BD/SHP/SRT normalized variants excluded (~3% of rows). "Significant delay" = Min Delay >= 5 minutes.

## Method (required)

- **Tools:** Python 3.12, pandas 2.2, matplotlib 3.9, seaborn 0.13, openpyxl 3.1
- **Approach:**
  1. Loaded 2025 delay CSV and XLSX code lookup (two column groups: YU codes and SRT/BD codes).
  2. Merged both lookup sheets into a single code-to-description table, marking each code as YU-only, BD-only, or both-lines.
  3. Assigned each code to a category by first letter: E=Equipment, M=Operations, P=Infrastructure, S=Safety/Security, T=Transportation, other="Other".
  4. Computed per-code summary statistics (count, mean, median, p95, total delay-minutes) for all delays and for significant delays (>=5 min).
  5. Computed monthly category share of significant-delay minutes per line (YU, BD, SHP).
  6. Generated three visualizations: bubble chart (frequency vs severity vs impact), horizontal bar chart (top 15 by total minutes), and small-multiples stacked percentage bars (category mix by month and line).

- **Key transformations:**
  1. Normalized line codes (YUS → YU, SRT → SHP, etc.); dropped ambiguous/other lines.
  2. Stripped whitespace from delay codes before joining to lookup.
  3. 9 codes present in the data had no match in either lookup sheet; these are included with blank descriptions.

## How to reproduce (required)

```bash
# 1. (one-time) install deps
pip install -r requirements.txt

# 2. run the analysis
python analyze.py

# 3. view outputs
open outputs/cause-bubble-chart.png
open outputs/top-codes-by-minutes.png
open outputs/category-monthly-share.png
```

Expected runtime: ~10 seconds on a laptop
Expected output: 3 figures + 2 summary CSVs

## Results (required)

| Finding | Value |
|---|---|
| Top delay code by total minutes | SUDP (Disorderly Patron) — 7,646 min |
| 2nd highest | MUIR (Injured Customer, Medical Aid Refused) — 4,797 min |
| 3rd highest | SUUT (Unauthorized at Track Level) — 3,917 min |
| Largest category by delay-minutes | Operations (32.9% of significant-delay minutes) |
| 2nd largest category | Safety/Security (28.7%) |
| 3rd largest category | Infrastructure (24.0%) |
| Equipment share | 7.3% |
| Transportation share | 7.1% |
| Unmatched codes | 9 codes (PUEO, MUPF, PUEWZ, PUEME, TUUR, MUCP, MUNCA, TUNCA, XXXXX) |

See `outputs/` for figures and tables.

## Caveats (required)

- The TTC-internal code taxonomy may not reflect current operational categories; codes were assigned to categories by first letter only.
- Some codes represent false alarms that still cause significant delays — notably MUPAA (Passenger Assistance Alarm - No Trouble Found) and SUDP (Disorderly Patron).
- A single incident may generate multiple codes across rows, so total delay-minutes can overstate the real-world time lost.
- 9 codes in the data (~0.1% of rows) don't appear in either lookup sheet and have blank descriptions.
- Analysis is limited to 2025 data only; seasonal and post-pandemic effects may not generalize.
- The YU/BD/SHP line normalization discards ~3% of rows with ambiguous or bus route line codes.
- Infrastructure and Equipment categories are more amenable to capital investment; Operations and Safety/Security improvements tend to be operational.

## Files

- `analyze.py` — main analysis script
- `requirements.txt` — pinned Python deps
- `outputs/` — figures, tables, summary CSVs

## Future work

- Compare 2025 patterns to pre-pandemic years (requires historical XLSX data).
- Time-of-day analysis to identify shift-specific patterns in Operations delays.
- Cost-benefit model weighting code frequency, severity, and estimated remediation cost.

---

Author: jeremyl14, 2026-06-10