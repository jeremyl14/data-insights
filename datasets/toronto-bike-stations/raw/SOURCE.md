# Toronto Bike Share Stations (snapshot demo)

This dataset demonstrates the **DVC + B2** snapshot workflow
described in `docs/DECISIONS.md` ADR-009. The data is small
enough to commit (~500 bytes) but the snapshot flow is identical
to the larger Bike Share Ridership dataset.

## Source

Static station reference data, embedded in the Bike Share Toronto
GTFS feed. Public via Open Data Toronto. Snapshot date: 2026-06-09.

## SHA-256

- `stations.csv`: `fb6303ed12469622a881c4b0e3d2715a9fdbbd73ace48835a0454cace57286a1`

## Re-fetch

```bash
curl -L -o raw/stations.csv \
  "https://bikesharetoronto.com/stations.csv"
dvc add raw/stations.csv
dvc push
```

## Storage

- `data_storage: dvc` (in the catalog)
- Real file committed to git
- DVC pointer: `raw/stations.csv.dvc`
- B2 location: `s3://data-insights-raw/snapshots/files/md5/...`
