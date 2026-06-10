# Architectural decisions (ADRs)

This document records the **why** behind the repo's structure. If you're
going to argue with the structure, read this first. If your argument
succeeds, update this document so the next person doesn't re-litigate.

Format: lightweight ADR — context, decision, consequences. Newest first.

---

## ADR-009: Use DVC with Backblaze B2 for raw data >5MB

**Date:** 2026-06-09
**Status:** Accepted
**Supersedes:** ADR-008

### Context

Datasets over ~5 MB are too large to commit to git. Bike Share Toronto
is ~1 GB across yearly files. DVC + B2 is the storage strategy; small
datasets use `gitignore+fetch` (documented in `raw/SOURCE.md`).

### Decision

Use **DVC** (Data Version Control) with a **Backblaze B2** bucket
as the remote storage backend. Implementation:

- **Backend:** S3-compatible API on B2. DVC calls B2 by
  configuring an S3 remote with the bucket's S3 endpoint URL.
- **Bucket:** `data-insights-raw`. Existing B2 bucket the
  maintainer already provisioned for this project. Separate from
  the restic bucket (`lempert-sv-3-backup`) per existing
  infrastructure.
- **S3 endpoint URL:** `https://s3.ca-east-006.backblazeb2.com`
  (Canada East region). **This is bucket-region-specific**;
  visible in the B2 web UI under the bucket's "Endpoint" tab.
  Using the wrong region is a 403 — DVC will not give a
  diagnostic for this, it just fails the upload.
- **Credentials:** `/etc/dvc-env` (mode 600) on the cron host
  (likely lempert-sv-3). Loaded by `_scripts/dvc_onboard.sh` via
  the `DVC_ENV_FILE` env var. Bucket-scoped key with `listFiles` +
  `readFiles` + `writeFiles` is sufficient. The same key works for
  both the B2 native API and the S3-compatible API; B2 does not
  require a separate "S3 key" type.
- **Scope:** Repo-wide, one remote. Per-dataset subprojects later
  if a single dataset becomes too large to pull by default.
- **Snapshot cadence:** Per-dataset, derived from the catalog's
  `refresh_frequency` column. `_scripts/snapshot.py` reads the
  catalog, decides what's due, and runs `dvc add` + `dvc push`
  for each.
- **State:** `_scripts/.snapshot-state.json` (gitignored) tracks
  `last_snapshot` per dataset. Sidecar, not a catalog column, to
  avoid noisy diffs.
- **What gets committed:** `.dvc/config`, `dvc.yaml`, `dvc.lock`,
  and the `*.dvc` pointer files. The data itself lives in B2.
- **What doesn't get committed:** `.dvc/cache/` (local DVC cache,
  gitignored), `/etc/dvc-env` (credentials).

### Consequences

- ✅ Reproducible: every `*.dvc` pointer is content-addressed;
  the actual file's hash is in git.
- ✅ Cheap clone: pointer files are KB; the data is in B2 and
  pulled on demand with `dvc pull`.
- ✅ Per-dataset cadence driven by the catalog, not by hardcoded
  cron schedules.
- ✅ Immutable raw preserved (ADR-004 still applies; a new
  snapshot is a new `dvc add` operation).
- ✅ Pipeline tracking: `dvc repro` re-runs analyses only when
  inputs change. Useful as analyses mature.
- ❌ Adds a system: contributors need DVC, the env file, and a
  way to `dvc pull`. Documented in `_scripts/dvc_onboard.sh`
  and `agents/cataloger.md`.
- ❌ DVC version drift: the snapshot script uses `dvc` from PATH;
  a future DVC major version may change the CLI. Pin a known-good
  version in `requirements-dev.txt` (now committed).
- ❌ The S3 endpoint URL is **bucket-region-specific** and easy
  to get wrong. A 403 from `dvc push` could be wrong endpoint,
  wrong key, or wrong bucket. The diagnostic is unclear.

### Snapshot semantics: replace on each release

For datasets whose upstream publishes **cumulative-current-year**
data (e.g., Bike Share Toronto trips so far this year), each new
release replaces the prior raw file. The new file is a superset
of the prior file (more rows, same columns). The repo's strategy:

