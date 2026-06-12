# E-bike share of total trips

Dataset: `toronto-bike-share`
Author: analyst
Date: 2026-06-10

## Question

How has e-bike adoption grown since their introduction? What share of trips are
e-bikes, and is it increasing? Do casual riders and annual members differ in
their e-bike usage?

## Data

- **Primary dataset:** `toronto-bike-share` ([README](../../README.md))
- **Joins with:** none
- **Snapshot dates:** `raw/bike-share-toronto-ridership-2024.csv`, `raw/bike-share-toronto-ridership-2025.csv`
- **Filters applied:** Only 2024 and 2025 data used (Bike_Model column does not exist in earlier years)

## Method

- **Tools:** Python 3.12, pandas 2.2, matplotlib 3.8, seaborn 0.13
- **Approach:** Count trips by Bike_Model per month for 2024 and 2025. EFIT and EFIT G5 are both classified as e-bikes. ICONIC is the standard bike. E-bike share = (EFIT + EFIT G5) trips / total trips. Also break down e-bike share by user type (member vs casual). Monthly and yearly aggregates computed.
- **Key transformations:**
  1. Loaded 2024 and 2025 ridership CSVs, selecting Start_Time, Bike_Model, and User_Type columns.
  2. Stripped whitespace from column names, Bike_Model, and User_Type values.
  3. Normalized User_Type labels: `Member`/`Annual Member` → `member`, `Casual`/`Casual Member` → `casual`.
  4. Aggregated trip counts by year, month, and bike model.
  5. Computed e-bike share per month and per year, overall and by user type.
  6. Flagged partial years (year where max month < 12).
- **Statistical test:** Descriptive analysis only — no inferential tests.

## How to reproduce

```bash
# 1. (one-time) install deps
pip install -r requirements.txt

# 2. make sure raw data is available
# from repo root: dvc pull

# 3. run the analysis
python analyze.py

# 4. view outputs
open outputs/bike-model-share.png
```

Expected runtime: ~30 seconds on a laptop
Expected output: 2 figures + 1 summary CSV

## Results

| Finding | Value |
|---|---|
| 2024 overall e-bike share | 15.4% |
| 2025 overall e-bike share | 19.4% (full year) |
| Peak monthly e-bike share | 24.8% (2025-05) |
| Monthly trend | E-bike share is seasonal — peaks in warmer months (Apr–Nov), drops sharply in winter |

E-bike share grew from 15.4% in 2024 to 19.4% in 2025 (full year). The share is
not monotonically increasing month-over-month — it follows a strong seasonal
pattern, peaking in late spring / early summer and falling sharply in winter
months (Jan, Feb, Dec). Within the warm season, 2025 consistently exceeds 2024
at the same month, indicating real adoption growth beyond seasonality.

**E-bike share by rider type:** Casual riders use e-bikes at a higher rate than
annual members. In 2024, casual e-bike share was 20.9% vs 13.8% for members
(~1.5× ratio). In 2025, casual e-bike share was 23.9% vs 17.7% for members
(~1.35× ratio). This gap explains much of the seasonality in overall e-bike
share, since casual ridership peaks in summer months.

See `outputs/` for figures and tables.

## Caveats

- The Bike_Model column only exists in 2024 and 2025 data — no earlier years are available, so we cannot measure e-bike share before 2024.
- 2025 data coverage: if partial, the yearly e-bike share may not be representative of the full year (seasonal ridership patterns differ).
- EFIT and EFIT G5 are both e-bikes but different hardware generations; this analysis groups them together.
- Station naming or availability changes may affect trip counts but should not bias model share.
- This is a descriptive analysis; no causal claims about why e-bike share changes are made.
- **2023 user_type data is unreliable.** The source data labels ~94% of 2023 trips as "Casual Member" — a clear labeling bug that inverts the actual ratio. This analysis only covers 2024–2026 (where bike_model data exists), so 2023 is not included, but any future extension should treat 2023 user_type labels with caution.

## Files

- `analyze.py` — main analysis script
- `requirements.txt` — pinned Python deps
- `outputs/` — figures and summary CSVs

---

Author: analyst, 2026-06-10