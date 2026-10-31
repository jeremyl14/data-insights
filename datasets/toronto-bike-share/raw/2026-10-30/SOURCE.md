# Source — Toronto Bike Share snapshot (2026 re-snapshot)

- **URL:** https://open.toronto.ca/dataset/bike-share-toronto-ridership-data
- **CKAN API:** https://ckan0.cf.opendata.inter.prod-toronto.ca/api/3/action/package_show?id=bike-share-toronto-ridership-data
- **Dataset UUID:** 7e876c24-177c-4605-9cef-e50dd74c617f
- **Snapshot date:** 2026-10-30
- **Upstream package last refreshed:** 2026-10-27 10:02:35
- **License (verbatim from upstream CKAN `license_id`):**
  > open-government-licence-toronto
  > https://open.toronto.ca/open-data-license/

This folder supersedes `../bike-share-toronto-ridership-2026.csv`
(snapshot 2026-06-10, Jan–Mar only) for 2026 data. The earlier file is
left in place per ADR-004. All other years are unchanged upstream and
remain in `../` (see `../SOURCE.md`).

## Download URL and resource UUID

| Year | Resource UUID | Format | Download URL |
|------|--------------|--------|-------------|
| 2026 | 6124836d-a7ce-4f95-82ea-105fecaecd1a | ZIP | `https://opendata.toronto.ca/toronto.parking.authority/bike-share-toronto-ridership-data/bikeshare-ridership-2026.zip` |

## File hashes (SHA-256)

```
95f9ca97f8859378ba582819785d1274e45a19c67c9bc56ef705178f6d119a75  bikeshare-ridership-2026.zip (upstream archive)
772ef54d0b2b26b70d7c4d1c3955443b52d98ad8908a06e096b3e62b5e9911a7  bike-share-toronto-ridership-2026.csv
```

## Files in this snapshot

| File | Rows | Size | Source format |
|------|------|------|---------------|
| `bike-share-toronto-ridership-2026.csv` | 6,830,174 | 901 MB | ZIP (1 partial-year CSV) |

Rows by month of `Start_Time`:

| Month | Trips |
|-------|-------|
| 2026-01 | 137,336 |
| 2026-02 | 112,910 |
| 2026-03 | 301,827 |
| 2026-04 | 519,723 |
| 2026-05 | 856,875 |
| 2026-06 | 1,173,371 |
| 2026-07 | 1,261,716 |
| 2026-08 | 1,263,910 |
| 2026-09 | 1,202,506 |

Tracked by DVC and stored in Backblaze B2 (`s3://data-insights-raw/snapshots`).
See `docs/DECISIONS.md` ADR-009.

## Notes

- Single consolidated CSV inside the ZIP (`bikeshare-ridership-2026.csv`,
  inner file dated 2026-10-06), extracted byte-for-byte and renamed.
- 2026 is partial-year data (Jan–Sep at time of snapshot).
- Same columns as the 2026-06-10 file: `Trip_Id, Trip_Duration,
  Start_Station_Id, Start_Time, Start_Station_Name, End_Station_Id,
  End_Time, End_Station_Name, Bike_Id, User_Type, Bike_Model`.
- **Jan–Mar rows were revised upstream.** Compared with the 2026-06-10
  snapshot, all 552,073 Jan–Mar trips are present with identical
  `Trip_Id`s, times, station IDs and durations, but 22,831 rows have a
  different `Start_Station_Name` and/or `End_Station_Name` (station
  renames, e.g. `- SMART` suffixes added/removed,
  `Wellington St W / Stafford St` → `Ordnance Park`). Join on station
  ID, not name, when combining the two snapshots.
- The 2024 and 2025 ZIPs were also re-uploaded on 2026-10-27, but their
  inner CSVs predate the 2026-06-10 snapshot (dated 2026-03-26 and
  ≤ 2026-03-12), so they were not re-snapshotted.
