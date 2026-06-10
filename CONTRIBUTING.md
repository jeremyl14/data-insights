# Contributing

Thanks for adding to the catalog. The bar to entry is intentionally low — a
CSV row, a README, and a snapshot — but the bar to *quality* is high: every
dataset needs to be reproducible by someone who isn't you.

## Two ways to contribute

### 1. Add a new dataset
For when the upstream has data worth analyzing and you want to capture it.

### 2. Add an analysis
For when you want to do actual work on an existing dataset. Smaller PRs, faster
review, no catalog churn.

You can do both in one PR. Just make sure the structure is clean.

---

## Adding a new dataset

### Step 1: Pick a slug
Lowercase, kebab-case, descriptive, stable. The slug is the foreign key for
the rest of the repo's life.

- ✅ `toronto-bike-share`
- ✅ `ontario-covid-cases`
- ❌ `covid` (too vague)
- ❌ `toronto_bike_share_2024` (underscores, dates in slugs)
- ❌ `BikeShare` (not kebab-case)

### Step 2: Create the folder

```bash
mkdir -p datasets/<slug>/{raw,processed,analysis}
cp docs/templates/DATASET_README.md datasets/<slug>/README.md
```

Fill in the dataset README. Required sections: Source, License, Fields,
Refresh, Status, Notes. See [docs/templates/DATASET_README.md](docs/templates/DATASET_README.md).

### Step 3: Snapshot the raw data

```bash
# Download the actual data
curl -L -o datasets/<slug>/raw/data.csv "https://...upstream.url..."

# Compute the hash
sha256sum datasets/<slug>/raw/data.csv
```

Then create `datasets/<slug>/raw/SOURCE.md`:

```markdown
# Source

- **URL:** https://...
- **Snapshot date:** 2026-06-08
- **SHA-256:** <hash>
- **License:** <verbatim from upstream>
- **Notes:** <anything excluded, encoding quirks, etc.>
```

### Step 4: Add a row to `catalog/datasets.csv`

Open the CSV, add a row. Required columns: `id`, `name`, `source`, `source_id`,
`url`, `license`, `tags`, `status`, `added_by`, `added_on`, `last_verified`.

See [docs/SCHEMA.md](docs/SCHEMA.md) for the full column reference.

### Step 5: Open the PR

Use the [PR template](.github/PULL_REQUEST_TEMPLATE.md). CI will:
- Verify the folder exists
- Verify the CSV row exists and matches the folder
- Verify the `README.md` is present
- HEAD-check the URL
- Validate the license string

If anything fails, fix it and push. Don't bypass CI by force-merging.

---

## Adding an analysis

You don't need to add a dataset to add an analysis. If a dataset already
exists in the catalog, just:

1. Create `datasets/<slug>/analysis/<your-analysis-name>/`
2. Add `README.md` (use [docs/templates/ANALYSIS_README.md](docs/templates/ANALYSIS_README.md))
3. Put code, notebooks, outputs in there
4. Open a PR

The analysis README is the most important file. It should let someone
reproduce your result without talking to you. Required: Question, Data,
Method, How to reproduce, Results, Caveats.

---

## Updating metadata

The catalog decays. Upstream URLs die, datasets get renamed, licenses change.

When you notice something is stale:
- Fix it in a PR. Keep the slug stable.
- If the dataset is now broken upstream, set `status: broken` in the CSV.
- If a new version exists, set `status: deprecated` and add a `superseded_by`
  column value pointing to the new slug. Don't delete the old one.

For major structural changes (new columns, schema migrations), open an
issue first to discuss.

---

## What we don't accept

- **Mirrored data we don't need.** If no analysis is planned and the dataset
  isn't useful in its own right, leave it upstream. We curate, not mirror.
- **Closed/proprietary data** unless you have explicit redistribution rights.
- **Personal data or anything with privacy concerns.** This is a public repo.
- **Generated/synthetic data** without clear disclosure in the README.

---

## Code style

- Python: PEP 8, type hints preferred, no NotImplemented placeholders in
  committed code.
- R: tidyverse style, project-friendly.
- SQL: lowercase keywords, one clause per line.
- Notebooks: clear markdown cells between code cells. Strip output on commit
  *unless* the output is the result (use `analysis/outputs/` for those).

If you don't have time to polish, mark the PR as a draft. Polish is welcome
later; clarity now matters more.

---

## Getting help

- Open an issue with the right template.
- Tag @jeremyl14 for review.
- For data-portal bugs, the upstream portals have their own issue trackers —
  link them rather than duplicating.

---

By contributing, you agree your contributions are MIT-licensed (the repo's
license) and that any data you include is shared under its upstream license
as recorded in the catalog.
