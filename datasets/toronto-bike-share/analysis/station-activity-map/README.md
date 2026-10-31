# Bike Share Toronto: Station Activity Map, 2018–2026

Dataset: `toronto-bike-share`
Author: jeremyl14
Date: 2026-10-31

## Question (required)

How have the intensity and the geographic distribution of Bike Share
Toronto use changed over time? Where is riding concentrated on a given
day, how has that footprint spread as the network grew, and does the
pattern look different once overall growth is factored out?

## Data (required)

- **Primary dataset:** [`toronto-bike-share`](../../README.md)
- **Joins with:** station locations from the Bike Share Toronto GBFS feed
  and its Wayback Machine captures; City of Toronto 25-ward boundaries and
  waterbodies (Lake Ontario, the harbour and Toronto Island lagoons) for
  the base map (see [`inputs/SOURCE.md`](inputs/SOURCE.md))
- **Snapshot dates:** `raw/bike-share-toronto-ridership-{2018–2021,2023–2025}.csv`
  (snapshot 2026-06-10), `raw/2026-10-31/bike-share-toronto-ridership-2022.csv`
  (2022 re-snapshot that includes November, which the 2026-06-10 file
  dropped), and `raw/2026-10-30/bike-share-toronto-ridership-2026.csv`
  (Jan–Sep 2026)
- **Filters applied:**
  - 2018-01-01 to 2026-09-30. Earlier trip files have no station IDs
    (2016, and Jul–Dec 2017), so they can't be placed reliably.
  - Endpoints with a blank/`NULL` station ID, an unparseable time, or a
    station ID not in the station table are excluded
    (0.01–0.03% per year; see `outputs/summary.csv`).

## Method (required)

- **Tools:** Python 3.14, DuckDB 2.0, NumPy 2.5; the figure is a
  self-contained HTML page (canvas, no external libraries)
