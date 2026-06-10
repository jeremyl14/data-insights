# Analysis README template

Copy this file to `datasets/<slug>/analysis/<analysis-name>/README.md` and
fill in every section. Required sections are marked with **(required)**.

---

# <Analysis title>

Dataset: `<dataset-slug>`
Author: <github-user>
Date: YYYY-MM-DD

## Question (required)

What are you trying to answer? One paragraph. State it as a question or a
hypothesis. Avoid vague goals like "explore the data."

> Example: "Is bike-share ridership correlated with daily air quality
> readings in Toronto, controlling for temperature and precipitation?"

## Data (required)

- **Primary dataset:** `<dataset-slug>` (link to its README)
- **Joins with:** <other datasets used, if any>
- **Snapshot dates:** <which raw/ snapshots are used>
- **Filters applied:** <e.g. "excluded 2020-Q2 due to pandemic closures">

## Method (required)

- **Tools:** <Python 3.12, pandas 2.2, DuckDB 1.0, etc.>
- **Approach:** <one paragraph — what did you actually do?>
- **Key transformations:**
  1. Joined bike-share trips to nearest air-quality station by lat/lon.
  2. Aggregated to daily ridership counts and daily mean AQI.
  3. Fit a negative binomial GLM with offset for working-day count.
- **Statistical test:** <e.g. "Pearson r = 0.34, p < 0.001, n = 730 days">

## How to reproduce (required)

```bash
# 1. (one-time) install deps
pip install -r requirements.txt   # if applicable

# 2. run the analysis
python analyze.py

# 3. view outputs
open outputs/figure-1.html
```

Expected runtime: <e.g. "30 seconds on a laptop">
Expected output: <e.g. "3 figures + 1 summary CSV">

## Results (required)

State the findings. Use a small table or a figure reference. Don't bury
the answer.

| Finding | Value |
|---|---|
| Correlation (r) | 0.34 |
| Effect size | +120 trips per 10 µg/m³ AQI increase |
| Confidence | 95% CI [85, 155] |

See `outputs/` for figures and tables.

## Caveats (required)

- Single city; not generalizable to other bike-share systems.
- AQI is measured at fixed stations, not at trip endpoints.
- Weather data joined by day, not by hour.
- The pandemic period (2020-Q2 to 2021-Q3) is excluded.

## Files

- `analyze.py` — main analysis script
- `requirements.txt` — pinned Python deps (use `==X.Y.*` for reproducibility; avoid bare `>=` ranges)
- `outputs/` — figures, tables, summary CSVs
- `notebook.ipynb` — exploratory notebook (output cleared)

## Future work

- Add precipitation as a covariate.
- Hour-of-day breakdown.
- Compare with Hamilton and Ottawa bike-share systems.

---

Author: <github-user>, YYYY-MM-DD
