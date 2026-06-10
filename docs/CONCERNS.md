# Open concerns, known issues, and TODOs

This is the **honest** list. Things we know are weak, that we plan to
fix, or that are actively at risk. Newest first.

---

## Active concerns

### ⚠️ Bus factor = 1
- **What:** @jeremyl14 is the only maintainer with full context.
- **Risk:** If they go quiet, the repo stalls. Architectural decisions
  are concentrated.
- **Mitigation:** ADRs (in DECISIONS.md) document *why*, so a successor
  doesn't have to re-litigate from scratch.
- **Status:** Acceptable for now. Reassess at 5+ active contributors.

### ⚠️ No automated URL re-validation yet
- **What:** The `validate.yml` workflow checks URLs on PR. We don't have
  a scheduled re-check of the full catalog.
- **Risk:** Upstream URLs die silently. We find out when someone tries
  to use the dataset.
- **Mitigation:** `.github/workflows/revalidate-urls.yml` exists but is
  not yet on a scheduled cron trigger.
- **Status:** Open. Add scheduled trigger when we have 20+ datasets.

### ⚠️ "Source of truth" can drift between CSV and `raw/` directories
- **What:** Someone could update `raw/SOURCE.md` without updating
  `last_verified` in the catalog, or vice versa.
- **Risk:** Validation gaps. Hard to detect retroactively.
- **Mitigation:** `validate.yml` cross-checks folder + CSV row.
  Doesn't yet cross-check `SOURCE.md` dates against `last_verified`.
- **Status:** Open. Add a script that diffs them.

### ⚠️ License vocabulary is incomplete
- **What:** We have `OGL-Ontario`, `ODC-BY`, `CC-BY`, `CC-BY-SA`, `CC0`.
  StatCan uses their own license. Some datasets are "all rights reserved"
  with explicit redistribution permission.
- **Risk:** Contributors have to use `custom:` for legitimate cases,
  losing consistency.
- **Mitigation:** Add specific tokens as we encounter them.
- **Status:** Will-grow-organically.

### ✅ Workflows moved from `workflows-tmp/` to `workflows/`
- **What:** The GitHub Actions workflow files are now in `.github/workflows/` where CI can pick them up.
- **Status:** Resolved 2026-06-10.

### ⚠️ Schema migrations are undefined
- **What:** ADR-006 says CSV is the source of truth. We don't have a
  documented migration path for adding a new column.
- **Risk:** Adding a column requires touching every row, or accepting
  empty values. Both are real choices with real consequences.
- **Mitigation:** Document the migration pattern in
  [docs/migrations/](migrations/) (TBD) before the first migration.
- **Status:** Open. Defer until the first real schema change.

### ⚠️ Tag sprawl
- **What:** Tags are free-form. We will inevitably get `transport`,
  `transit`, `public-transit`, `public_transit` from different
  contributors.
- **Risk:** Filtering by tag misses synonyms.
- **Mitigation:** Canonical tag list in `docs/SCHEMA.md` + warning in
  `_scripts/validate.py` for unknown tags. New tags require updating
  both the list and the validator.
- **Status:** Mitigated. Watch for new tags in PRs.

### ⚠️ CSV will get painful at scale
- **What:** `catalog/datasets.csv` is diffable and reviewable at 5–20
  rows. At 50+ rows, manual CSV editing becomes error-prone (misaligned
  columns, unquoted commas in notes/tags).
- **Risk:** PRs touching the catalog will be hard to review. Misaligned
  rows will pass `csv.DictReader` but produce wrong data.
- **Mitigation:** CSV lint is now in the validator (`--csv-lint`).
  A migration path to per-dataset YAML exists in
  `_scripts/csv_to_yaml.py`. The CSV would become a generated artifact;
  YAML front-matter in each dataset folder would be the source of truth.
- **Status:** Tooling ready. Migration deferred until CSV editing
  friction is real (~20+ datasets).

### ⚠️ `dvc push` 403 with no diagnostic
- **What:** DVC's S3 backend returns `403 Forbidden` for several
  unrelated causes: wrong S3 endpoint URL (most common), wrong key,
  wrong bucket, or key without the right capabilities.
- **Why this is hard:** DVC does not distinguish between them. The
  error is the same string in all four cases.
