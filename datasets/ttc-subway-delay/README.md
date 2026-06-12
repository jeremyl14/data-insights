# TTC Subway Delay Data

Slug: `ttc-subway-delay`
Status: `active`
Added: 2026-06-10

## Source (required)

- **Publisher:** Toronto Transit Commission (TTC), via City of Toronto Open Data
- **Portal:** https://open.toronto.ca/dataset/ttc-subway-delay-data/
- **URL:** https://open.toronto.ca/dataset/ttc-subway-delay-data/
- **API endpoint:** https://ckan0.cf.opendata.inter.prod-toronto.ca/api/3/action/package_show?id=996cfe8d-fb35-40ce-b569-698d51fc683b
- **Source ID:** 996cfe8d-fb35-40ce-b569-698d51fc683b
- **First available:** 2014-01 (historical XLSX); 2025-01 (live CSV datastore)

## License (required)

- **License:** custom:OGL-Toronto
- **Verbatim text:** https://open.toronto.ca/open-data-license/

## What's in the data (required)

### `ttc-subway-delay-data-since-2025.csv`
- **Format:** CSV
- **Encoding:** UTF-8
- **Approx rows:** 35,385 (Jan 2025 – present, growing monthly)
- **Update cadence:** monthly (live datastore dump)
- **Fields:**
  - `_id` (int) — datastore row ID
  - `Date` (date) — date of delay event (YYYY-MM-DD)
  - `Time` (time) — approximate time of delay (HH:MM, 24h)
  - `Day` (string) — day of week
  - `Station` (string) — TTC station name (e.g., "BATHURST STATION")
  - `Code` (string) — TTC delay code (e.g., MUSAN, MUIRS)
  - `Min Delay` (int) — reported delay duration in minutes
  - `Min Gap` (int) — gap between trains caused by delay, in minutes
  - `Bound` (string) — direction (E/W/N/S or blank)
  - `Line` (string) — subway line code (YU, BD, SRT, SHP)
  - `Vehicle` (int) — vehicle number

### `ttc-subway-delay-codes.xlsx`
- **Format:** XLSX
- **Rows:** 130
- **Fields:** Code, Code Description (for YU and SRT/BD lines separately)

## Refresh & verification (required)

- **Refresh frequency:** monthly
- **Last fetched:** 2026-06-10
- **Last verified:** 2026-06-10 (by jeremyl14)
- **Verification method:** HEAD-checked URL, confirmed 35,385 rows for 2025+
- **Storage strategy:** `git` (total ~3 MB, well under threshold)
- **Known re-fetch procedure:**
  ```bash
  curl -L -o raw/ttc-subway-delay-data-since-2025.csv \
    "https://ckan0.cf.opendata.inter.prod-toronto.ca/dataset/996cfe8d-fb35-40ce-b569-698d51fc683b/resource/0b6e5c52-e993-46d6-8d74-8602ee224457/download/ttc-subway-delay-data-since-2025.csv"
  curl -L -o raw/ttc-subway-delay-codes.xlsx \
    "https://ckan0.cf.opendata.inter.prod-toronto.ca/dataset/996cfe8d-fb35-40ce-b569-698d51fc683b/resource/3900e649-f31e-4b79-9f20-4731bbfd94f7/download/ttc-subway-delay-codes.xlsx"
  ```

## How to use (required)

```python
import pandas as pd

delays = pd.read_csv("datasets/ttc-subway-delay/raw/ttc-subway-delay-data-since-2025.csv")
delays["Date"] = pd.to_datetime(delays["Date"])
# Filter to 2025
delays_2025 = delays[delays["Date"].dt.year == 2025]
```

## Notes (required)

- Station names use TTC internal format (e.g., "BATHURST STATION", "DUNDAS STATION").
  Need normalization for spatial joins with bike-share station data.
- `Min Delay` of 0 means the delay was reported but duration was not recorded or
  was under 1 minute.
- Historical data (2014–2024) is available as separate XLSX files per year
  from the portal but is not included in this snapshot.
- The 2025+ file is a live datastore dump that grows; re-fetching will add new months.

## Provenance

See `raw/SOURCE.md` for the exact snapshot date, hash, and license text.

## Analyses

- `../toronto-bike-share/analysis/subway-delay-impact/` — subway disruption effect on bike-share ridership

---

## Author

jeremyl14, 2026-06-10