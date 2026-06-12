# Weather lag regression: snow, rain, and temperature effects on Toronto bike-share ridership

Dataset: `toronto-bike-share`
Author: jeremy
Date: 2026-06-10

## Question (required)

How does each weather variable — rain, snow (same-day and lagged), and temperature — affect daily bike-share ridership in Toronto? How long does snow's effect persist after a snowfall event? Do 311 bike infrastructure complaints predict additional ridership loss beyond weather?

## Data (required)

- **Primary dataset:** `toronto-bike-share` ([README](../../README.md))
- **Joins with:** Weather data from the `toronto-weather-daily` dataset ([README](../../../toronto-weather-daily/README.md)), already merged in `weather-ridership` analysis; 311 bike infrastructure complaints from `raw/311-bike-infrastructure-daily-2025.csv`
- **Snapshot dates:** 2025-01-01 through 2025-12-31 (365 days)
- **Filters applied:** First 14 days dropped due to lag creation (351 observations remaining)

## Method (required)

- **Tools:** Python 3.12, pandas 2.2, statsmodels 0.14, matplotlib 3.8, seaborn 0.13
- **Approach:** Distributed lag OLS regression. The model estimates the effect of same-day weather and lagged snowfall (1–14 days) on daily ridership, controlling for day-of-week and month fixed effects.
- **Key transformations:**
  1. Loaded merged weather+ridership data from `weather-ridership` analysis output.
  2. Merged in `snow_on_grnd_cm` from the `toronto-weather-daily` dataset.
  3. Created 14 lag features for `total_snow_cm` (lag_1 through lag_14).
  4. Created day-of-week and month dummy variables (dropping first category each).
  5. Fit OLS: `ridership ~ total_rain_mm + total_snow_cm + snow_lag_1..14 + temp_mean_c + complaints_311 + complaints_lag_1..7 + C(day_of_week) + C(month)`.
- **Statistical test:** OLS with 351 observations, 42 predictors. R² = 0.937.

## How to reproduce (required)

```bash
# 0. generate prerequisite outputs (weather-ridership must run first)
python ../weather-ridership/analyze.py

# 1. (one-time) install deps
pip install -r requirements.txt

# 2. run the analysis
python analyze.py

# 3. view outputs
open outputs/lag-coefficients.png
```

Expected runtime: ~10 seconds on a laptop
Expected output: 5 figures + 3 summary CSVs

## Results (required)

| Finding | Value |
|---|---|
| Same-day snow effect | −469 trips per cm (p < 0.001, 95% CI [−689, −249]) |
| Lag-1 snow effect | −244 trips per cm (p = 0.029, 95% CI [−462, −26]) |
| Lag-6 snow effect | −239 trips per cm (p = 0.047, 95% CI [−475, −3]) |
| Lag-7 snow effect | −258 trips per cm (p = 0.032, 95% CI [−494, −22]) |
| Rain effect | −257 trips per mm (p < 0.001, 95% CI [−326, −189]) |
| Temperature effect | +464 trips per °C (p < 0.001, 95% CI [365, 562]) |
| Cumulative snow effect (lag 0–14) | −1,744 trips per cm (95% CI via covariance matrix; see weather-coefficients.png for CI) |
| 311 complaints (same-day) | +73 trips per complaint (p = 0.29, not significant) |
| 311 complaints (all lags) | No significant lagged effects (all p > 0.25) |
| Model R² | 0.937 |
| Significant snow lags (p < 0.05) | lag_0, lag_1, lag_6, lag_7 |

Snow significantly reduces ridership on the day of snowfall and reappears as significant at lags 6 and 7 days later, possibly reflecting weekly cyclical patterns or snow-on-ground persistence. The cumulative effect of a 1 cm snowfall sums to approximately −1,744 trips over 15 days, but this point estimate has substantial uncertainty — only 4 of 15 lags are individually significant and the confidence interval (computed from the full covariance matrix and shown in `outputs/weather-coefficients.png`) is wide. The cumulative figure should be interpreted with caution. Rain has a strong same-day effect (−257 trips/mm). Temperature is the strongest positive driver (+464 trips/°C).

**311 complaints do not predict ridership after controlling for weather.** The same-day coefficient is positive (+73 trips/complaint, p=0.29) — if anything, days with more complaints have slightly *higher* ridership, but this is not significant. This likely reflects that complaints happen on days when people are *trying* to ride but encounter problems; on truly bad days, nobody rides and nobody complains either. The 311 variable is endogenous — it measures reporting behavior, not road conditions.

See `outputs/` for figures and tables.

## Caveats (required)

- OLS assumes independent errors; the Durbin-Watson statistic (1.5) suggests mild positive autocorrelation in residuals, which may inflate t-statistics.
- Single year of data limits sample size (351 days after lag trimming); results may not generalize across years.
- Snow and temperature are correlated despite month controls — cold days with snow are also low-ridership days, making causal attribution difficult.
- Weather data is from Pearson airport (~20 km from downtown Toronto), which may not reflect conditions at actual bike-share stations.
- Lagged snow coefficients may partially proxy for snow-on-ground persistence rather than a true lagged behavioral response; a model with explicit snow-on-ground data would be more appropriate.
- The model does not account for holidays or special events, which could confound day-of-week effects.
- 311 complaints are endogenous: they measure public reporting behavior, not road conditions. Days with zero complaints may have good clearing, or may have so few riders that nobody encounters the problem. The positive (insignificant) same-day coefficient is consistent with this — complaints happen when people ride but find problems.
- 311 "Bike Lane Winter Maintenance Required" does not distinguish between cycle tracks, painted lanes, or other facility types.

## Files

- `analyze.py` — main analysis script
- `requirements.txt` — pinned Python deps
- `outputs/` — figures and summary CSVs

---

Author: jeremy, 2026-06-10