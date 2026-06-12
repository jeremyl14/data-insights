# Ridership dip detection

Dataset: `toronto-bike-share`
Author: @jeremyl14
Date: 2026-06-10

## Question

Which periods show sustained drops in Bike Share Toronto ridership —
a sharp decline followed by days of depressed usage and then recovery —
suggesting infrastructure disruptions like snow, ice, or system outages?

## Data

- **Primary dataset:** `toronto-bike-share`
- **Years used:** 2017–2026 (2016 starts mid-year, so excluded)
- **Filters applied:** Rows with timestamps outside 2014–2030 are dropped
  (removes a misparsed year-2000 row in the 2016 file).

## Method

- **Tools:** Python 3.13, pandas 2.2, seaborn 0.13, matplotlib 3.8
- **Approach:**
  1. Compute daily ride counts per year.
  2. Calculate a 7-day centered moving average ("baseline") per year as
     the expected seasonal trend.
  3. Identify "dip events": periods where actual rides are at least 20%
     below the baseline for **2 or more consecutive days**. The 20%
     threshold filters out minor fluctuations; the 2-day minimum filters
     isolated one-off drops (e.g., a single holiday).
  4. For each dip event, record start date, end date, duration, maximum
     drop percentage, total lost trips, and the ride count at the start
     and lowest point.
- **What this captures:** Snow/ice events where ridership drops sharply
  and stays low until streets are cleared or bikes are rebalanced. Also
  captures system outages, major storms, and holidays that span multiple
  days.
- **What this does NOT capture:** Single-day anomalies (filtered out by
  the 2-day minimum), gradual seasonal decline (captured by the baseline),
  or infrastructure issues that reduce ridership by <20%.

## How to reproduce

```bash
pip install -r requirements.txt
python analyze.py
```

Expected runtime: ~2–3 minutes on a laptop (loads 30M+ rows).
Expected output: 1 figure + 2 CSVs.

## Results

Run `analyze.py` to populate. See `outputs/dip-events.csv` for the full
list of sustained dip events, sorted by total lost trips.

## Caveats

- This detects **statistical** dips, not **causal** events. A dip
  could be caused by snow, ice, rain, system maintenance, a holiday
  weekend, or a combination. Correlation is not causation.
- The 20% threshold is arbitrary. Lowering it catches more events but
  includes minor dips; raising it catches only severe disruptions.
- The 2-day minimum excludes single-day drops (e.g., a single severe
  storm day that recovers the next day).
- The 7-day moving average baseline smooths over the dip itself, so
  very long dips (>7 days) may have an inflated baseline. This is
  acceptable for detecting the onset of dips.
- January and February are included because winter infrastructure
  disruptions (snow clearing delays, ice) are exactly the events this
  analysis is designed to detect.
- 2026 is partial year (Jan–Mar only).
- 2022 is missing January data from the upstream ZIP.

## Files

- `analyze.py` — main script
- `requirements.txt` — pinned Python deps
- `outputs/` — figures and CSVs (generated; `dip-events.csv` and
  `daily-rides.csv` are tracked, PNG figures are gitignored)