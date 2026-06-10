## What does this PR do?

<!-- One or two sentences. -->

## Type of change

- [ ] New dataset
- [ ] New analysis
- [ ] Catalog metadata update (URL fix, license correction, deprecation)
- [ ] Documentation (README, ADR, etc.)
- [ ] Bug fix
- [ ] Other (describe)

## Dataset submission checklist (if adding/changing a dataset)

- [ ] Added/updated row in `catalog/datasets.csv`
- [ ] `id` (slug) matches the folder name and is in kebab-case
- [ ] `source_id` is correct (verified against upstream)
- [ ] `url` returns 200 (HEAD-checked)
- [ ] `license` is from the approved vocabulary (or `custom:...` with notes)
- [ ] `raw/SOURCE.md` is filled in with date + SHA-256 + license text
- [ ] README.md follows `docs/templates/DATASET_README.md`

## Analysis submission checklist (if adding an analysis)

- [ ] README.md follows `docs/templates/ANALYSIS_README.md`
- [ ] Question, Method, How to reproduce, Results, Caveats all filled in
- [ ] Pinned dependencies in `requirements.txt` (use `==X.Y.*` pins, not bare `>=` ranges)
- [ ] Outputs cleared from committed notebooks (or in `outputs/` if they're the result)

## Verification

- [ ] Local validation passes: `python _scripts/validate.py`
- [ ] Catalog query works: `python _scripts/query.py --tag <your-tag>`
- [ ] If a script was added, it's runnable from a fresh clone (deps install cleanly)

## Linked issues

<!-- e.g. "Closes #12" or "Addresses open concern in docs/CONCERNS.md" -->

## Notes for reviewer

<!-- Anything that doesn't fit the checklist. Surprises, scope cuts, follow-up TODOs. -->
