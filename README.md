# data-insights

A collaborative repository for analyzing public datasets — a knowledge base
of **data + analysis + visualization** in the open.

This repo is **not** a data mirror. It is a knowledge base of public-data
insights, each backed by a reproducible analysis and a clear visualization.
Raw data stays upstream under its original license; we keep only what we need
to make analyses reproducible and reviewable.

---

## TL;DR for contributors

An **analysis** is a clear, reproducible look at a public dataset — with the
code that produced it, the visualization that communicates it, and a writeup
explaining what's shown and what the caveats are.

1. Pick a dataset from the [catalog](catalog/datasets.csv) (or add a new one).
2. Create a folder: `datasets/<your-slug>/` with a `README.md` following
   [the dataset template](docs/templates/DATASET_README.md).
3. Add a row to `catalog/datasets.csv` (use [the schema](docs/SCHEMA.md) and
   [the PR template](.github/PULL_REQUEST_TEMPLATE.md)).
4. Do your analysis in `datasets/<your-slug>/analysis/<analysis-slug>/`.
   Keep `raw/` immutable. Include at least one visualization in `outputs/`.
5. Open a PR. CI will validate the catalog and the structure.

That's it. No DB, no build system, no magic. **No real-time data** — only
batch snapshots of public datasets, analyzed and visualized.

---

## Goals

1. **Lower the bar for serious public-data work.** Most open-data analyses die
   in someone's Downloads folder. This repo makes them forkable, reviewable, and
   reproducible.
2. **Make provenance first-class.** Every analysis points back to a specific
   upstream snapshot, with a license and a hash. No "I think I downloaded this
   in 2023."
3. **Present data clearly, not just publish it.** "I downloaded the data and
   made some charts" is not enough. The analysis should explain what's shown
   (Question), how it was produced (Method), what the result is (Results),
   and what the limits are (Caveats). A reader who hasn't seen the data
   should understand the takeaway from the README alone.
4. **Be a learning artifact, not just a result.** Scripts should be readable
   by someone newer to the stack. Comments explain *why*, not just *what*.
5. **Stay boring.** Predictable structure, plain text metadata, minimal
   moving parts. Boring scales; clever rots.

## Non-goals

- Mirroring an entire portal. We curate.
- **Real-time data, period.** This repo is for batch-snapshot analysis of
  public datasets. No streaming pipelines, no live dashboards, no webhooks,
  no "always-on" anything. Data is downloaded on a schedule, snapshotted,
  and analyzed. A new analysis can be added at any time, but it always
  reads from a snapshot — never from a live source.
- Real-time dashboards or web apps (lives in a separate repo when it exists).
- Replacing the upstream portals' data quality work.
- Being a comprehensive statistics agency. We're analysts, not StatsCan.

---

## Principles & preferences

These are the design decisions behind the repo's structure. Read this section
before arguing with the structure.

### 1. CSV is the source of truth — no database
`catalog/datasets.csv` is **the** canonical metadata store. Not a SQLite file,
not a DuckDB dump, not YAML-in-disguise. A CSV.

Why: plain text, git-diffable, reviewable in a PR, editable in any spreadsheet
or text editor. The database-shaped problem ("filter by tag across 500 rows")
is solved in 5 lines of DuckDB or pandas at query time, not by maintaining a DB
file in the repo.

### 2. One folder per dataset, flat — no theme hierarchy
```
datasets/
├── <source>-<dataset-slug>/
├── <source>-<dataset-slug>/
├── <source>-<dataset-slug>/
└── ...
```
Tags/themes live in the catalog CSV, not in the directory structure. A dataset
can be `health,transport,climate` without you choosing one. Folders get
*politically* messy around 30+ datasets; tags don't.

### 3. Raw is read-only, processed is derived
```
datasets/<slug>/
├── README.md
├── raw/           # immutable snapshot from upstream
├── processed/     # cleaned / joined / re-shaped
└── analysis/      # notebooks, scripts, outputs
```
Never edit a file in `raw/`. If you need a different version, snapshot it again
under a new folder (`raw/2026-06-08/`) and update the README.

### 4. Provenance is mandatory, not optional
Every `raw/` directory contains a `SOURCE.md` with:
- The exact URL pulled
- The snapshot date
- The SHA-256 of the file(s)
- The license (verbatim from upstream)
- Any notes on what was excluded

If you can't fill that out, the snapshot isn't real and shouldn't be committed.

### 5. The slug is the foreign key
`datasets/<slug>/` matches the `id` column in the catalog. **Never rename a
slug.** If the human-readable name changes, change the `name` column. The slug
is what scripts, links, and citations point to.

