# TTC Bus Delay Data — Source

## Snapshot

- **Date:** 2026-06-10
- **SHA-256 (ttc-bus-delay-data-since-2025.csv):** `c4952d94e9745b9d562e6d30d0051787072aa014689b94d4309f444dd6203125`
- **SHA-256 (ttc-bus-delay-codes.csv):** `17a32cce4dadf783466603c49988c3eeaf15c9fb77f4bd7654d25bf630da0484`

## Upstream

- **Portal:** https://open.toronto.ca/dataset/ttc-bus-delay-data/
- **CKAN UUID:** `e271cdae-8788-4980-96ce-6a5c95bc6618`
- **API:** https://ckan0.cf.opendata.inter.prod-toronto.ca/api/3/action/package_show?id=ttc-bus-delay-data

## Files

| File | Description | Rows | Size |
|---|---|---|---|
| `ttc-bus-delay-data-since-2025.csv` | Per-incident bus delay data from 2025 onward | ~84,000 | 7.5 MB |
| `ttc-bus-delay-codes.csv` | Delay code descriptions (46 codes) | 46 | 1.3 KB |

## Re-fetch

```bash
cd datasets/ttc-bus-delay/raw
curl -L "https://ckan0.cf.opendata.inter.prod-toronto.ca/dataset/e271cdae-8788-4980-96ce-6a5c95bc6618/resource/b5725365-9252-4bfe-b6f4-cda7ddf74341/download/ttc-bus-delay-data-since-2025.csv" -o ttc-bus-delay-data-since-2025.csv
curl -L "https://ckan0.cf.opendata.inter.prod-toronto.ca/dataset/e271cdae-8788-4980-96ce-6a5c95bc6618/resource/874ae66c-9f6f-443f-91e0-1d37d416e0d8/download/code-descriptions.csv" -o ttc-bus-delay-codes.csv
sha256sum ttc-bus-delay-data-since-2025.csv ttc-bus-delay-codes.csv
dvc add ttc-bus-delay-data-since-2025.csv ttc-bus-delay-codes.csv
dvc push
```

## Storage

- `data_storage: dvc` (in catalog)
- DVC pointers: `ttc-bus-delay-data-since-2025.csv.dvc`, `ttc-bus-delay-codes.csv.dvc`
- B2 location: `s3://data-insights-raw/snapshots/files/md5/...`

## License

Open Government Licence — Toronto (OGL-Toronto)

<https://www.toronto.ca/city-government/data-research-maps/open-data/open-data-licence/>

Permission is hereby granted, free of charge, to any person obtaining a copy of this data and associated documentation files, to use the Data without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Data, subject to the following conditions:

1. The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Data.
2. The Data is provided "as is", without warranty of any kind.