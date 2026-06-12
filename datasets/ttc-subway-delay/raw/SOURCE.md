# Source: TTC Subway Delay Data

- **URL:** https://open.toronto.ca/dataset/ttc-subway-delay-data/
- **CKAN UUID:** 996cfe8d-fb35-40ce-b569-698d51fc683b
- **Snapshot date:** 2026-06-10
- **Files:**
  - `ttc-subway-delay-data-since-2025.csv` — 35,385 rows, Jan 2025–present
    SHA-256: `5a13c07c9a0cda737f823c1a69a00335f00ef2d996dacfedd9d1e3b50c1f0d41`
  - `ttc-subway-delay-codes.xlsx` — Delay code lookup (130 codes × 2 systems)
    SHA-256: `7ced9b9aa9084b2c7c0bfe12a2a687225c0ea4d1f40122dd5d889f73fb291bdd`
- **Historical files (2014–2024):** Available as XLSX from the CKAN portal but not
  included in this snapshot. Can be added later for multi-year analysis.

## Re-fetch procedure

```bash
# 2025+ CSV (live datastore dump)
curl -L -o raw/ttc-subway-delay-data-since-2025.csv \
  "https://ckan0.cf.opendata.inter.prod-toronto.ca/dataset/996cfe8d-fb35-40ce-b569-698d51fc683b/resource/0b6e5c52-e993-46d6-8d74-8602ee224457/download/ttc-subway-delay-data-since-2025.csv"

# Delay code descriptions
curl -L -o raw/ttc-subway-delay-codes.xlsx \
  "https://ckan0.cf.opendata.inter.prod-toronto.ca/dataset/996cfe8d-fb35-40ce-b569-698d51fc683b/resource/3900e649-f31e-4b79-9f20-4731bbfd94f7/download/ttc-subway-delay-codes.xlsx"
```

## License

The Toronto Open Data Portal publishes this dataset without an explicit
license declaration. The portal's terms of use page states that data is
made available under the **Open Government Licence — Ontario** for
provincial data and the **Open Data Licence for City of Toronto data**.

Verbatim from https://open.toronto.ca/open-data-license/:

> You are free to copy, modify, publish, translate, adapt, distribute or
> otherwise use the Data in any medium, mode or format for any lawful
> purpose. You must, where you do any of the above, acknowledge the
> source of the Data by including any attribution statement specified by
> the Information Provider and, where possible, provide a link to this
> licence.

## Notes

- The dataset uses TTC-internal delay codes (e.g., MUSAN, MUIRS, EUAC).
  The `ttc-subway-delay-codes.xlsx` lookup maps codes to descriptions
  like "Air Conditioning", "Door Problems", etc.
- Station names are TTC internal names (e.g., "BATHURST STATION",
  "DUNDAS STATION") — these need normalization to match bike-share
  station locations.
- `Min Delay` is the reported delay duration in minutes.
- `Min Gap` is the gap between trains caused by the delay.
- `Bound` is the direction (E/W/N/S or blank).
- `Line` is the subway line code: YU (Yonge-University), BD
  (Bloor-Danforth), SRT (Scarborough RT), SHP (Sheppard).
- The 2025+ CSV is a live datastore dump that grows with each month.
  Re-fetching will include new rows.