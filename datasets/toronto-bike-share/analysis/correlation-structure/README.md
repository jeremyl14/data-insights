# Correlation Structure: Ridership, 311 Complaints, Temperature, and Snowfall

Dataset: `toronto-bike-share`
Author: jeremy
Date: 2026-06-12

## Question

What are the lagged and partial correlations between daily bike-share ridership, 311 bike infrastructure complaints, mean temperature, and snowfall — after removing shared seasonality?

## Data

- **Bike-share ridership**: `raw/bike-share-toronto-ridership-2025.csv` and `raw/2026-10-30/bike-share-toronto-ridership-2026.csv` (daily trip counts; the 2026 re-snapshot runs Jan–Sep).
- **311 complaints**: `raw/311-bike-infrastructure-daily-2025.csv` and `raw/311-bike-infrastructure-daily-2026.csv`.
- **Weather**: `toronto-weather-daily/raw/toronto-pearson-daily-2025.csv` and `toronto-pearson-daily-2026.csv`.
- **Snapshot dates**: 2025 full year + 2026 Jan–Sep (ridership), Jan 1 – May 30 (311), Jan 1 – Jun 10 (weather).
- **Filters applied**: Ridership is cut at the last date all three sources cover (2026-05-30), so days without 311 or weather data aren't filled in as zero complaints / zero snow / a forward-filled temperature. Within that range, days with missing temperature are forward-filled and days with missing ridership dropped. 515 days with complete data.

## Method

- **Tools:** Python 3.12, pandas 2.2, numpy 2.0, scipy 1.14, matplotlib 3.9, seaborn 0.13.
- **Detrending:** All series deseasonalized by subtracting day-of-year means, then demeaned. This removes the dominant annual cycle shared by all variables.
- **Cross-correlation function (CCF):** Computed for all 6 variable pairs at lags 0–30 days, on deseasonalized residuals. 95% confidence bands shown (±1.96/√n).
- **Partial correlation:** Pearson r between variable pairs after regressing out controls. Four tests:
  1. Trips vs complaints, controlling for temperature
  2. Trips vs snowfall, controlling for temperature
  3. Complaints vs snowfall, controlling for temperature
  4. Trips vs complaints, controlling for temperature + snowfall
- **Rolling correlation:** 30-day window Pearson r for trips-vs-temperature and trips-vs-complaints, on deseasonalized data.

## How to reproduce

```bash
cd datasets/toronto-bike-share/analysis/correlation-structure
pip install -r requirements.txt
python analyze.py
```

Expected runtime: ~60 seconds. Outputs are written to `outputs/`.

## Results

### Raw correlations (deseasonalized)

| Pair | r | p-value |
|---|---|---|
| Trips vs Temperature | 0.486 | < 0.001*** |
| Trips vs 311 Complaints | −0.167 | < 0.001*** |
| Trips vs Snowfall | −0.137 | 0.002** |
| 311 Complaints vs Temperature | −0.196 | < 0.001*** |
| 311 Complaints vs Snowfall | −0.049 | 0.264 (NS) |
| Temperature vs Snowfall | −0.064 | 0.148 (NS) |

### Partial correlations

| X | Y | Controlling for | Partial r | p-value |
|---|---|---|---|---|
| Daily trips | 311 complaints | Temperature | −0.083 | 0.059 (NS) |
| Daily trips | Snowfall | Temperature | −0.122 | 0.006** |
| 311 complaints | Snowfall | Temperature | −0.063 | 0.153 (NS) |
| Daily trips | 311 complaints | Temp + Snowfall | −0.092 | 0.037* |

### CCF highlights

- **Trips → Temperature:** Strong positive CCF at lag 0 (r ≈ 0.49), falling to r ≈ 0.10 by lag 5 and not significant from lag 6.
- **Trips → Snowfall:** Negative at lag 0 only (r ≈ −0.14, p = 0.002); lags 1–6 are not significant.
- **Trips → Complaints:** Negative at lag 0 (r ≈ −0.17) and growing slightly over lags 1–4 (r ≈ −0.27 at lag 4): low-ridership days are followed by more complaints over the next few days.

### Key findings

1. **Temperature is the dominant covariate.** After deseasonalizing, trips–temperature r = 0.49 is the strongest pairwise correlation.
2. **Once temperature is controlled for, the trips–complaints link is weak.** Partial r = −0.08 (p = 0.06) controlling for temperature, −0.09 (p = 0.04) controlling for temperature and snowfall. The raw negative correlation (r = −0.17) is mostly shared with temperature.
3. **311 complaints and snowfall are not significantly correlated** after controlling for temperature (partial r = −0.06, p = 0.15). Their raw correlation is negligible (r = −0.05).
4. **Snowfall's effect on ridership is same-day only** in this sample (significant at lag 0, not at lags 1–6).
5. **These results are sensitive to the sample window** — see Caveats. With 2026 ridership through March only (455 days), the same method gave trips–temperature r = 0.63, trips–complaints partial r = −0.21 (p < 0.001) and significant snowfall lags of 1–4 days.

## Caveats

- **Deseasonalizing by day-of-year means** removes the annual cycle but not shorter-period effects (e.g., weekly patterns, holidays). Day-of-week effects are not controlled for.
- **CCF does not imply causation.** A significant cross-correlation at lag k means variable X at time t predicts variable Y at time t+k — it does not mean X causes Y.
- **311 complaints measure reporting, not conditions.** The negative partial correlation with ridership could reflect endogeneity (more complaints on days people try to ride and find problems) rather than a causal effect of complaints on ridership.
- **2026 data is partial**, and the sample stops at 2026-05-30, the last day all three sources cover (ridership runs to September, 311 to May 30, weather to June 10). The 515-day sample is dominated by 2025.
- **Day-of-year deseasonalizing needs more years than this sample has.** With ~1.4 years, each calendar day has one or two observations, so the "seasonal" mean for a day is largely that day's own value. Adding April–May 2026 (60 days) changed most correlations substantially (e.g. trips–complaints partial r from −0.21 to −0.08). Treat the coefficients as provisional until several full years are available.
- **Snowfall is sparse** — most days have 0 cm, which compresses the correlation distribution. The CCF for snow pairs is driven by relatively few snowy days.
- **No day-of-week controls** in the partial correlations. Weekend ridership patterns may confound some relationships.

## Files

- `analyze.py` — analysis script
- `requirements.txt` — Python dependencies
- `outputs/ccf-panel.png` — CCF for all 6 variable pairs (lags 0–30)
- `outputs/ccf-results.csv` — full CCF values with p-values
- `outputs/correlation-heatmap.png` — raw correlation matrix + partial correlation bar chart
- `outputs/raw-correlation-matrix.csv` — deseasonalized Pearson correlation matrix
- `outputs/raw-correlation-pvalues.csv` — p-values for correlation matrix
- `outputs/partial-correlations.csv` — partial correlation results
- `outputs/rolling-correlation-trips-temp.png` — 30-day rolling r for trips vs temperature
- `outputs/rolling-correlation-trips-complaints.png` — 30-day rolling r for trips vs complaints