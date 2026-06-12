# Subway delay impact on bike-share ridership (Toronto 2025)

Dataset: `toronto-bike-share`
Author: analyst
Date: 2026-06-10

## Question (required)

Do TTC subway disruptions cause measurable increases in bike-share ridership, and is the effect concentrated near subway stations? Specifically, when subway service is significantly disrupted (either by total delay minutes exceeding the 90th percentile or by a single event lasting 30+ minutes), do we see more bike-share trips than expected given the weather and day of week — and is this effect stronger for trips starting near subway stations?

## Data (required)

- **Primary dataset:** `toronto-bike-share` ([README](../../README.md))
- **Joins with:**
  - `ttc-subway-delay` — TTC subway delay data for 2025 ([README](../../../ttc-subway-delay/README.md))
  - `toronto-weather-daily` — ECCC Toronto Pearson daily weather for 2025
  - `toronto-bike-stations` — station reference data for name matching
- **Snapshot dates:** Ridership from `raw/bike-share-toronto-ridership-2025.csv`; TTC delays from `raw/ttc-subway-delay-data-since-2025.csv`; weather from `raw/toronto-pearson-daily-2025.csv`
- **Filters applied:** 2025 only; TTC delays filtered to 2025 dates; bike-share trips filtered to 2025

## Method (required)

- **Tools:** Python 3.12, pandas 2.2, statsmodels 0.14, matplotlib 3.8, seaborn 0.13
- **Approach:** Merged TTC subway delay data with daily bike-share ridership and ECCC weather data. Defined "disruption days" as days where total delay minutes exceed the 90th percentile OR any single delay event is >= 30 minutes. Ran two OLS regressions (all trips and near-subway trips) controlling for temperature, rain, snow, day of week, and month.
- **Key transformations:**
  1. TTC delay data parsed by date; total delay minutes, event count, and max single delay computed per day.
  2. Disruption days flagged using dual threshold: >90th percentile total delay minutes OR max single delay >= 30 min.
  3. Bike-share stations matched to TTC subway stations by name heuristic (9 stations matched, see below).
  4. Near-subway ridership computed as daily trip count from matched stations.
  5. OLS regression: `ridership ~ is_disruption_day + temp_mean_c + total_rain_mm + total_snow_cm + C(day_of_week) + C(month)`.
- **Approach:** Three regression specifications to address the broad treatment group:
  1. **Binary (broad):** `is_disruption_day` = 1 if total delay minutes > 90th percentile OR max single delay ≥ 30 min. Classifies 150/365 days (41%).
  2. **Binary (strict):** `is_strict_disruption` = 1 if total delay minutes > 95th percentile OR max single delay ≥ 60 min. Classifies fewer days with more contrast.
  3. **Continuous:** `total_delay_min` as a continuous predictor — tests whether each additional minute of delay is associated with more ridership.
- **Statistical test:** OLS with HAC (Newey-West) robust standard errors (maxlags=7) to account for autocorrelation in daily time series.

## How to reproduce (required)

```bash
# 1. (one-time) install deps
pip install -r requirements.txt

# 2. run the analysis
python analyze.py

# 3. view outputs
open outputs/delay-ridership-overview.png
open outputs/disruption-effect.png
open outputs/regression-coefficients.png
```

Expected runtime: ~60 seconds on a laptop (loads ~7.8M trip rows for near-subway calculation)
Expected output: 3 figures + 2 summary CSVs (regression results include all three specifications: binary broad, binary strict, continuous)

## Results (required)

| Finding | Value |
|---|---|
| Binary disruption (broad) — all trips | +135 trips, p = 0.72 |
| Binary disruption (broad) — near-subway | +7 trips, p = 0.71 |
| Binary disruption (strict, 95th/60min) — all trips | +811 trips, p = 0.06 |
| Binary disruption (strict, 95th/60min) — near-subway | +38 trips, p = 0.08 |
| Continuous (per delay-min) — all trips | +1.7 trips/min, p = 0.11 |
| Continuous (per delay-min) — near-subway | +0.07 trips/min, p = 0.15 |
| Disruption days (broad) | 150 |
| Disruption days (strict) | 68 |
| All trips R² (binary) | 0.933 |
| Near-subway R² (binary) | 0.925 |
| Temperature effect (all trips) | +445 trips/°C, p < 0.001 |
| Rain effect (all trips) | −253 trips/mm, p < 0.001 |
| Snow effect (all trips) | −357 trips/cm, p < 0.001 |