- **Diagnostic order when 403 happens:**
  1. **Check the S3 endpoint URL.** It is **bucket-region-specific**;
     visible in the B2 web UI under the bucket's "Endpoint" tab. The
     format is `https://s3.<region>.backblazeb2.com` (e.g.
     `s3.ca-east-006.backblazeb2.com` for Canada East). Wrong region
     = silent 403. This was the cause of a 2-hour debug session on
     2026-06-09; we tried `us-west-004` before finding the right
     region in the UI.
  2. **Check the credentials.** `dvc` reads `AWS_ACCESS_KEY_ID` and
     `AWS_SECRET_ACCESS_KEY` from the env. The key must have
     `listFiles` + `readFiles` + `writeFiles` for this bucket.
  3. **Check the bucket name.** Use the B2 web UI to confirm the
     bucket exists and that the key is scoped to it.
  4. **Check key capabilities.** A bucket-scoped key with only
     `readFiles` cannot write. Re-create the key in the B2 UI
     with the needed capabilities.
- **Status:** Documented. Will recur; treat as a runbook.

---

## TODOs

Things we'd like to add but haven't yet. No deadlines.

- [x] First real analysis in `datasets/toronto-bike-share/analysis/`
      — resolved 2026-06-10: 10 analyses now exist.
- [x] Decide on first analysis theme — resolved: transport (bike-share) + environment (weather).
- [ ] Decide on website repo (`data-insights-site`) — defer until
      ≥20 datasets.


## Resolved concerns

### ✅ Large-data storage strategy (DVC + B2) — implemented 2026-06-09
Originally parked per ADR-008 (use `gitignore+fetch` for now).
Implemented the same day after the maintainer confirmed
infrastructure availability (B2 already in use for restic backups).

- `.dvc/` and DVC pointer files are committed; the data lives in B2.
- `_scripts/dvc_onboard.sh` — one-time setup, idempotent, reads
  credentials from `/etc/dvc-env`.
- `_scripts/snapshot.py` — per-dataset cadence from the catalog's
  `refresh_frequency` column. Sidecar state file is gitignored.
- `.github/workflows/dvc-snapshot-status.yml` — daily dry-run report, no creds.
- `_scripts/dvc.env.example` — template for `/etc/dvc-env`.
- First dataset migrated: `toronto-bike-stations` →
  `data_storage: dvc` in the catalog. Real DVC pointer file in
  `datasets/toronto-bike-stations/raw/stations.csv.dvc` (md5:
  37d1ca56603d5f73886b7299f00cd5a9, 475 bytes).
- See ADR-009 (DECISIONS.md) for the formal decision.

**End-to-end tested 2026-06-09:** `dvc add` + `dvc push` succeeds
against `s3.ca-east-006.backblazeb2.com`; `dvc pull` restores the
file; SHA-256 of the restored file matches the original. The
S3 endpoint is **bucket-region-specific**; using the wrong region
(e.g. `us-west-004` for a Canada East bucket) gives a silent
403 from DVC with no diagnostic. Documented in ADR-009.

### ✅ `query.py` and CKAN harvester — implemented 2026-06-08
The README referenced these; both now exist. `_scripts/query.py` is
~140 lines of stdlib Python. `_scripts/harvest_ckan.py` is a ~240-line
CKAN harvester that works against both data.ontario.ca and
open.toronto.ca (both are CKAN instances).

### ✅ DATASET_README / ANALYSIS_README templates — implemented
Both templates now live in `docs/templates/` and are referenced by
the analysis submission checklist in `CONTRIBUTING.md`.

### ✅ AGENTS.md + Reviewer role — implemented 2026-06-09
The repo now has a documented agent contract (`AGENTS.md`) with three
roles (Cataloger, Analyst, Reviewer). The Reviewer has a full
operational prompt in `agents/reviewer.md`. The contract is deliberately
stricter than the average repo because analyses published under a
shared name decay the whole repo's reputation if wrong.

### ✅ Repo name decided — `data-insights` (was `open-data-analysis`)
Originally drafted as `open-data-analysis`; renamed after maintainer
feedback that the name should reflect that the repo is data + analysis
+ visualization, not just data.

---

## How to add a concern

Don't be shy. Open a PR adding to "Active concerns" with:
- What (one sentence)
- Risk (one sentence)
- Mitigation (if known)
- Status (Open / Mitigated / Resolved)

If you fix something, move it to "Resolved concerns" with a date.