- **Approach:** Count every trip twice — once at its start station on its
  start date and once at its end station on its end date — giving daily
  "activity" per station. Each map frame is the 7-day rolling sum ending
  on that day, coloured on one fixed cube-root scale so frames are
  comparable across the whole period. (A log scale spent most of the ramp
  on quiet stations, so the roughly 2× growth of busy downtown stations
  moved them only ~9% along it; a square-root scale fixed that but pushed
  quiet stations into the palest steps. Cube root sits between the two:
  5 trips/week → 12% of the ramp, 100 → 32%, and a median downtown
  station's 2018→2026 growth spans 15%.) The ramp's palest steps are
  trimmed so every dot clears the map background. A second view colours each station
  by its share of that frame's system-wide activity, which separates
  *where* riding happens from *how much* there is.
- **Key transformations:**
  1. Read each year's CSV as text with DuckDB and parse times per year
     (2018 `M/D/YYYY H:MM`; 2019–2023 `MM/DD/YYYY HH:MM`, verified
     month-first; 2024+ ISO). 249 rows in 2020 are missing the duration
     column, which shifts later fields left by one; they are detected and
     read with the shifted layout.
  2. Aggregate to (station ID, day) counts of starts + ends.
  3. Join each station-day to the station location valid on that date
     (`inputs/station-locations.csv`), so moved stations and reused IDs
     are drawn in the right place.
  4. 7-day rolling sums per station; system total = sum over stations.
  5. Detect missing data as runs of ≥ 3 days with no trip starts. Frames
     whose window overlaps a gap would be flagged incomplete and excluded
     when setting the colour range. With the 2022 re-snapshot, none are
     found; the check stays so a future gap can't pass as zero use.
  6. Colour range: trips view, cube-root scale from 0 to the 99.9th
     percentile of non-zero station-weeks (3,062; the 0.1% above it, mostly
     ferry docks and York St / Queens Quay W on summer weeks, share the top
     colour); share view, log scale from the 0.1th to the 99.9th percentile.
  7. Assign each station location to a ward (point-in-polygon) to report
     the share of activity in the three downtown wards.
- **Statistical test:** None; this is a descriptive visualization.

## How to reproduce (required)

```bash
pip install -r requirements.txt
dvc pull datasets/toronto-bike-share/raw/*.dvc datasets/toronto-bike-share/raw/2026-10-3*/*.dvc
python analyze.py
open outputs/station-activity-map.html

# optional: 14 s MP4 of the animation (needs ffmpeg with libx264; reads the HTML's data)
python render_video.py --seconds 14 --fps 30

# optional: rebuild the station/ward inputs (needs network)
python fetch_inputs.py --cache /tmp/wayback-cache
```

Expected runtime: ~20 seconds on a laptop (analyze.py)
Expected output: 1 interactive HTML figure (~6 MB) + 1 summary CSV

The page supports deep links, e.g.
`station-activity-map.html#date=2020-07-15&mode=share&center=43.632,-79.375&zoom=6`
(`zoom` is relative to the default view).

## Results (required)

| Year | Peak 7-day activity | Most stations active in a week | Activity in downtown wards¹ |
|---|---|---|---|
| 2018 | 141,128 (Aug 15) | 358 | 87.8% |
| 2019 | 203,146 (Aug 16) | 501 | 84.3% |
| 2020 | 243,380 (Aug 25) | 605 | 72.9% |
| 2021 | 263,248 (May 24) | 637 | 75.6% |
| 2022 | 343,198 (Aug 16) | 649 | 79.0% |
| 2023 | 367,359 (Aug 5) | 763 | 79.8% |
| 2024 | 457,049 (Sep 20) | 863 | 79.5% |
| 2025 | 565,164 (Jul 23) | 1,000 | 79.5% |
| 2026 (Jan–Sep) | 639,424 (Aug 19) | 1,070 | 78.8% |

¹ Wards 10 Spadina–Fort York, 11 University–Rosedale, 13 Toronto Centre.

- Peak weekly activity grew about 4.5× from 2018 to 2026, and the number
  of stations in use roughly tripled.
- The downtown share fell from 88% (2018) to 73% (2020) as the network
  expanded outward, then settled near 79% from 2022 onward: new outer
  stations add activity, but downtown use grew at a similar rate.
- In the share view, the waterfront (Queens Quay, the ferry docks, Ontario
  Place) dominates summer weeks throughout the period.

See `outputs/station-activity-map.html` and `outputs/summary.csv`.

## Caveats (required)

- **2022 uses the 2026-10-31 re-snapshot.** The 2026-06-10 file has no
  November trips (upstream ships that month as a nested ZIP, which the
  earlier snapshot skipped); analyses still reading that file undercount
  2022 by 320,229 trips.
- **Station locations come from periodic snapshots.** There are no
  archived station feeds between 2017-07 and 2019-08, or during 2018 and
  2020; a station that moved inside a gap is drawn at its old location
  until the next capture.
- **Activity counts trip endpoints, not riders or bikes.** A round trip
  counts twice at the same station.
- **"Downtown wards" uses today's 25-ward boundaries** for all years.
- Station IDs that are not in any station snapshot (pop-up and test
  stations such as 7219 "Fringe Next Stage") are excluded; they account
  for under 0.1% of endpoints in any year.
- Trips with very short or very long durations are not filtered.

## Files

- `analyze.py` — aggregation and HTML generation
- `fetch_inputs.py` — builds `inputs/` from the live/archived station feeds and ward boundaries
- `template.html` — the page `analyze.py` fills with data
- `render_video.py` — renders the animation to `outputs/station-activity-map.mp4` (1920×1080, 30 fps)
- `inputs/` — station locations, ward boundaries, water, provenance (`SOURCE.md`)
- `requirements.txt` — pinned Python deps
- `outputs/` — `station-activity-map.html` and `.mp4` (generated, not committed), `summary.csv`

## Future work

- Per-ward or per-neighbourhood aggregation as a second view.
- Add 2016–2017 by matching station names (names, not IDs, are all those
  files carry).

---

Author: jeremyl14, 2026-10-31
