# Dataset README template

Copy this file to `datasets/<your-slug>/README.md` and fill in every
section. Required sections are marked with **(required)**.

---

# <Dataset name>

Slug: `<your-slug>` (must match the folder name and the CSV `id`)
Status: `active` | `draft` | `deprecated` | `broken`
Added: YYYY-MM-DD

## Source (required)

- **Publisher:** <e.g. City of Toronto, Province of Ontario>
- **Portal:** <data.ontario.ca | open.toronto.ca | other>
- **URL:** <link to the dataset's portal page>
- **API endpoint:** <CKAN package_show URL or Socrata SODA endpoint, if any>
- **Source ID:** <upstream's package/dataset id>
- **First available:** <earliest year/date>
- **Last updated upstream:** <date>

## License (required)

- **License:** <OGL-Ontario | ODC-BY | CC-BY | CC0 | custom: name>
- **Verbatim text:** <link to the upstream license page>

## What's in the data (required)

Briefly describe each table/file in the snapshot. One section per file
if there are multiple.

### `data.csv`
- **Format:** CSV
- **Encoding:** UTF-8
- **Approx rows:** 1,500,000
- **Update cadence:** monthly
- **Fields:**
  - `trip_id` (int) — unique trip identifier
  - `start_time` (datetime) — ISO 8601
  - `end_time` (datetime)
  - `start_station_id` (int)
  - `end_station_id` (int)
  - `bike_id` (int)
  - `user_type` (enum: `casual`, `member`)

### Other files
- `stations.csv` — station metadata (id, name, lat, lon, capacity)

## Refresh & verification (required)

- **Refresh frequency:** <hourly | daily | weekly | monthly | quarterly | annual | manual | never>
- **Last fetched:** YYYY-MM-DD
- **Last verified:** YYYY-MM-DD (by <github-user>)
- **Verification method:** <e.g. "HEAD-checked URL, compared file count to upstream">
- **Storage strategy:** `git` | `gitignore+fetch` | `dvc` | `external:<provider>`.
  See `docs/DECISIONS.md` ADR-009. For `gitignore+fetch` and external,
  the catalog `data_storage` column must match.
- **Known re-fetch procedure:**
  ```bash
  # the curl/wget/whatever command that reproduces the snapshot
  ```

## How to use (required)

One or two paragraphs. What's the canonical way to load this in Python / R /
DuckDB? Include a working snippet.

```python
import pandas as pd
df = pd.read_csv("datasets/toronto-bike-share/raw/data.csv", parse_dates=["start_time", "end_time"])
```

## Notes (required, can be empty)

Caveats, known issues, things the upstream doesn't tell you:
- 2020 data is incomplete due to pandemic closures.
- Some station IDs changed after the 2019 re-numbering; cross-reference
  with `stations.csv`.

## Provenance

See `raw/SOURCE.md` for the exact snapshot date, hash, and license text.

## Analyses

List analyses that have been done on this dataset. Each lives in
`analysis/<analysis-name>/`.

- (none yet)

---

## Author

<github-user>, YYYY-MM-DD
