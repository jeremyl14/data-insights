# Bike Share Toronto Ridership

Slug: `toronto-bike-share`
Status: `active`
Added: 2026-06-08

## Source

- **Publisher:** City of Toronto — Toronto Parking Authority
- **Portal:** open.toronto.ca
- **URL:** https://open.toronto.ca/dataset/bike-share-toronto-ridership-data/
- **API endpoint:** https://ckan0.cf.opendata.inter.prod-toronto.ca/api/3/action/package_show?id=bike-share-toronto-ridership-data
- **Source ID:** `7e876c24-177c-4605-9cef-e50dd74c617f`
- **First available:** 2014
- **Last updated upstream:** monthly

## License

- **License:** ODC-BY
- **Verbatim text:** https://open.toronto.ca/open-data-license/

## What's in the data

Per-year ridership CSVs from 2014 to 2026 (partial). Each file contains
individual trip records. Earlier years (2014–2019) use quarterly formats;
2020+ uses monthly or consolidated formats. All have been concatenated
into one CSV per year with a single header row.

| File | Rows | Size | Source format |
|------|------|------|---------------|
| `raw/bike-share-toronto-ridership-2014-2015.csv` | 4,325 | 100 KB | XLSX → CSV |
| `raw/bike-share-toronto-ridership-2016.csv` | 367,962 | 40 MB | XLSX → CSV |
| `raw/bike-share-toronto-ridership-2017.csv` | 1,492,369 | 156 MB | ZIP (quarterly) |
| `raw/bike-share-toronto-ridership-2018.csv` | 1,922,955 | 228 MB | ZIP (quarterly) |
| `raw/bike-share-toronto-ridership-2019.csv` | 2,439,517 | 307 MB | ZIP (quarterly) |
| `raw/bike-share-toronto-ridership-2020.csv` | 2,911,308 | 369 MB | ZIP (monthly) |
| `raw/bike-share-toronto-ridership-2021.csv` | 3,575,182 | 452 MB | ZIP (monthly) |
| `raw/bike-share-toronto-ridership-2022.csv` | 4,300,240 | 534 MB | ZIP (monthly; missing Nov, superseded) |
| `raw/2026-10-31/bike-share-toronto-ridership-2022.csv` | 4,620,469 | 573 MB | ZIP (monthly, incl. nested Nov ZIP) |
| `raw/bike-share-toronto-ridership-2023.csv` | 5,713,141 | 691 MB | ZIP (monthly) |
| `raw/bike-share-toronto-ridership-2024.csv` | 6,953,094 | 925 MB | ZIP (consolidated) |
| `raw/bike-share-toronto-ridership-2025.csv` | 7,812,520 | 1,014 MB | ZIP (monthly) |
| `raw/bike-share-toronto-ridership-2026.csv` | 552,073 | 74 MB | ZIP (partial year, Jan–Mar; superseded) |
| `raw/2026-10-30/bike-share-toronto-ridership-2026.csv` | 6,830,174 | 901 MB | ZIP (partial year, Jan–Sep) |

### Common fields (all years)

- `trip_id` (int) — unique trip identifier
- `trip_start_time` (datetime) — ISO 8601
- `trip_stop_time` (datetime)
- `from_station_id` (int)
- `from_station_name` (string)
- `to_station_id` (int)
- `to_station_name` (string)
- `user_type` (enum: `casual`, `member`)

Column names vary slightly across years; see `raw/SOURCE.md` for details.

### `raw/bike-share-stations.csv`

- **Format:** CSV, ~700 rows
- **Fields:** `station_id`, `name`, `lat`, `lon`, `capacity`

## Refresh & verification

- **Refresh frequency:** monthly
- **Last fetched:** 2026-10-30 (2026 only; other years 2026-06-10)
- **Last verified:** 2026-10-30 (by @jeremyl14)
- **Verification method:** CKAN API `package_show` confirmed all year
  resources present and downloadable.
- **Storage strategy:** `dvc`. Raw files are tracked by DVC and
  stored in a Backblaze B2 bucket (`data-insights-raw`); small
  `.dvc` pointer files live in git. See `docs/DECISIONS.md` ADR-009
  and `_scripts/dvc_onboard.sh`.
- **Known re-fetch procedure:**
  ```bash
  # Download all years from upstream (ZIPs and XLSX)
  # See raw/SOURCE.md for per-year resource UUIDs and download URLs.
  # After downloading, extract/convert and rename:
  #   bikeshare-ridership-{YEAR}.csv → bike-share-toronto-ridership-{YEAR}.csv
  # Then:
  dvc add datasets/toronto-bike-share/raw/bike-share-toronto-ridership-{YEAR}.csv
  dvc push
  ```
  Or run: `python3 _scripts/snapshot.py --dataset toronto-bike-share`.

## How to use

```python
import pandas as pd

# Single year
trips_2024 = pd.read_csv(
    "datasets/toronto-bike-share/raw/bike-share-toronto-ridership-2024.csv",
    parse_dates=["trip_start_time", "trip_stop_time"],
)

# Multi-year (concatenate)
years = range(2017, 2025)
trips = pd.concat([
    pd.read_csv(
        f"datasets/toronto-bike-share/raw/bike-share-toronto-ridership-{y}.csv",
        parse_dates=["trip_start_time", "trip_stop_time"],
    )
    for y in years
], ignore_index=True)
```

## Notes

- 2014–2015 has very few rows (early program, limited station coverage).
- 2020-Q2 to 2021-Q3 data is sparse due to pandemic station closures;
  flag with `user_type` filters if comparing across years.
- Station IDs were re-numbered in 2019; join through `name` if you need
  to span the cutover.
- 2022: use `raw/2026-10-31/bike-share-toronto-ridership-2022.csv`
  (4,620,469 trips). The older `raw/bike-share-toronto-ridership-2022.csv`
  is missing November (320,229 trips): upstream ships that month as a ZIP
  nested inside the year's ZIP, and the 2026-06-10 snapshot only took the
  CSV members. Earlier notes said "January missing", which was wrong.
  See `raw/2026-10-31/SOURCE.md`.
- 2017 Jul–Dec rows have only 7 columns (no station IDs) but sit under
  the 9-column Jan–Jun header, so those rows don't line up with the
  column names.
- 2026 is partial-year. Use `raw/2026-10-30/bike-share-toronto-ridership-2026.csv`
  (Jan–Sep); the older `raw/bike-share-toronto-ridership-2026.csv` is
  Jan–Mar only and has pre-rename station names. See
  `raw/2026-10-30/SOURCE.md`.
- The official open data portal lags 2–3 months. Third-party sources
  like BikeRacoon (https://github.com/mjarrett/bikeraccoon) provide
  more timely data by estimating trips from GBFS station availability
  changes, but these are estimates (~2% undercount, not official trip
  records) and are not comparable to this dataset. See `raw/SOURCE.md`
  for details.
- Column names vary slightly across years (e.g., `Trip Id` vs `trip_id`,
  `Bike Id` present in some years). Clean before concatenating.

## Provenance

See `raw/SOURCE.md` for the exact snapshot date, per-file hashes, and
license text.

## Analyses

- `analysis/seasonal-ridership/` — first analysis. Ridership by month,
  year-over-year change, and weekday vs weekend split.
- `analysis/station-activity-map/` — animated map of 7-day station
  activity (starts + ends), 2018 – Sep 2026, with historical station
  locations.