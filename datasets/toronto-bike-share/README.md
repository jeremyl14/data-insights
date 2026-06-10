# Bike Share Toronto Ridership

Slug: `toronto-bike-share`
Status: `draft`
Added: 2026-06-08

## Source

- **Publisher:** City of Toronto — Toronto Parking Authority
- **Portal:** open.toronto.ca
- **URL:** https://open.toronto.ca/dataset/bike-share-toronto-ridership-data/
- **API endpoint:** https://ckan0.cf.opendata.inter.prod-toronto.ca/api/3/action/package_show?id=bike-share-toronto-ridership-data
- **Source ID:** `bike-share-toronto-ridership-data`
- **First available:** 2014
- **Last updated upstream:** monthly

## License

- **License:** ODC-BY
- **Verbatim text:** https://open.toronto.ca/open-data-license/

## What's in the data

### `raw/bike-share-toronto-ridership-2024.csv`
- **Format:** CSV (extracted from ZIP)
- **Encoding:** UTF-8
- **Approx rows:** 4,500,000 (full year)
- **Update cadence:** monthly
- **Fields:**
  - `trip_id` (int) — unique trip identifier
  - `trip_start_time` (datetime) — ISO 8601
  - `trip_stop_time` (datetime)
  - `from_station_id` (int)
  - `from_station_name` (string)
  - `to_station_id` (int)
  - `to_station_name` (string)
  - `user_type` (enum: `casual`, `member`)

## Refresh & verification

- **Refresh frequency:** monthly
- **Last fetched:** —
- **Last verified:** —
- **Storage strategy:** `dvc`. Raw files will be tracked by DVC and
  stored in a Backblaze B2 bucket (`data-insights-raw`); small
  `.dvc` pointer files live in git. See `docs/DECISIONS.md` ADR-009
  and `_scripts/dvc_onboard.sh`.
- **Known re-fetch procedure:**
  ```bash
  # Snapshots are managed by DVC. To re-snapshot manually:
  # See raw/SOURCE.md for the download URL after first snapshot.
  dvc add datasets/toronto-bike-share/raw/bike-share-toronto-ridership-2024.csv
  dvc push
  ```
  Or run: `python3 _scripts/snapshot.py --dataset toronto-bike-share`.

## Notes

- 2020-Q2 to 2021-Q3 data is sparse due to pandemic station closures;
  flag with `user_type` filters if comparing across years.
- Station IDs were re-numbered in 2019; join through `name` if you need
  to span the cutover.

## Provenance

See `raw/SOURCE.md` for the exact snapshot date, hash, and license text.