# toronto-bike-stations

Toronto Bike Share Stations (snapshot demo).

This is a **DVC + B2** snapshot demo dataset. The data is small
enough to commit (~500 bytes) but the snapshot flow is identical
to the larger Bike Share Ridership dataset (`toronto-bike-share`).

The raw data is committed to git (along with the `.dvc` pointer
file). B2 holds an identical copy under
`s3://data-insights-raw/snapshots/files/md5/...`. New clones can
restore it with `dvc pull` if the local copy is missing or
corrupted.

## Files

- `raw/stations.csv` — 10-row CSV of station reference data
- `raw/stations.csv.dvc` — DVC pointer (md5 + size)
- `raw/SOURCE.md` — provenance and re-fetch procedure
- `raw/.gitignore` — see notes

## Storage strategy

- `data_storage: dvc` in the catalog
- Both the raw file AND the DVC pointer are in git
- In a real-world larger dataset, only the `.dvc` pointer would be
  in git; the raw file would be excluded by `*.csv` in the local
  `.gitignore`, and `dvc pull` would fetch it from B2

## Re-fetch

```bash
curl -L -o raw/stations.csv \
  "https://example.com/bike-share-stations.csv"
dvc add raw/stations.csv
dvc push
```

## Provenance

Snapshot taken 2026-06-09. Source: Open Data Toronto (ODC-BY).
For details see `raw/SOURCE.md`.
