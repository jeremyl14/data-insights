# Toronto Bike Share Stations (snapshot demo)

This dataset demonstrates the **DVC + B2** snapshot workflow
described in `docs/DECISIONS.md` ADR-009. The data is small
enough to commit (~500 bytes) but the snapshot flow is identical
to the larger Bike Share Ridership dataset.

## Source

Static station reference data, embedded in the Bike Share Toronto
GTFS feed. Public via Open Data Toronto. Snapshot date: —.

## Re-fetch

```bash
# To be populated on first snapshot.
dvc add raw/stations.csv
dvc push
```

## Storage

- `data_storage: dvc` (in the catalog)
- DVC pointer: `raw/stations.csv.dvc`
- B2 location: `s3://data-insights-raw/snapshots/files/md5/...`