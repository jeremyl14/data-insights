# Source — Toronto Bike Share snapshot (2022 re-snapshot)

- **URL:** https://open.toronto.ca/dataset/bike-share-toronto-ridership-data
- **CKAN API:** https://ckan0.cf.opendata.inter.prod-toronto.ca/api/3/action/package_show?id=bike-share-toronto-ridership-data
- **Dataset UUID:** 7e876c24-177c-4605-9cef-e50dd74c617f
- **Snapshot date:** 2026-10-31
- **License (verbatim from upstream CKAN `license_id`):**
  > open-government-licence-toronto
  > https://open.toronto.ca/open-data-license/

This folder supersedes `../bike-share-toronto-ridership-2022.csv`
(snapshot 2026-06-10) for 2022 data. The earlier file is left in place
per ADR-004.

## Why

The 2026-06-10 file is missing **November 2022**. Upstream, November is
not a CSV like the other months but a ZIP nested inside the year's ZIP
(`bikeshare-ridership-2022/Bike share ridership 2022-11.zip`, inner file
dated 2022-12-16). The earlier snapshot concatenated only the `.csv`
members, so November was dropped; its notes recorded this as "January
missing", which was wrong. The data was never missing upstream.

## Download URL and resource UUID

| Year | Resource UUID | Format | Download URL |
|------|--------------|--------|-------------|
| 2022 | 34c99885-9e7a-4fa2-a23f-2068ec92b06d | ZIP | `https://opendata.toronto.ca/toronto.parking.authority/bike-share-toronto-ridership-data/bikeshare-ridership-2022.zip` |

Upstream `last_modified` for this resource: 2023-01-18T17:36:31 (unchanged
since the earlier snapshot).

## File hashes (SHA-256)

```
4114b32242f5949138bade1df16acf29da3bd210c46e8fb642ff81f32a498b5f  bikeshare-ridership-2022.zip (upstream archive)
e73ab2961d2f4434c3940cb04acd6aaef01f2ebef827760fcc4b90f34df2fb65  bike-share-toronto-ridership-2022.csv
```

## Files in this snapshot

| File | Rows | Size | Source format |
|------|------|------|---------------|
| `bike-share-toronto-ridership-2022.csv` | 4,620,469 | 573 MB | ZIP (11 monthly CSVs + November as a nested ZIP) |

Rows by month: Jan 56,765 · Feb 67,010 · Mar 151,938 · Apr 245,920 ·
May 504,926 · Jun 605,645 · Jul 680,308 · Aug 705,150 · Sep 602,817 ·
Oct 499,751 · **Nov 320,229** · Dec 180,010.

Tracked by DVC and stored in Backblaze B2 (`s3://data-insights-raw/snapshots`).
See `docs/DECISIONS.md` ADR-009.

## Build method

1. Take the 12 monthly members of the upstream ZIP in month order,
   unpacking the nested November ZIP (it holds one CSV with the same
   10 columns as the other months).
2. Convert CRLF line endings to LF.
3. Keep the first month's header row and drop the others' (all headers
   are identical).

Verified: applying the same method **without** November reproduces the
2026-06-10 file byte for byte (SHA-256 `923cf105…8d10`), so the two
snapshots differ only by the added November rows.
