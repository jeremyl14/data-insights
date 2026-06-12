# Snow Clearing Event Study: How Snowfall Suppresses Cycling Volume

Dataset: `toronto-bike-share`
Author: jeremy
Date: 2026-06-11

## Question

How do major snowfall events suppress bike-share ridership, and does the timing of 311 bike-infrastructure complaints predict when ridership recovers? This is an event study that aligns days relative to each storm to measure the ridership deficit and 311 complaint curve in the ±2-week window.

## Data

- **Primary dataset:** `toronto-bike-share` — daily trip counts from trip-level ridership data (2025)
- **Joins with:** `toronto-weather-daily` (ECCC Toronto Pearson, 2025) for snowfall and snow-on-ground; 311 bike-infrastructure daily complaints (2025)
- **Snapshot dates:** 2025 ridership CSV, 2025 weather CSV, 2025 311 daily CSV
- **Filters applied:** only 2025 data; snowfall events defined as days with total_snow_cm >= 2.0; events within 2 days of each other grouped into a single storm

## Method

- **Tools:** Python 3.12, pandas 2.2, matplotlib 3.8, seaborn 0.13
- **Approach:**
  1. Merged daily weather, ridership, and 311 complaint data on date for 2025.
  2. Identified snowfall events (days with >= 2 cm snow), grouping consecutive snowy days within 2 days into a single storm.
  3. For each event, computed a 7-day pre-storm baseline (days -7 to -1) as "expected ridership," then measured the ridership deficit as (actual - expected) / expected * 100 for each day in the window [-3, +14].
  4. Recovery is measured from the **last day of the storm**, not the first — multi-day storms suppress ridership throughout their duration.
  5. Plotted individual event panels (top 5 by snowfall) and an aggregate recovery curve with 95% CI bands.
- **Key transformation:** "T" values in weather data (trace precipitation) replaced with 0. Event grouping uses a 2-day gap threshold.

## How to reproduce

```bash
cd datasets/toronto-bike-share/analysis/snow-clearing-event-study
pip install -r requirements.txt
python analyze.py
```

Expected runtime: ~30 seconds. Outputs: 2 PNG figures + 2 CSVs in `outputs/`.

## Results

| Metric | Value |
|---|---|
| Snowfall events found (2025) | 12 |
| Mean ridership trough | -54.3% below baseline |
| Mean recovery time (events that recover) | ~5.9 days after storm end |
| Mean 311 clearing time | ~1.6 days after storm end |
| Largest event | Feb 6-16: 69.6 cm, trough -97.6%, no recovery within 14 days |

**Key dates and snowfall:**

| Event | Dates | Snow (cm) | Trough | Recovery (days) |
|---|---|---|---|---|
| 1 | Jan 7-11 | 11.6 | -43.7% | 4 |
| 4 | Feb 6-16 | 69.6 | -97.6% | >14 |
| 9 | Nov 9 | 9.8 | -79.6% | >14 |
| 12 | Dec 23-29 | 23.8 | -92.6% | >14 |

- 4 of 12 events never recovered to baseline within the 14-day window — all were major winter storms.
- Weekday storms (n=7 that recovered) have a mean recovery of 5.4 days; the one weekend storm that recovered took 9 days. Sample too small to draw firm conclusions about weekday vs. weekend clearing speed.
- 311 complaints spike within 0-2 days of the storm end but drop to near-zero quickly (~1.6 days on average). This fast drop likely reflects that few people file complaints rather than fast clearing — most cyclists have already stopped riding by the time they would report.
- Larger snowfall events produce deeper troughs and slower recovery. The Feb 6-16 event (69.6 cm over 7 days) suppressed ridership by 97.6% and did not recover within 14 days.

See `outputs/` for figures and tables.

## Caveats

- **311 categories only started in 2025.** No historical comparison is possible. Reporting culture may change over time.
- **Single winter (2025).** Only 12 snowfall events; 4 never recovered within the 14-day window. The sample is too small for robust statistical inference.
- **311 complaints measure reporting, not road conditions.** A drop in complaints does not mean bike lanes are cleared — it may mean cyclists have stopped riding and stopped reporting.
- **Ridership deficit confounds cold with clearing.** Some people don't ride because it's cold or icy, not because bike lanes are uncleared. The deficit overstates the effect of snow on infrastructure.
- **Baseline is the 7 days before the storm.** In deep winter, this baseline is already depressed by cold, so "recovery" means returning to already-low winter levels, not to summer ridership.
- **The 2 cm threshold for snow events is low.** Events 6, 7, and 8 (2.4-3.8 cm) produced surprisingly deep troughs, likely because the pre-storm baseline was already very low in late winter/early spring.

## Files

- `analyze.py` — main analysis script
- `requirements.txt` — pinned Python deps
- `outputs/` — figures and tables
  - `event-study-panel.png` — per-event panels (top 5 by snowfall)
  - `aggregate-recovery-curve.png` — mean deficit and complaints across all events
  - `summary.csv` — one row per event
  - `event-details.csv` — daily data for each event window

## Future work

- Include 2024 weather data for a second winter of events.
- Add temperature as a covariate to disentangle cold-weather suppression from snow-clearing effects.
- Model the relationship between 311 complaint volume and recovery speed explicitly.
- Compare weekday vs. weekend clearing with more data.

---

Author: jeremy, 2026-06-11