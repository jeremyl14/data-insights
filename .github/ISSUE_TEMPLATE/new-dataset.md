---
name: New dataset
about: Add a new dataset to the catalog
title: "[dataset] "
labels: dataset
---

## Dataset info

- **Name:**
- **Source portal:** data.ontario.ca / open.toronto.ca / other
- **Upstream URL:**
- **License:**
- **Proposed slug:** `kebab-case-name`

## What kind of analysis is planned?

<!-- One or two sentences. We curate, so a dataset without a clear use case probably doesn't belong. -->

## Will you commit the raw data?

- [ ] Yes — small (<5MB), commit to repo
- [ ] Yes — large, will use DVC or external storage (describe in PR)
- [ ] No — only metadata + analysis; raw data is fetched at runtime

## Checklist

- [ ] I have verified the upstream URL is currently accessible
- [ ] I have read CONTRIBUTING.md
- [ ] I will fill in `raw/SOURCE.md` with snapshot date + hash + license
- [ ] I will add a row to `catalog/datasets.csv`
