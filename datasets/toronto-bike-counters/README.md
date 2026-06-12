# Toronto Permanent Bicycle Counters

Slug: `toronto-bike-counters`
Status: `active`
Added: 2026-06-10

## Source (required)

- **Publisher:** City of Toronto Transportation Services
- **Portal:** https://open.toronto.ca/dataset/permanent-bicycle-counters/
- **URL:** https://open.toronto.ca/dataset/permanent-bicycle-counters/
- **API endpoint:** https://ckan0.cf.opendata.inter.prod-toronto.ca/api/3/action/package_show?id=ff7e7369-cbba-4545-9e26-e5a5ef6a123c
- **Source ID:** ff7e7369-cbba-4545-9e26-e5a5ef6a123c
- **First available:** 1994-06-26

## License (required)

- **License:** ODC-BY
- **Verbatim text:** https://open.toronto.ca/open-data-licence/

## What's in the data (required)

Permanent inductive loop counters on Toronto streets and multi-use paths counting passing bicycles at 15-minute resolution. All count files join to the locations file via `location_dir_id`.

### `cycling-permanent-counts-locations.csv`
- **Format:** CSV
- **Encoding:** UTF-8
- **Approx rows:** 43
- **Fields:**
  - `_id` (int) — row ID
  - `location_dir_id` (int) — unique counter ID (join key)
  - `location_name` (string) — street location description
  - `direction` (string) — Eastbound/Westbound/Northbound/Southbound
  - `linear_name_full` (string) — street name
  - `side_street` (string) — nearest cross street
  - `longitude` (float), `latitude` (float) — coordinates
  - `centreline_id` (int) — City centreline ID
  - `bin_size` (string) — time bin (always 00:15:00)
  - `latest_calibration_study` (date) — last calibration
  - `first_active` (date) — first data date
  - `last_active` (date) — last data date
  - `date_decommissioned` (date) — retirement date (blank if active)
  - `technology` (string) — counter type (all "Induction - Eco-Counter" or "Induction - Other")

### `cycling-permanent-counts-daily.csv`
- **Format:** CSV
- **Rows:** ~52,900
- **Fields:** `_id`, `location_dir_id`, `location_name`, `direction`, `linear_name_full`, `side_street`, `dt` (date), `daily_volume`

### `cycling-permanent-counts-15min-2025-2026.csv`
- **Format:** CSV (DVC-tracked, ~30 MB)
- **Rows:** ~1.2M
- **Fields:** `_id`, `location_dir_id`, `datetime_bin` (ISO datetime), `bin_volume`

### `cycling-permanent-counts-15min-2024-2025.csv`
- **Format:** CSV (DVC-tracked, ~29 MB)
- **Rows:** ~1.1M
- **Fields:** same as above

### `cycling-permanent-counts-15min-1994-2024.csv`
- **Format:** CSV (DVC-tracked, ~83 MB)
- **Rows:** ~3.3M
- **Fields:** same as above

## Refresh & verification (required)

- **Refresh frequency:** monthly
- **Last fetched:** 2026-06-10
- **Last verified:** 2026-06-10 (by jeremyl14)
- **Verification method:** HEAD-checked URL, confirmed row counts
- **Storage strategy:** `dvc` for 15-min files (29–83 MB each); `git` for locations (8 KB) and daily (5.2 MB)
- **Known re-fetch procedure:**
  ```bash
  cd datasets/toronto-bike-counters/raw
  # Small files (git-tracked)
  curl -L -o cycling-permanent-counts-locations.csv \
    "https://ckan0.cf.opendata.inter.prod-toronto.ca/dataset/ff7e7369-cbba-4545-9e26-e5a5ef6a123c/resource/217a6e7f-c980-46ab-ba06-6d10b5499194/download/cycling_permanent_counts_locations.csv"
  curl -L -o cycling-permanent-counts-daily.csv \
    "https://ckan0.cf.opendata.inter.prod-toronto.ca/datastore/dump/b6fdab07-bf2f-4c30-8b68-d4cde7674941"
  # Large files (DVC-tracked) — download then dvc add
  curl -L -o cycling-permanent-counts-15min-2025-2026.csv \
    "https://ckan0.cf.opendata.inter.prod-toronto.ca/dataset/ff7e7369-cbba-4545-9e26-e5a5ef6a123c/resource/473fd887-9741-49ca-9816-bbe589ecf3a6/download/cycling_permanent_counts_15min_2025_2026.csv"
  curl -L -o cycling-permanent-counts-15min-2024-2025.csv \
    "https://ckan0.cf.opendata.inter.prod-toronto.ca/dataset/ff7e7369-cbba-4545-9e26-e5a5ef6a123c/resource/49675bd6-a17c-4de7-af66-c0e8338d7d13/download/cycling_permanent_counts_15min_2024_2025.csv"
  curl -L -o cycling-permanent-counts-15min-1994-2024.csv \
    "https://ckan0.cf.opendata.inter.prod-toronto.ca/dataset/ff7e7369-cbba-4545-9e26-e5a5ef6a123c/resource/1da069cb-ee75-4698-96ec-fdf70ff3e964/download/cycling_permanent_counts_15min_1994_2024.csv"
  dvc add cycling-permanent-counts-15min-*.csv
  dvc push
  sha256sum *.csv
  ```

## How to use (required)

```python
import pandas as pd

REPO = "datasets/toronto-bike-counters/raw"

locs = pd.read_csv(f"{REPO}/cycling-permanent-counts-locations.csv")
daily = pd.read_csv(f"{REPO}/cycling-permanent-counts-daily.csv", parse_dates=["dt"])

# Merge daily counts with location metadata
merged = daily.merge(locs[["location_dir_id", "location_name", "direction"]],
                     on="location_dir_id", how="left")

# For 15-min data (DVC-tracked, run `dvc pull` first):
# df15 = pd.read_csv(f"{REPO}/cycling-permanent-counts-15min-2025-2026.csv")
```

## Notes (required)

- Counter IDs are stable across all files — join on `location_dir_id`.
- Many locations have EB/WB or NB/SB pairs (same street, two directions) with separate IDs.
- Some counters are retired (`date_decommissioned` set). Their data is still in the historical files.
- The 1994–2024 15-min file is large (83 MB). Use the daily file for most trend analyses.
- Counter gaps: data may have missing days if a counter was offline.
- The Bloor St Castle Frank counter (IDs 1–2, active 1994–2019) is the longest-running; it was replaced by IDs 746–747 in 2025.
- Yonge St has the densest coverage (6 sites from Bloor to St Clair).

## Provenance

See `raw/SOURCE.md` for the exact snapshot date, hash, and license text.

## Analyses

- [consolidated-ridership-stats](analysis/consolidated-ridership-stats/README.md) — aggregated volumes, seasonal/day-of-week patterns, YoY growth across all active counters
- [yoy-traffic-percentiles](analysis/yoy-traffic-percentiles/) — How does each counter's 2025 daily cycling volume compare to its own history?
- [station-outlier-deltas](analysis/station-outlier-deltas/) — which counters had unusual 2025 deviations from baseline

---

## Author

jeremyl14, 2026-06-10