# Weather quantile regression: asymmetric effects of temperature, rain, and snow

Dataset: `toronto-bike-share`
Author: @jeremyl14
Date: 2026-06-11

## Question

Do weather variables affect bike-share ridership differently at low, median, and high ridership days? Are fair-weather riders more sensitive to bad weather than commuters?

## Data

- **Primary dataset:** `toronto-bike-share` ([README](../../README.md))
- **Joins with:** Weather data from `toronto-weather-daily`, pre-merged in `weather-ridership` analysis
- **Snapshot dates:** 2025-01-01 through 2025-12-31
- **Filters applied:** First 14 days dropped due to lag creation (351 observations)

## Method

- **Tools:** Python 3, pandas, statsmodels (QuantReg), matplotlib, seaborn
- **Approach:** Quantile regression at τ = 0.25, 0.5, 0.75 using the same distributed-lag specification as the OLS `weather-lag-regression` analysis: `ridership ~ total_rain_mm + total_snow_cm + snow_lag_1..14 + temp_mean_c + C(day_of_week) + C(month)`.
- **Why quantile regression:** OLS estimates the conditional mean. But weather may suppress low-ridership days (fair-weather riders) more than high-ridership days (commuters who ride regardless). Quantile regression estimates effects at different points in the conditional distribution, revealing this asymmetry without distributional assumptions.

## How to reproduce

```bash
# 0. generate prerequisite outputs
python ../weather-ridership/analyze.py

pip install -r requirements.txt
python analyze.py
```

Expected runtime: ~15 seconds
Expected output: 3 figures + 2 CSVs in `outputs/`

## Results

| Variable | Q25 (low days) | Q50 (median) | Q75 (high days) |
|----------|---------------|-------------|-----------------|
| Temperature (trips/°C) | +434 | +432 | +369 |
| Rain (trips/mm) | −471 | −284 | −182 |
| Same-day snow (trips/cm) | −477 | −416 | −290 |
| Pseudo R² | 0.768 | 0.794 | 0.780 |

Key finding: **Rain and snow effects are strongly asymmetric across quantiles**, while temperature is relatively stable.

- Rain at Q25 is 2.6× the effect at Q75 (−471 vs −182 trips/mm). Low-ridership days — likely dominated by casual/fair-weather riders — see much larger drops when it rains. High-ridership days (commuters) are more resilient.
- Snow shows the same pattern: −477 at Q25 vs −290 at Q75 (1.6× ratio).
- Temperature is nearly flat across quantiles (~370–430 trips/°C), suggesting temperature shifts the whole distribution rather than selectively affecting one tail.

This supports the intuition that rain and snow selectively drive away fair-weather riders, while commuters (who ride regardless) are less sensitive. Temperature, by contrast, shifts ridership broadly — even commuters ride more when it's warm.

## Caveats

- Same single-year, single-city limitations as the OLS analysis (351 observations).
- Quantile regression standard errors assume independent errors; autocorrelation may inflate precision.
- Snow and temperature are correlated despite month controls.
- Weather data from Pearson airport may not reflect downtown conditions.
- "Low ridership days" at Q25 are not necessarily the same population as "casual riders" — they could also be weekends, holidays, or off-season days. The quantile is conditional on the model covariates, not a direct user-type segmentation.

## Files

- `analyze.py` — main analysis script
- `requirements.txt` — Python dependencies
- `outputs/quantile-weather-effects.png` — temperature/rain/snow coefficients by quantile
- `outputs/quantile-snow-lags.png` — snow lag structure by quantile
- `outputs/quantile-cumulative-snow.png` — cumulative snow effect by quantile
- `outputs/quantile-coefficients.csv` — full coefficient table
- `outputs/summary.csv` — key results summary