If a dataset is superseded, set `status: deprecated` and `superseded_by: <new-slug>`
in the catalog. Leave the old folder in place with a `MOVED.md` pointing to the
new slug, so existing references don't break silently:

```markdown
# This dataset has been superseded

New slug: `<new-slug>`
See: `datasets/<new-slug>/`
```

### 6. Catalog edits go through PRs, never direct pushes to main
The CSV is reviewed like code. Use the PR template — it asks the questions
that catch 90% of catalog rot (license, source_id verification, last_fetched).

### 7. Public data, public process
Everything in this repo is meant to be readable on github.com without running
anything. The CSV is the homepage. The READMEs are the analyses.

---

## Repo structure

```
.
├── README.md                       # you are here
├── CONTRIBUTING.md                 # how to add a dataset / analysis
├── LICENSE.md                      # repo license + data licensing note
├── CODE_OF_CONDUCT.md
├── catalog/
│   ├── datasets.csv                # ⭐ source of truth
│   └── datasets.example.csv        # template for new contributors
├── datasets/
│   └── <slug>/
│       ├── README.md               # what this dataset is
│       ├── raw/
│       │   ├── SOURCE.md           # provenance
│       │   └── ...                 # immutable snapshot
│       ├── processed/
│       └── analysis/
├── _scripts/                       # shared utilities (harvesters, helpers)
│   ├── harvest_ckan.py             # populates catalog from a CKAN portal
│   ├── query.py                    # ad-hoc filter over datasets.csv
│   ├── validate.py                 # catalog + structure validation
│   ├── dvc_onboard.sh              # DVC + B2 one-time setup
│   ├── snapshot.py                 # per-dataset snapshot cadence
│   ├── csv_to_yaml.py              # CSV → per-dataset YAML migration tool
│   ├── dvc.env.example             # template for DVC credentials
│   └── pre-commit-raw-readonly.sh  # enforces raw/ immutability
├── docs/
│   ├── SCHEMA.md                   # catalog CSV columns
│   ├── DECISIONS.md                # architectural decision records (ADRs)
│   ├── CONCERNS.md                 # open issues / known risks
│   ├── STACK.md                    # languages, tools, why
│   └── templates/
│       ├── DATASET_README.md
│       └── ANALYSIS_README.md
├── .github/
│   ├── PULL_REQUEST_TEMPLATE.md
│   ├── ISSUE_TEMPLATE/
│   │   ├── new-dataset.md
│   │   └── bug-report.md
│   └── workflows/
│       ├── validate.yml            # catalog + structure checks
│       ├── revalidate-urls.yml     # quarterly URL HEAD checks
│       ├── reproduce-analysis.yml  # analysis reproducibility checks
│       └── dvc-snapshot-status.yml # daily snapshot dry-run report
├── .gitignore
├── .pre-commit-config.yaml
├── .editorconfig
├── requirements-dev.txt
└── AGENTS.md
```

---

## Quick start (analyst)

```bash
# Browse the catalog from your terminal
python _scripts/query.py --tag transport
python _scripts/query.py --source <source-name> --status active

# Or with DuckDB (read-only, no setup)
duckdb -c "SELECT id, name, license FROM read_csv_auto('catalog/datasets.csv') WHERE list_contains(string_split(tags, ','), 'health')"

# Start a new analysis
cp -r docs/templates/DATASET_README.md datasets/my-new-dataset/README.md
# ... fill it in, add a row to catalog/datasets.csv, open a PR
```

---

## Quick start (contributor adding a dataset)

See [CONTRIBUTING.md](CONTRIBUTING.md). TL;DR:

1. Fork, branch.
2. Create `datasets/<slug>/` with `README.md` + `raw/SOURCE.md` + the raw files (or a small `processed/` if you haven't snapshotted yet).
3. Add a row to `catalog/datasets.csv`.
4. Open the PR using the template. CI will yell if anything's off.

---

## License

- **Repo contents (code, docs):** MIT. See [LICENSE.md](LICENSE.md).
- **Data:** Each dataset retains its upstream license (recorded in the
  catalog's `license` column and in each `raw/SOURCE.md`). We do not
  relicense upstream data. By contributing a dataset folder, you confirm
  the data's license permits redistribution or that you are only including
  metadata + derived analysis, not the upstream data itself.

---

## Maintainers

- @jeremyl14

## See also

- [docs/DECISIONS.md](docs/DECISIONS.md) — why we made specific choices
- [docs/CONCERNS.md](docs/CONCERNS.md) — open issues, known risks, TODO
- [docs/SCHEMA.md](docs/SCHEMA.md) — catalog column reference
- [docs/STACK.md](docs/STACK.md) — languages & tools
