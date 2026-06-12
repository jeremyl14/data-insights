# Ridership + 311 Bike Infrastructure Complaints (2025-2026)

## Question

How do daily bike-share ridership, snowfall, and 311 bike infrastructure complaints relate across 2025 and early 2026?

## Data

- **Bike-share ridership**: `raw/bike-share-toronto-ridership-2025.csv` and `raw/bike-share-toronto-ridership-2026.csv` (daily trip counts derived from trip-level timestamps).
- **311 complaints**: `raw/311-bike-infrastructure-daily-2025.csv` and `raw/311-bike-infrastructure-daily-2026.csv` (aggregated from Toronto open data 311 service requests). Five complaint types:
  - Bike Lane Winter Maintenance Required
  - Damaged Bike Lane Barrier
  - Missing/Damaged Flexible Bollards
  - Bollard - Damaged
  - Bike Lane Pothole
- **Weather**: `toronto-weather-daily/raw/toronto-pearson-daily-2025.csv` and `toronto-pearson-daily-2026.csv` for snowfall data.

Both datasets are batch snapshots stored in `raw/` (see `raw/SOURCE.md`).

## Method

1. Load trip-level ridership data for 2025 and 2026, normalize columns, parse timestamps, and count trips per calendar date.
2. Compute a 7-day centered moving average of daily trips.
3. Load 311 daily complaint counts for both years and merge with ridership by date.
4. Plot daily trips as a shaded area with the 7-day MA as a line (left y-axis), 311 total complaints as orange bars (right y-axis, offset), and snowfall on its own y-axis (far right) as light blue bars. Group consecutive days with ≥2 cm snowfall into "snow events", highlight each event span with a blue band, and annotate total cm.
5. Add alternating grey year bands.

## How to reproduce

```bash
cd datasets/toronto-bike-share/analysis/ridership-311-2025-2026
pip install -r requirements.txt
python analyze.py
```

Expected runtime: ~30 seconds. Outputs are written to `outputs/`.

## Results

- **2025**: 7,812,520 trips, 1,123 bike infrastructure 311 complaints.
- **2026 (Jan 1 – Mar 31)**: 552,073 trips, 1,415 complaints (311 data extends through May but bike-share data only through March).
- 311 bike infrastructure complaints in early 2026 already exceed all of 2025 (1,415 vs 1,123).
- Winter maintenance dominates: 350 in all of 2025 vs 1,180 in Jan–May 2026 alone.
- The chart shows snowfall (light blue) aligning with both ridership dips and 311 spikes, confirming weather as the common driver.

The chart shows ridership following its strong seasonal pattern while 311 complaints and snowfall cluster in winter months. Consecutive snowy days are grouped into events (highlighted spans) with total accumulation annotated, making it easy to see both the duration and intensity of each storm.

## Caveats

- **311 complaints measure reporting behavior, not road conditions.** A spike in complaints could reflect increased awareness of the 311 system, a viral social media post, or a councillor directing constituents to report — not necessarily worse infrastructure.
- **The 311 bike infrastructure categories are new (started in 2025).** Year-over-year comparisons are unreliable because reporting culture, category definitions, and city promotion of these channels may change.
- **2026 data is partial**: bike-share through March, 311 through May, weather through May.
- **Triple y-axes can mislead.** The visual relationship between trips, complaints, and snowfall is suggestive, not causal. Winter months naturally have both low ridership and high complaint volume, but one does not cause the other.
- **No causal model.** This is a descriptive visualization; see `snow-clearing-event-study` and `weather-lag-regression` for statistical analysis of weather effects on ridership.

## Files

- `analyze.py` — analysis script
- `requirements.txt` — Python dependencies
- `outputs/ridership-311-2025-2026.png` — main figure with ridership, snowfall, and 311 complaints
- `outputs/summary.csv` — yearly trip and complaint totals
- `outputs/311-daily-comparison.csv` — daily ridership + complaints merged