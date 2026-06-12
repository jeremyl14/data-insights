# Toronto Permanent Bicycle Counters — Source

## Snapshot

- **Date:** 2026-06-10
- **SHA-256 (locations):** `e2da039ff4b5a8a4b09a7e85189d0929b25ec630fd9330d4559b8e13511b1f2f`
- **SHA-256 (daily):** `c0d91a23cbf5ecd15820727fb1a2421a95dc51da4b0eb8ace06a7c10899e582d`
- **SHA-256 (15min 1994-2024):** `365bc4be8efa98c67e135e563da885202bebd2b41fbbee53361c8c29d500a9ad`
- **SHA-256 (15min 2024-2025):** `bc2d6e5ba5fb43267570ab6d092c8e0488136356b12113c7e5d552860a1a6477`
- **SHA-256 (15min 2025-2026):** `c62ceabca7d6413f15a6e06aa311e5e850df9cc81d8d168f9517830a1583bd54`

## Upstream

- **Portal:** https://open.toronto.ca/dataset/permanent-bicycle-counters/
- **CKAN UUID:** `ff7e7369-cbba-4545-9e26-e5a5ef6a123c`
- **API:** https://ckan0.cf.opendata.inter.prod-toronto.ca/api/3/action/package_show?id=ff7e7369-cbba-4545-9e26-e5a5ef6a123c

## Files

| File | Description | Rows | Size | Storage |
|---|---|---|---|---|
| `cycling-permanent-counts-locations.csv` | Counter locations + metadata | 43 | 8 KB | git |
| `cycling-permanent-counts-daily.csv` | Daily bike counts per counter | ~52,900 | 5.2 MB | git |
| `cycling-permanent-counts-15min-1994-2024.csv` | 15-min counts, historical | ~3.3M | 83 MB | DVC |
| `cycling-permanent-counts-15min-2024-2025.csv` | 15-min counts, 2024–2025 | ~1.1M | 29 MB | DVC |
| `cycling-permanent-counts-15min-2025-2026.csv` | 15-min counts, current | ~1.2M | 30 MB | DVC |

## Re-fetch

```bash
cd datasets/toronto-bike-counters/raw
curl -L -o cycling-permanent-counts-locations.csv \
  "https://ckan0.cf.opendata.inter.prod-toronto.ca/dataset/ff7e7369-cbba-4545-9e26-e5a5ef6a123c/resource/217a6e7f-c980-46ab-ba06-6d10b5499194/download/cycling_permanent_counts_locations.csv"
curl -L -o cycling-permanent-counts-daily.csv \
  "https://ckan0.cf.opendata.inter.prod-toronto.ca/datastore/dump/b6fdab07-bf2f-4c30-8b68-d4cde7674941"
curl -L -o cycling-permanent-counts-15min-2025-2026.csv \
  "https://ckan0.cf.opendata.inter.prod-toronto.ca/dataset/ff7e7369-cbba-4545-9e26-e5a5ef6a123c/resource/473fd887-9741-49ca-9816-bbe589ecf3a6/download/cycling_permanent_counts_15min_2025_2026.csv"
curl -L -o cycling-permanent-counts-15min-2024-2025.csv \
  "https://ckan0.cf.opendata.inter.prod-toronto.ca/dataset/ff7e7369-cbba-4545-9e26-e5a5ef6a123c/resource/49675bd6-a17c-4de7-af66-c0e8338d7d13/download/cycling_permanent_counts_15min_2024_2025.csv"
curl -L -o cycling-permanent-counts-15min-1994-2024.csv \
  "https://ckan0.cf.opendata.inter.prod-toronto.ca/dataset/ff7e7369-cbba-4545-9e26-e5a5ef6a123c/resource/1da069cb-ee75-4698-96ec-fdf70ff3e964/download/cycling_permanent_counts_15min_1994_2024.csv"
dvc add cycling-permanent-counts-15min-*.csv
dvc push
sha256sum *.csv
```

## License

Open Data Commons Attribution License (ODC-BY)

https://open.toronto.ca/open-data-licence/