**Interpretation:** The broad binary disruption definition (41% treatment) yields a small, insignificant coefficient (+135 trips, p = 0.72) — unsurprising given the low contrast between groups. The strict definition (68/365 days, 19% treatment) produces a larger coefficient (+811 trips, p = 0.06), marginally significant at the 10% level. The continuous specification (+1.7 trips per delay-minute, p = 0.11) is also insignificant. Near-subway results follow the same pattern but with smaller coefficients. **The weight of evidence suggests subway disruptions do not cause a statistically reliable increase in bike-share ridership at the daily level.** The marginal significance of the strict binary (p = 0.06) deserves further investigation with multi-year data and hour-of-day resolution, but with HAC-corrected standard errors, even this result does not reach the 5% threshold.

See `outputs/` for figures and tables.

## Caveats (required)

- **Station name matching is approximate.** Only 9 TTC subway stations were matched to bike-share stations using a name-based heuristic, covering a small fraction of the system. The "near-subway" trips represent a subset of stations with obvious name overlaps (e.g., "Bathurst St / Front St W" near Bathurst Station), not a systematic geospatial match.
- **2025 only.** Single-year analysis; patterns may not generalize.
- **Near-subway definition is rough.** The name heuristic is a proxy for proximity. No geospatial distance (500m) was computed because bike-share station lat/lon was available for only 10 stations in the reference file. A proper analysis would use geocoded station locations.
- **Confounding with time-of-day.** Subway disruptions cluster during rush hours, when bike-share ridership is already high. The daily-level regression cannot distinguish "rush hour" from "disruption" effects.
- **No causal identification.** This is an observational regression with controls, not a natural experiment. Subway disruptions correlate with unobserved factors (e.g., large events, construction) that may independently affect ridership.
- **Broad disruption definition dilutes the treatment group.** With 150/365 days (41%) classified as disruption days, the binary OLS has insufficient contrast. The strict definition (68/365, 19%) and continuous specification address this — the strict binary reaches marginal significance (p = 0.06) but still fails the 5% threshold with HAC errors.
- **HAC standard errors.** The regressions now use Newey-West (maxlags=7) standard errors to account for autocorrelation in daily time-series data. This makes p-values more reliable than the original OLS, but may over-correct in small samples.
- **Weather data is from Pearson airport** (~20 km from downtown), which may not reflect conditions at bike-share stations.
- **Non-independence of disruption days.** Consecutive disruption days are not independent observations; the regression treats each day as independent.

## Matched stations

The following TTC subway stations were matched to Bike Share Toronto stations by name heuristic:

| TTC Station | Bike-share Stations |
|---|---|
| BATHURST STATION | Bathurst St / Front St W, Bathurst St / Lennox St, Bathurst St/Queens Quay (Billy Bishop Airport) |
| BAY STATION | Bay St / Charles St W - SMART, Bay St / Dundas St W, Bay St / Harbour St, Bay St / Queens Quay W (Ferry Terminal) |
| BLOOR STATION | Bloor St E / Parliament St, Bloor St W / Huron St, Bloor St W / Kingsmill Rd |
| BROADVIEW STATION | Danforth Ave / Dewhurst Blvd |
| DUNDAS STATION | Dundonald St / Church St |
| EGLINTON STATION | Davisville Ave / Pailton Cres |
| KING STATION | King St W / Charlotte St |
| UNION STATION | Union Station, Front St W / Bay St (North Side), Front St W / University Ave (2), Front St W / Yonge St (Hockey Hall of Fame) |
| YONGE STATION | Yonge St / Dundas Sq |

## Files

- `analyze.py` — main analysis script
- `requirements.txt` — pinned Python deps
- `outputs/delay-ridership-overview.png` — dual-panel ridership + delay figure
- `outputs/disruption-effect.png` — box plot comparing disruption vs normal days
- `outputs/regression-coefficients.png` — coefficient plot with 95% CI
- `outputs/daily-delay-summary.csv` — daily delay statistics and disruption flags
- `outputs/regression-results.csv` — full regression output tables

## Future work

- Use geocoded station locations for proper 500m proximity matching.
- Add hour-of-day analysis to separate rush-hour disruptions from off-peak.
- Implement a stricter disruption definition (e.g., 95th percentile or 60+ min single delay) for a more targeted treatment group.
- Use a difference-in-differences design comparing near-subway vs far-from-subway stations on disruption vs non-disruption days.
- Extend to multiple years for more statistical power.

---

Author: analyst, 2026-06-10