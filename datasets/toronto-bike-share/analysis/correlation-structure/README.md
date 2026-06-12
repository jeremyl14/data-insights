# Correlation Structure: Ridership, 311 Complaints, Temperature, and Snowfall

Dataset: `toronto-bike-share`
Author: jeremy
Date: 2026-06-12

## Question

What are the lagged and partial correlations between daily bike-share ridership, 311 bike infrastructure complaints, mean temperature, and snowfall — after removing shared seasonality?

## Data

- **Bike-share ridership**: `raw/bike-share-toronto-ridership-2025.csv` and `raw/bike-share-toronto-ridership-2026.csv` (daily trip counts).
- **311 complaints**: `raw/311-bike-infrastructure-daily-2025.csv` and `raw/311-bike-infrastructure-daily-2026.csv`.
- **Weather**: `toronto-weather-daily/raw/toronto-pearson-daily-2025.csv` and `toronto-pearson-daily-2026.csv`.
- **Snapshot dates**: 2025 full year + 2026 Jan–Mar (ridership), Jan–May (311, weather).
- **Filters applied**: Days with missing temperature forward-filled; days with missing ridership dropped. 455 days with complete data.

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
| Trips vs Temperature | 0.628 | < 0.001*** |
| Trips vs 311 Complaints | −0.309 | < 0.001*** |
| Trips vs Snowfall | −0.248 | < 0.001*** |
| 311 Complaints vs Temperature | −0.238 | < 0.001*** |
| 311 Complaints vs Snowfall | −0.048 | 0.310 (NS) |
| Temperature vs Snowfall | −0.073 | 0.120 (NS) |

### Partial correlations

| X | Y | Controlling for | Partial r | p-value |
|---|---|---|---|---|
| Daily trips | 311 complaints | Temperature | −0.211 | 0.000005*** |
| Daily trips | Snowfall | Temperature | −0.260 | <0.000001*** |
| 311 complaints | Snowfall | Temperature | −0.068 | 0.148 (NS) |
| Daily trips | 311 complaints | Temp + Snowfall | −0.238 | <0.000001*** |

### CCF highlights

- **Trips → Temperature:** Strong positive CCF at lag 0 (r ≈ 0.63), decaying to ~0 within 5 days. Temperature leads ridership by 0–2 days.
- **Trips → Snowfall:** Negative at lag 0 (r ≈ −0.25), significant negative lags persisting 1–4 days. Snowfall's effect on ridership is immediate and short-lived.
- **Trips → Complaints:** Negative at lag 0 (r ≈ −0.31). More complaints on low-ridership days — consistent with complaints being endogenous (people complain when they try to ride and find problems).

### Key findings

1. **Temperature is the dominant covariate.** After deseasonalizing, trips–temperature r = 0.63 is the strongest pairwise correlation. Controlling for it reduces but does not eliminate the trips–complaints link (partial r = −0.21, p < 0.001).
2. **311 complaints and snowfall are not significantly correlated** after controlling for temperature (partial r = −0.07, p = 0.15). Their raw correlation is negligible (r = −0.05).
3. **The trips–complaints negative correlation persists** after controlling for both temperature and snowfall (partial r = −0.24, p < 0.001). This is consistent with complaints being an endogenous variable: people report problems on days they attempt to ride and encounter obstacles.
4. **Snowfall's effect on ridership is immediate and short-lived** (1–4 day lag in CCF), consistent with the event-study findings in `snow-clearing-event-study`.

## Caveats

- **Deseasonalizing by day-of-year means** removes the annual cycle but not shorter-period effects (e.g., weekly patterns, holidays). Day-of-week effects are not controlled for.
- **CCF does not imply causation.** A significant cross-correlation at lag k means variable X at time t predicts variable Y at time t+k — it does not mean X causes Y.
- **311 complaints measure reporting, not conditions.** The negative partial correlation with ridership could reflect endogeneity (more complaints on days people try to ride and find problems) rather than a causal effect of complaints on ridership.
- **2026 data is partial** (ridership through March, 311 through May). The 455-day sample is dominated by 2025.
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