- The local raw file is overwritten on each snapshot.
- The git history records the change (old `.dvc` pointer vs new).
- The old bytes live forever in B2 at `snapshots/files/md5/<old-hash>`.
- DVC's content-addressed store never garbage-collects; the
  old version is recoverable via `git checkout <old-commit> && dvc checkout`.
- B2 versioning is **not** needed; DVC's content store is the
  version store. B2 versioning would be two systems doing the same job.

**Superset check** (added 2026-06-09): for `data_storage: dvc`
datasets, the snapshot script extracts the prior raw file from
B2 (by reading the .dvc pointer's MD5) and compares it line-by-line
against the new file. The check:

1. New file is **smaller** than prior → ⚠️ WARN (likely truncated
   history).
2. New file is missing lines that were in the prior → ⚠️ WARN
   (likely row deletion or upstream correction).
3. Otherwise → OK.

The check **warns but does not block** — the upstream's new file
is the new ground truth; we can't refuse to commit it. The warning
is for visibility so a human can investigate. See `_scripts/snapshot.py`
(`fetch_prior_snapshot` + `verify_superset`).

Three strategies considered, replace is the chosen one:

| Strategy | Storage cost | Audit | Verdict |
|---|---|---|---|
| **Replace on each snapshot** | Constant | git log of `raw/SOURCE.md` + .dvc history | ✅ **Chosen** |
| Append each release (keep all) | Linear (release count × annual size) | Same as replace, but with N copies | Overkill for cumulative data |
| Delta-only snapshots | Baseline + small per-release | More complex, harder to reason about | Overengineering for single-maintainer |

**Other semantics** (catalog value `data_storage` does not encode these;
the `replace` behavior is implicit for all `dvc` datasets):

- `append` (rare): upstream data is event-sourced, e.g. raw events
  that we want to keep even when an "all-of-2026" view exists.
  Strategy: never delete local; DVC pointer for each append.
- `delta` (very rare): upstream publishes deltas only. Strategy:
  baseline + ordered deltas in B2; rebuild-on-read.

For this project, all current datasets use `replace` semantics.

For datasets under ~5 MB, use `data_storage: git` (committed) or
`data_storage: gitignore+fetch` (re-fetch procedure documented in
`raw/SOURCE.md`). The "raw is immutable" rule (ADR-004) and the
"raw/SOURCE.md is mandatory" rule still apply to all strategies.

---

## ADR-008: Use `gitignore+fetch` for small datasets

**Date:** 2026-06-09
**Status:** Accepted

### Context

Datasets under ~5 MB can be committed directly to git or fetched on demand.
DVC is overkill for small files with cheap re-fetch procedures.

### Decision

Small datasets use `data_storage: git` (committed directly) or
`data_storage: gitignore+fetch` (raw files gitignored, re-fetch procedure
documented in `raw/SOURCE.md`). For `gitignore+fetch`, SOURCE.md must
include the exact curl/wget command to reproduce the snapshot.

### Consequences

- ✅ No infrastructure for small datasets — no DVC, no B2.
- ✅ SOURCE.md is the reproducibility guarantee.
- ❌ If upstream disappears, the analysis dies with it (for `gitignore+fetch`).
- ❌ Requires manual re-fetch; no automated pull like `dvc pull`.

---

## ADR-007: Theme folders are wrong; tags in CSV are right

**Date:** 2026-06-08
**Status:** Accepted

### Context

We needed to organize datasets that fit multiple themes (a bike-share dataset
is transport, climate, and health). Two options:
1. Theme-based folder hierarchy (`datasets/transport/toronto-bike-share/`)
2. Flat folder per dataset + tags in catalog

### Decision

Option 2. Flat folders, multi-valued tags in the catalog CSV.

### Consequences

- A dataset is in exactly one place on disk — no "where does this go?" tax.
- Tags are N-dimensional and don't require a tree refactor when themes evolve.
- Browsing by theme requires a query (`_scripts/query.py` or DuckDB), not `ls`.
- Contributors must remember to tag, not just place. Mitigated by the PR
  template + CI.

---

## ADR-006: Catalog is a CSV, not a database

**Date:** 2026-06-08
**Status:** Accepted

### Context

A "real" metadata catalog usually lives in SQLite, DuckDB, or YAML-in-JSON.
We considered all three.

### Decision

Plain CSV. One file: `catalog/datasets.csv`.

### Consequences

- ✅ Plain text, diffable in PRs, editable in any text editor or spreadsheet.
- ✅ Git review works natively — no "I forgot to commit the .db file" rot.
- ✅ No migration tooling to maintain.
- ✅ Anyone with a CSV library can read it; no DB driver required.
- ❌ Filtering at scale is slower than indexed DB. Acceptable until ~10k rows.
- ❌ No referential integrity enforced by the database — CI handles it.

If we ever need a queryable cache for analysis work, generate it on demand
with DuckDB. Don't commit binary database files.

---

## ADR-005: Separate repo for the public website

**Date:** 2026-06-08
**Status:** Accepted

### Context

We'll eventually want a public-facing site (Astro/Hugo/whatever) and possibly
a developer webui. Should these live in the data repo?

### Decision

No. Three repos (eventually):
1. `data-insights` — catalog, datasets, scripts (this repo)
2. `data-insights-site` — static site, pulls catalog.csv at build time
3. `data-insights-api` — only if/when build-time isn't enough

### Consequences

- Different cadences (slow data PRs vs fast site deploys) don't conflict.
- Data repo stays boring and dependency-light.
- Site can be a static build → GitHub Pages → free.
- One-way dependency: site reads from data, never writes back.

---

## ADR-004: Raw data is read-only and provenance-mandatory

**Date:** 2026-06-08
**Status:** Accepted

### Context

Analyses rot when the underlying data is unclear: "which version did I
download? When? Was anything filtered out?" Reproducibility dies quietly.

### Decision

Every `datasets/<slug>/raw/` directory must contain a `SOURCE.md` with:
- The exact URL pulled
- Snapshot date
- SHA-256 of file(s)
- Verbatim upstream license
- Any filtering/exclusion notes

Raw files are never edited in place. If a different version is needed,
it's a new folder (`raw/2026-06-08/`, `raw/2026-09-15/`, etc.).

### Consequences

- ✅ Analyses are reviewable and reproducible.
- ✅ Provenance is auditable from `git log datasets/<slug>/raw/SOURCE.md`.
- ❌ More upfront work per dataset. Worth it.

---

## ADR-003: Slug is immutable; rename via display name, not folder

**Date:** 2026-06-08
**Status:** Accepted

### Context

Datasets get renamed upstream all the time. We need a stable identifier
that doesn't break when a Toronto portal rename happens.

### Decision

- The CSV `id` column is the slug (`toronto-bike-share`).
- It must match the folder name under `datasets/`.
- It is **never renamed**. The folder can be moved in spirit (different
  display name in CSV's `name` column) but the slug is the foreign key.

### Consequences

- URLs and citations remain valid forever.
- Scripts and links don't break.
- If the dataset is replaced upstream, we add a new slug and set
  `status: deprecated` + `superseded_by` on the old one.

---

## ADR-002: Public catalog, not a data mirror

**Date:** 2026-06-08
**Status:** Accepted

### Context

It's tempting to make this repo "the place to get Ontario open data" —
mirror everything, query locally, etc.

### Decision

We curate. Each dataset in the catalog is one we (or a contributor)
actually want to analyze. We do not mirror the entire portal.

### Consequences

- ✅ Repo stays small and focused.
- ✅ We have opinions on which datasets matter.
- ❌ It's not a substitute for the upstream portals. That's by design.

---

## ADR-001: Collaborative & public, with a single maintainer

**Date:** 2026-06-08
**Status:** Accepted

### Context

We want this to be public and welcome contributions, but the initial
direction is set by a single maintainer (@jeremyl14).

### Decision

- Public, MIT-licensed, CoC enforced.
- Single maintainer for now; co-maintainers added when load warrants.
- Significant changes (schema, structure) require issue discussion
  before PR.
- Small changes (new dataset, new analysis, fix typo) — just PR.

### Consequences

- Low friction for routine contributions.
- Architectural decisions stay coherent because one person arbitrates.
- Bus factor is 1. Acceptable for now; document in CONCERNS.md.

---

## How to add an ADR

1. Append at the top (newest first).
2. Number sequentially (ADR-009, ADR-010, ...).
3. Use the context / decision / consequences template.
4. Keep it short. If it's longer than a screen, you're writing a design doc,
   not an ADR.
5. State changes are not edits — write a new ADR that supersedes the old
   one. Link to the previous version.