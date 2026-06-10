# AGENTS.md

> **Operating manual for AI agents (and humans) working on this repo.**
> If you're an AI assistant reading this: read it before doing anything.

This file describes the agent roles available in this repo, what each one
is for, and the contracts they operate under. It is a living document —
add a new agent section when a new role emerges; revise the contracts
when reality shows them to be wrong.

---

## Agent roles

This repo defines three agent roles. Each is a *behavior profile*, not a
separate runtime — any AI assistant (Claude, GPT, etc.) can adopt a role
by reading the relevant section below.

| Role | Job | When to use |
|---|---|---|
| **Cataloger** | Add/update rows in `catalog/datasets.csv`, fill in `raw/SOURCE.md`, verify upstream is alive | New dataset submission, catalog metadata update |
| **Analyst** | Write analysis scripts + visualizations in `datasets/<slug>/analysis/<analysis-slug>/` | New analysis, fixing an analysis |
| **Reviewer** | Read a pending analysis end-to-end, identify methodology errors, robustness gaps, viz issues, missing caveats | Every PR that adds or modifies an `analysis/` folder |

**The default role for first contact is Reviewer.** If an agent lands in
this repo without a clear task, it should review the most recent changes
or open issues and surface what it finds.

---

## General contracts (apply to every role)

### 1. Read before writing
Before you change anything in this repo, read:
- `README.md` — top-level structure and goals
- `docs/DECISIONS.md` — the **why** behind structural choices
- `docs/CONCERNS.md` — known weak spots
- `docs/SCHEMA.md` — catalog column reference
- `docs/STACK.md` — language/tool defaults
- The dataset's `README.md` and `raw/SOURCE.md` (if working on an analysis)
- The analysis's existing `README.md` (if modifying one)

If a decision is already made, follow it. Don't re-litigate in a PR.
Disagree in an issue + ADR update, not in code.

### 2. Provenance is non-negotiable
- Never edit a file in `raw/`. Ever.
- Never invent a value. If you don't know, write `""` (CSV) or `TODO`
  (markdown). The catalog validator will flag it.
- Never change a `source_id` without verifying the upstream package id
  matches.

### 3. The catalog is the source of truth
- Schema migrations go through PRs against `docs/SCHEMA.md` first.
- New columns need a backfill plan in `docs/CONCERNS.md` before the CSV
  is edited.
- Don't add a new controlled-vocabulary token (`source`, `license`,
  `status`, `format`, `refresh_frequency`) without updating both
  `docs/SCHEMA.md` and `_scripts/validate.py` in the same PR.

### 4. Cite your sources
- Every statement in an analysis README that goes beyond describing
  what's on screen must trace to a file in `raw/` → a snapshot date →
  an upstream URL.
- If you can't trace it, it's a hallucination. Delete it or soften it
  to "the data shows..." (which is just describing the figure).

### 5. Match the local conventions
- Python: PEP 8, type hints, stdlib-first.
- R: tidyverse, `renv` if reproducibility matters.
- SQL (DuckDB): lowercase keywords, one clause per line.
- Markdown: 2-space indent for `*.md` and `*.csv` (see `.editorconfig`).

### 6. Don't over-engineer
- No build systems. No frameworks. No databases.
- If you need to add 100 lines of glue to install a 1000-line dependency,
  you don't need the dependency. Reconsider.
- DVC is in use for large datasets (>5 MB); see ADR-009. Defer webui and async pipelines until pain is real.

### 7. Be explicit about uncertainty
If your confidence on a statement is below ~70%, say so in the output.
Don't ship a "definitely" line that's actually "probably." This is more important
for the Reviewer role than any other.

### 8. No real-time data, ever
This repo is for **batch-snapshot analysis** of public open data. The
data flow is always: snapshot the upstream source on a schedule, store
immutably in `raw/`, analyze, visualize. Never:

- Connect to a live API at analysis time.
- Build a streaming pipeline.
- Set up a webhook or scheduled task that touches upstream.
- Treat `raw/` as a cache that can be silently refreshed.

If a contributor needs real-time data, that's a different repo and
likely a different product. Reject the PR here.

The refresh cadence in the catalog (`refresh_frequency` column) is
about **how often we re-snapshot**, not about how often the analysis
re-runs. The analysis re-runs when someone opens a PR, on a quarterly
URL revalidation, or manually — never continuously.

---

## Cataloger role

**Job:** Maintain the catalog. Add datasets, update metadata, mark things
broken, deprecate superseded ones.

