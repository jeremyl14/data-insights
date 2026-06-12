# Source: Toronto Pearson daily weather

- **URL:** https://climate.weather.gc.ca/climate_data/bulk_data_e.html?format=csv&stationID=51459&Year=2025&Month=1&Day=1&timeframe=2&submit=Download+Data
- **Station:** Toronto Pearson International Airport (Climate ID 6158731, Station ID 51459)
- **Snapshot date:** 2026-06-10
- **File:** `toronto-pearson-daily-2025.csv`
- **SHA-256:** `c142160ccafb73b249893185e0b2a7d4e788bc2333e4a14855795c30f9a4fdae`
- **Rows:** 365 (Jan 1 – Dec 31, 2025)

## Re-fetch procedure

```bash
curl -L -o raw/toronto-pearson-daily-2025.csv \
  "https://climate.weather.gc.ca/climate_data/bulk_data_e.html?format=csv&stationID=51459&Year=2025&Month=1&Day=1&timeframe=2&submit=Download+Data"
```

## License

Environment and Climate Change Canada historical climate data is published under the
**Open Government Licence — Canada**:
https://open.canada.ca/en/open-government-licence-canada

Verbatim terms:

> You are free to copy, modify, publish, translate, adapt, distribute or otherwise use
> the Information in any medium, mode or format for any lawful purpose.
> ...
> You must, where you do any of the above in relation to the Information, acknowledge
> the source of the Information by including any attribution statement specified by
> the Information Provider and, where possible, provide a link to this licence.

## Notes

- Station 51459 is Toronto Pearson International Airport (43.68°N, 79.63°W),
  approximately 20 km from downtown Toronto.
- Trace precipitation values ("T") appear in the raw CSV and should be treated as 0.0.
- Missing numeric values are empty strings in the CSV.
- Snow on Ground is measured at 06:00 UTC.
- For multi-year coverage, additional station IDs or monthly downloads may be needed.