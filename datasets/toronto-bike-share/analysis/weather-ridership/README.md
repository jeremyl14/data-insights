# Weather and ridership overlay for Bike Share Toronto 2025

Dataset: `toronto-bike-share`
Author: analyst
Date: 2026-06-10

## Question (required)

How does daily precipitation (rain, snow, and mixed events) overlay with bike-share ridership patterns in Toronto through 2025? Which significant precipitation events coincide with the sharpest ridership dips, and how do rain vs. snow events differ in their apparent effect?

## Data (required)

- **Primary dataset:** `toronto-bike-share` ([README](../../README.md))
- **Secondary dataset:** `toronto-weather-daily` ([README](../../../toronto-weather-daily/README.md)) — ECCC daily weather for Toronto Pearson (station 51459), 2025
- **Snapshot dates:** Ridership data from `raw/bike-share-toronto-ridership-2025.csv`; weather data from `toronto-weather-daily/raw/toronto-pearson-daily-2025.csv`
- **Filters applied:** Only 2025 data; days with missing ridership (if any) are filled as 0

## Method (required)

- **Tools:** Python 3.12, pandas 2.2, matplotlib 3.8, seaborn 0.13
- **Approach:** Merged ECCC daily weather (Toronto Pearson) with bike-share daily trip counts. Weather data sourced from the `toronto-weather-daily` catalog dataset. Defined "significant precipitation events" as days where total snow >= 5 cm OR total rain >= 10 mm OR total precipitation >= 15 mm. Grouped consecutive significant days into events, classified each event as rain, snow, or mixed. Produced a dual-panel figure (top: ridership with 7-day MA and event shading; bottom: stacked precipitation bars). Saved a merged daily CSV and a precip-events summary CSV.
- **Key transformations:**
  1. ECCC CSV columns stripped of whitespace; trace amounts ("T") converted to 0.0; missing numeric values filled with 0.0.
  2. Weather data loaded from the `toronto-weather-daily` dataset (local CSV, not a live API call).
  3. Ridership loaded from seasonal-ridership `daily-rides.csv` (2025 rows); fallback to raw trip file with per-date grouping.
  4. 7-day centered moving average computed on daily ridership.
  5. Consecutive significant-precip days grouped into events; each event classified by dominant precipitation type.
- **Statistical test:** Descriptive overlay only — no formal hypothesis test. The figure shows co-occurrence, not causation.

## How to reproduce (required)

```bash
# 0. (if using fallback path) pull bike-share raw data and ensure seasonal-ridership outputs exist
dvc pull datasets/toronto-bike-share/raw/bike-share-toronto-ridership-2025.csv.dvc
python ../seasonal-ridership/analyze.py  # optional: creates daily-rides.csv

# 1. (one-time) install deps
pip install -r requirements.txt

# 2. run the analysis
python analyze.py

# 3. view outputs
open outputs/weather-ridership-2025.png
```

Expected runtime: ~10 seconds on a laptop (local CSVs, no network calls)
Expected output: 1 figure + 2 summary CSVs

## Results (required)

See `outputs/` for the figure and CSVs.

| Finding | Value |
|---|---|
| Significant precipitation events in 2025 | 26 |
| Largest snow event | Feb 12–13 (26.4 cm over 2 days) |
| Peak ridership day | ~48,800 trips (summer, warm dry day) |
| Trough ridership | ~2,000–4,000 trips (cold snow days in Jan–Feb) |
| Seasonal range | ~10× variation between winter lows and summer peaks |
| Snow events | Consistently produce sharp ridership dips visible in 7-day MA |
| Heavy rain events | Moderate dips, recovery within 1–2 days |
| Mixed events | Largest dips when cold + wet coincide |

Snow events (Jan–Mar, Dec) produce the most visible ridership dips, with the 7-day MA dropping 30–50% from seasonal baseline. Rain events in summer cause smaller relative dips (10–20%) because the baseline is much higher.

## Caveats (required)

- Weather data is from Toronto Pearson airport, ~20 km from downtown. Urban heat island and lake-effect differences mean actual downtown conditions may differ from Pearson readings.
- Snow on Ground is measured at 0600 UTC; precipitation values are daily totals. This creates an asymmetry in the snow measurement.
- This analysis shows correlation, not causation. Precipitation is a plausible driver of ridership dips, but other factors (holidays, system outages, special events) may co-occur with weather events.
- The bottom precipitation panel uses mm water equivalent: snow cm is multiplied by 10 (1 cm snow ≈ 10 mm water equivalent) so rain and snow are visually comparable on the same axis.
- 2025 only — patterns may not generalize across years or to other bike-share systems.
- Trace precipitation ("T" in ECCC data) is treated as 0.0 mm/cm, which may undercount very light precipitation days.
- Days with missing ridership data are filled as 0; for 2025 no days were actually missing (all 365 days had trip records).

## Files

- `analyze.py` — main analysis script
- `requirements.txt` — pinned Python deps
- `outputs/weather-ridership-2025.png` — dual-panel figure
- `outputs/weather-ridership-2025.csv` — daily merged data
- `outputs/precip-events-2025.csv` — precipitation event summaries

## Future work

- Add temperature as a covariate (overlay mean temp on ridership).
- Quantify the ridership dip per event type with confidence intervals.
- Compare 2025 patterns to prior years (2019–2024) to separate seasonal baseline from weather effects.
- Use hourly weather data for finer-grained analysis of time-of-day effects.

---

Author: analyst, 2026-06-10