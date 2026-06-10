# Stack

What we use, why, and what we'd consider switching to. Newest first.

## Languages

### Python
- **Used for:** harvesters, ETL scripts, data cleaning, anything
  procedural.
- **Why:** universal in data work, batteries-included, the default
  for CKAN/Socrata API clients.
- **Conventions:** PEP 8, type hints on function signatures, virtualenv
  per script group (`_scripts/py/<group>/requirements.txt`).

### R
- **Used for:** statistical analysis, ggplot2 visualizations.
- **Why:** Still the best for fast EDA and publication-quality plots
  in 30 lines.
- **Conventions:** tidyverse style, `renv` if reproducibility matters.
- **Status:** Not yet used in this repo; all current analyses use Python.

### SQL (via DuckDB)
- **Used for:** ad-hoc queries over processed data, joins across datasets.
- **Why:** DuckDB is fast, in-process, and reads parquet/csv/json natively.
  Lets us query without standing up a database server.
- **Status:** Plan, not yet in use.

### Markdown
- **Used for:** every doc, every README.
- **Why:** It's just text. Renders on GitHub. Diffable.

## Tools

### CKAN harvester (implemented)
- **Tool:** `ckanapi` Python client or direct HTTP to
  `/api/3/action/package_search`.
- **Both** data.ontario.ca and open.toronto.ca are CKAN instances.
- One harvester, two configs.
- **Script:** `_scripts/harvest_ckan.py`

### Socrata client (planned, toronto-only)
- **Tool:** `sodapy` Python client or direct SODA API calls.
- Toronto's open data portal exposes a Socrata-compatible SODA API
  in addition to CKAN. Some datasets are easier via SODA.

### Pre-commit / CI
- **Tool:** GitHub Actions, Python-based validators.
- **What it does:**
  - Schema-validates the catalog CSV
  - Cross-references folders ↔ CSV rows
  - HEAD-checks `url` column
  - Validates license vocabulary
  - Lints Python with `ruff`

### DuckDB (planned)
- **Used for:** ad-hoc analysis queries, not as a committed artifact.
- **Why:** Faster than pandas for joins, reads CSVs/parquet directly,
  no server required.

### DVC (Data Version Control)
- **Used for:** tracking raw data files >5 MB; storing the actual
  bytes in Backblaze B2 with small pointer files in git.
- **Why:** Git can't hold GBs of CSV history cleanly. DVC keeps
  content hashes in git, the data in cheap object storage, and the
  existing per-snapshot, immutable-raw model intact. B2 is the
  cheapest durable object storage the maintainer already has
  (restic backups run there too).
- **Scope:** Repo-wide, one B2 remote (`data-insights-raw`).
  Per-dataset subprojects later if needed.
- **S3 endpoint:** `s3.ca-east-006.backblazeb2.com` (region-
  specific; wrong region = silent 403).
- **Cadence:** Driven by the catalog's `refresh_frequency` column,
  not a hardcoded cron.
- **More:** `docs/DECISIONS.md` ADR-009, `_scripts/dvc_onboard.sh`,
  `_scripts/snapshot.py`.

## What we explicitly don't use

### Jupyter notebooks as the primary artifact
- **Why not:** They rot (output goes stale, no clear linear history).
  We use them for exploration, then commit a clean `.py` or `.R`
  script + a markdown explanation.
- **Exception:** If the notebook *is* the analysis (rare), it's committed
  with cleared output and explanatory markdown cells.

### YAML / TOML for the catalog
- **Why not:** Doesn't review as cleanly in PRs as CSV. Multi-row edits
  are painful. Spreadsheets don't read it.

### A database file in the repo
- **Why not:** Binary in git, no diffs, no clean merges. ADR-006.

### Heavy frameworks (Django, Rails, Next.js) in this repo
- **Why not:** This is a data + analysis repo. Web stuff lives in
  `data-insights-site` (separate repo, ADR-005).

## When to revisit the stack

- When harvester scripts exceed ~500 lines, consider refactoring into
  a small package.
- When we have 3+ analysts wanting different environments, consider
  Docker for `_scripts/`.
- When a contributor wants to use Julia / Polars / Observable — fine,
  document in DECISIONS.md if it's a structural change.