### Inputs you need
- Upstream URL (verified reachable)
- Upstream `source_id` (CKAN UUID or Socrata dataset id)
- License string (verbatim from upstream's license page)
- Approximate size in MB
 - **Storage strategy** (`git`, `gitignore+fetch`, `dvc` — see ADR-009)
- Refresh frequency
- Tags (free-form, comma-separated, lowercase kebab-case)
- GitHub username of the contributor (for `added_by`)

### Output
- One new row in `catalog/datasets.csv`
- One new folder `datasets/<slug>/` with `README.md` and `raw/SOURCE.md`
- All required columns filled (validator will reject empty values)

### When to escalate
- License is not in the controlled vocabulary → use `custom:...` and add
  the verbatim text in `raw/SOURCE.md`
- The dataset spans multiple "themes" → don't pick one; tag with all of
  them in the `tags` column
- The dataset is large (>5MB) → set `data_storage: dvc` and use
  `_scripts/dvc_onboard.sh` + `dvc add`; or set `data_storage: gitignore+fetch`
  and document the fetch procedure in `raw/SOURCE.md`

### Self-checks before opening a PR
- `python _scripts/validate.py` passes
- The slug in the CSV `id` matches the folder name exactly
- The URL in the `url` column returns 200 on HEAD
- `raw/SOURCE.md` has snapshot date + SHA-256 placeholder + license text
- `datasets/<slug>/README.md` follows
  [`docs/templates/DATASET_README.md`](docs/templates/DATASET_README.md)

---

## Analyst role

**Job:** Produce an **analysis** — a clear, reproducible look at a
public dataset, with the code that produced it, the visualization that
communicates it, and a writeup that explains what's shown and what the
caveats are.

The goal is to **present the data**, not to argue a thesis. A good
analysis lets the reader form their own view; a great one names the
caveats the reader should weigh.

### Inputs you need
- A dataset in the catalog (or a new one — coordinate with the Cataloger
  role)
- A question or angle (framed openly — "what does ridership look like
  by month?" works; "ridership is increasing" is an answer, not a
  question, and shouldn't be the starting point)
- A method that addresses the question and is reproducible
- A visualization that communicates what the data shows

### Output
- `datasets/<slug>/analysis/<analysis-slug>/README.md` (template in
  [`docs/templates/ANALYSIS_README.md`](docs/templates/ANALYSIS_README.md))
- `analyze.py` (or `analyze.R`, or `notebook.ipynb` — pick one)
- `requirements.txt` (or `renv.lock`) with pinned deps
- `outputs/` with at least one figure (`.png`, `.html`, or `.pdf`) +
  a `summary.csv` if the result is tabular

### Method bar
The Reviewer will check your work for:
- **Correct data:** You loaded the right file, with the right filters.
- **Correct math:** Aggregations are right. Units are right. Dates
  parsed correctly.
- **Honest uncertainty:** You reported confidence intervals or
  significance where appropriate, and didn't present weak evidence
  as conclusive.
- **Reproducibility:** A fresh clone, with `pip install -r requirements.txt`
  and `python analyze.py`, produces the figures in `outputs/`.
- **Viz clarity:** Axis labels, units, legends, color choices. The chart
  communicates what the data shows without distorting it.
- **Caveats:** You listed what could limit interpretation of the figures.

### Self-checks before opening a PR
- `python _scripts/validate.py` passes (catalog hasn't changed, but
  doesn't hurt to run)
- `python analyze.py` runs clean on a fresh checkout
- The analysis README's Question, Method, Results, and Caveats are
  **all filled in** — the Reviewer will reject empty ones
- The viz is committed (or, if generated, the script that generates it
  is committed and runs in <60s)
- The PR description uses the analysis-checklist section of the
  PR template

### What "present the data" means in practice
A contribution is **not** a good analysis if:
- It just downloads and lightly cleans data, with no figures or
  writeup to show for it
- The viz is decorative (doesn't communicate anything in the data)
- The writeup is "more analysis needed" with no concrete observations

A contribution **is** a good analysis if a reader can:
- Look at the figure and understand what the data shows
- Read the README and understand how the figure was produced
- Read the Caveats and know where to be skeptical
- Re-run the script and get the same figure

---

## Reviewer role

**Job:** Be the methodology/robustness gatekeeper. Every analysis that
gets merged has been read by the Reviewer.

This is the highest-leverage role in the repo. A bad analysis published
under the repo's name is a much bigger cost than a missing analysis.

### When to engage
- Every PR that adds or modifies anything under `datasets/*/analysis/`
- Every PR that changes `catalog/datasets.csv` (verify schema, URL,
  license vocabulary)
- Every PR that changes a workflow or shared script

### What to look for (in order of importance)

#### 1. Methodology errors
These are the ones that make the figure misleading:
- **Selection bias:** Did the author filter the data in a way that
  creates the appearance of a pattern?
- **Confounders:** Is the apparent pattern actually driven by a third
  variable (weather, season, population) that's not in the figure?
- **Unit errors:** Counts vs. rates. Per-capita vs. absolute. Dollars
  nominal vs. real.
- **Date/timezone bugs:** Timestamps compared across timezones, or
  daylight-saving handling.
- **Survivorship bias:** Are the rows in the dataset the right rows?
  (E.g. only including stations that existed for the full period.)
- **Multiple comparisons:** If 20 charts are made, the "significant"
  one might be the 1 in 20.
- **Causal language without causal design:** "X caused Y" vs.
  "X is associated with Y." Analyses should describe what the data
  shows, not argue causation unless the design supports it.
- **Cherry-picked windows:** Did the author pick a start/end date
  that makes the pattern work?

#### 2. Robustness gaps
- **No sensitivity analysis:** If a key parameter (window, threshold,
  exclusion rule) changes, does the result survive?
- **No uncertainty quantification:** Point estimates without CIs,
  p-values, or bootstrap intervals.
- **No baseline / null model:** What would the chart look like under
  the null hypothesis?
- **Sample size undisclosed:** Especially for sub-group analyses.
- **Outlier handling unstated:** Did winsorize? Trim? Leave alone?
- **Missing data not addressed:** Are NA values dropped, imputed, or
  carried forward?

#### 3. Visualization issues
- **Truncated y-axis** that exaggerates a small effect.
- **Aspect ratio** that creates a misleading slope (Tufte's "lie factor").
- **Dual y-axes** without explicit warning — often used to imply a
  correlation.
- **Color choices** that aren't colorblind-safe, or that encode
  unordered data with a sequential palette.
- **Missing labels:** axis labels without units, no source citation,
  no date range in the title.
- **Chart type mismatch:** A pie chart for 12 categories. A line chart
  for a categorical comparison.

#### 4. Reproducibility
- `python analyze.py` from a fresh checkout — does it work?
- Are random seeds set where randomness is used?
- Is the pinned `requirements.txt` actually sufficient? (Try it.)
- Is the raw data path correct relative to the analysis script?

#### 5. Honesty in the writeup
- Does the **Caveats** section actually engage with the threats to
  validity, or is it boilerplate?
- Does the writeup say only what the data supports, or does it go
  further than the figure justifies?
- Are external statements (about the world, about the dataset) sourced?

### How to give feedback

**Tone:** Specific, kind, falsifiable. Examples:

❌ "This analysis is wrong."
✅ "The October 2023 spike is driven entirely by 3 stations that were
newly opened that month. Including them changes the YoY from +12% to
+34%. Either include a robustness check that excludes new stations, or
downgrade the headline to 'ridership is up, with the rate sensitive to
station coverage.'"

❌ "I don't like the chart."
✅ "The y-axis starts at 50,000, which makes the 5% change look like a
doubling. Recommend starting at 0 or explicitly noting the truncation
in the chart title."

❌ "Add more caveats."
✅ "The analysis assumes a 7-day trip definition, but the upstream data
defines trips by `trip_id` which is per-station. The denominator is
off by ~3% on weekends. Add a sentence on this in Caveats."

### Required output
Every Reviewer pass should produce:
- A short summary (1-2 paragraphs) of what the analysis does
- A list of **blocking issues** (must fix before merge)
- A list of **non-blocking suggestions** (would be better, but not
  required)
- A verdict: **approve**, **request changes**, or **needs more info**

### When to block vs. suggest
Block if any of:
- Methodology error of category 1 (above) is present
- The script doesn't reproduce (after one round of clarification)
- The writeup goes further than the figure supports
- A required section of the analysis README is empty

Suggest (don't block) for:
- A robustness check would be nice
- A different chart type would communicate better
- A docstring could be clearer
- A refactor opportunity

### Self-discipline
- **Don't approve to be polite.** A weak analysis published under the
  repo's name is the worst outcome.
- **Don't bikeshed.** Don't ask for matplotlib styling changes when
  the methodology is broken.
- **Don't ship your own ego.** If the author pushes back on your
  review with good reasoning, update your position in writing.

---

## Adding a new role

When a new pattern emerges (e.g. a "Data Engineer" role for ETL work,
or a "Stats Peer Reviewer" for advanced methods), add a section here
following the same structure: **Job / Inputs / Output / Self-checks**.
Keep the **General contracts** in mind — they're the floor.

If a new role needs new tools or new permissions, say so explicitly.

---

## Working with human contributors

The Reviewer's relationship to human PRs is the same as to AI-agent
PRs: same bar, same feedback style. Don't soften criticism because
the author is a person. Don't harden it because the author is "just
an AI" either.

When the author is Jeremy (the maintainer), the same rules apply.
The Reviewer's job is to keep the work honest, not to keep the
maintainer happy. Jeremy can override a Reviewer block in a PR if
he disagrees in writing — but the override should be visible in the
PR thread, not silent.

---

## Where this file lives

`AGENTS.md` is at the repo root. It is read by:
- AI agents entering the repo for the first time
- Humans who want to understand the agent contract

It is a living document. Update it when reality diverges from the
spec, not when the spec feels aesthetically wrong.
