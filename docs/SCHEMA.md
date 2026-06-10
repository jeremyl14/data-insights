# Catalog schema

The catalog is `catalog/datasets.csv`. This document describes every column,
whether it's required, and the controlled vocabularies where applicable.

## Required columns

| Column | Type | Notes |
|---|---|---|
| `id` | string (slug) | Lowercase kebab-case. Must match the folder name under `datasets/`. **Never renamed.** |
| `name` | string | Human-readable title. |
| `source` | enum | `toronto`, `ontario`, `statcan`, `canada-open-data`, `other` — add to this list in a PR if needed. |
| `source_id` | string | Upstream's package/dataset identifier. For CKAN, the UUID. For Socrata, the dataset id. |
| `url` | URL | Canonical human-readable page. |
| `api_url` | URL | Machine-readable endpoint (CKAN `package_show`, Socrata SODA, etc.). Optional but encouraged. |
| `license` | enum | `OGL-Ontario`, `ODC-BY`, `CC-BY`, `CC-BY-SA`, `CC0`, `custom:<name>`. |
| `format` | enum | `csv`, `json`, `geojson`, `parquet`, `xlsx`, `xml`, `api`, `mixed`. |
| `tags` | csv-list | Comma-separated, lowercase, kebab-case. Multi-valued. See canonical tag list below. New tags welcome but should be added to the list. |
| `refresh_frequency` | enum | `hourly`, `daily`, `weekly`, `monthly`, `quarterly`, `annual`, `manual`, `never`. |
| `last_fetched` | ISO date | When we last pulled a snapshot. Empty if never. |
| `last_verified` | ISO date | When we last confirmed upstream still exists & metadata matches. |
| `size_mb` | float | Approximate size of one full snapshot. |
| `data_storage` | enum | Where the raw file actually lives. `git` (committed), `gitignore+fetch` (raw/SOURCE.md + re-fetch command), `dvc`. See ADR-009. |
| `status` | enum | `active`, `draft`, `deprecated`, `broken`. |
| `added_by` | string | GitHub username. |
| `added_on` | ISO date | When this row was created. |
| `superseded_by` | slug | If deprecated, the new slug. Empty otherwise. |
| `notes` | string | Freeform, one line. |

## Conventions

- **Empty fields are empty strings**, not `NA` / `null` / `None`. Spreadsheets
  and CSV parsers handle `""` consistently.
- **Tag format**: lowercase, kebab-case, comma-separated, no spaces around
  commas. Example: `"health,transport,active-mobility"`.
- **License format**: short tokens, never free text. If you need a custom
  license, prefix with `custom:` and put the full text in `notes` or in
  `datasets/<slug>/raw/SOURCE.md`.
- **Dates**: ISO 8601 (`YYYY-MM-DD`). UTC for `last_fetched` so we can
  compute durations without timezone math; the harvester handles this.
- **Sizes**: megabytes with one decimal. Don't worry about precision.

## Status lifecycle

```
draft → active → deprecated
                ↘ broken
```

- `draft` — added but not yet snapshotted. Will be flagged by CI if older
  than 30 days.
- `active` — current, upstream reachable, snapshot present.
- `deprecated` — replaced by a newer dataset; `superseded_by` is required.
- `broken` — upstream URL is dead. We keep the local copy + metadata.
  Should be re-checked quarterly.

## Canonical tag list

Tags are free-form but should use these canonical forms when they apply.
The validator warns on tags not in this list. To add a new tag, update
both this list and the `CANONICAL_TAGS` set in `_scripts/validate.py`.

| Tag | Description |
|---|---|
| `transport` | Public transit, roads, cycling infrastructure |
| `transit` | Subset of transport: buses, subways, streetcars |
| `active-mobility` | Walking, cycling, scooter share |
| `health` | Public health, epidemiology, hospital data |
| `demographics` | Population, census, age/income breakdowns |
| `environment` | Air quality, emissions, weather |
| `climate` | Long-term climate trends |
| `energy` | Electricity, natural gas, fuel production |
| `infrastructure` | Buildings, utilities, signals |
| `housing` | Rental market, construction permits |
| `safety` | Crime, emergency services |
| `economy` | Employment, GDP, business registrations |
| `education` | Schools, enrolment, literacy |

## Validation rules (enforced by CI)

- `id` matches `^[-a-z0-9]+$` and matches a folder in `datasets/`.
- `status` is one of the allowed values.
- `license` is one of the allowed values.
- `url` returns HTTP 200 on HEAD.
- Every folder in `datasets/` has a matching CSV row.
- Every CSV row has a matching folder (unless `status: broken` and the
  local copy is documented in `notes`).

## Adding a new column

Don't. Open an issue first. New columns need a migration story:
- Edit this file
- Add a `migrations/00X_add_<column>.md` describing the backfill plan
- Update `docs/DECISIONS.md` with the rationale
- Update `_scripts/query.py` to handle missing values gracefully for old rows
