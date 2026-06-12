# Toronto Pearson Daily Weather

Slug: `toronto-weather-daily`
Status: `active`
Added: 2026-06-10

## Source (required)

- **Publisher:** Environment and Climate Change Canada (ECCC)
- **Portal:** https://climate.weather.gc.ca
- **URL:** https://climate.weather.gc.ca/climate_data/daily_data_e.html?StationID=51459
- **API endpoint:** https://climate.weather.gc.ca/climate_data/bulk_data_e.html?format=csv&stationID=51459&Year=2025&Month=1&Day=1&timeframe=2&submit=Download+Data
- **Source ID:** 51459 (ECCC Station ID)
- **First available:** 1937 (Pearson station history)
- **Last updated upstream:** Ongoing (daily observations added)

## License (required)

- **License:** OGL-Canada
- **Verbatim text:** https://open.canada.ca/en/open-government-licence-canada

## What's in the data (required)

### `toronto-pearson-daily-2025.csv`
- **Format:** CSV
- **Encoding:** UTF-8
- **Approx rows:** 365 (one per day, Jan 1 – Dec 31, 2025)
- **Update cadence:** manual (re-fetch when needed for new analyses)
- **Fields:**
  - `Date/Time` (date) — YYYY-MM-DD
  - `Max Temp (°C)` (float) — daily maximum temperature
  - `Min Temp (°C)` (float) — daily minimum temperature
  - `Mean Temp (°C)` (float) — daily mean temperature
  - `Total Rain (mm)` (float) — daily rainfall
  - `Total Snow (cm)` (float) — daily snowfall
  - `Total Precip (mm)` (float) — total precipitation (rain + snow melt equivalent)
  - `Snow on Grnd (cm)` (float) — snow on ground at 06:00 UTC
  - Additional fields: Data Quality flags, Heat/Cool Degree Days, Gust direction/speed

### `toronto-pearson-daily-2026.csv`
- **Format:** CSV (same schema as 2025)
- **Approx rows:** ~150 (Jan 1 – May 31, 2026; partial year)
- **Note:** This file will grow as 2026 data becomes available from ECCC

## Refresh & verification (required)

- **Refresh frequency:** manual
- **Last fetched:** 2026-06-10
- **Last verified:** 2026-06-10 (by jeremyl14)
- **Verification method:** HEAD-checked URL, confirmed 365 rows for 2025
- **Storage strategy:** `git` (44 KB, well under threshold)
- **Known re-fetch procedure:**
  ```bash
  curl -L -o raw/toronto-pearson-daily-2025.csv \
    "https://climate.weather.gc.ca/climate_data/bulk_data_e.html?format=csv&stationID=51459&Year=2025&Month=1&Day=1&timeframe=2&submit=Download+Data"
  ```

## How to use (required)

```python
import pandas as pd

df = pd.read_csv(
    "datasets/toronto-weather-daily/raw/toronto-pearson-daily-2025.csv",
    parse_dates=["Date/Time"],
)
# Strip whitespace from column names
df.columns = [c.strip() for c in df.columns]
# Convert trace values and blanks to 0.0 for numeric columns
for col in ["Total Rain (mm)", "Total Snow (cm)", "Total Precip (mm)"]:
    df[col] = pd.to_numeric(df[col].astype(str).str.replace("T", "0.0"), errors="coerce").fillna(0.0)
```

## Notes (required)

- Station is Toronto Pearson International Airport, ~20 km from downtown.
  Urban heat island and lake-effect differences mean downtown conditions
  may differ from Pearson readings.
- Trace precipitation ("T") appears in the raw CSV. Convert to 0.0 for analysis.
- Missing numeric values are empty strings — fill with 0.0 or NaN depending on context.
- Snow on Ground is measured at 06:00 UTC, not end-of-day.
- Currently covers 2025 (full year) and 2026 (Jan–May, partial). Additional years can be fetched by changing the `Year=` and `Month=` parameters in the URL.

## Provenance

See `raw/SOURCE.md` for the exact snapshot date, hash, and license text.

## Analyses

- `../toronto-bike-share/analysis/weather-ridership/` — ridership vs precipitation overlay
- `../toronto-bike-share/analysis/weather-lag-regression/` — distributed lag model
- `../toronto-bike-share/analysis/correlation-structure/` — CCF and partial correlations

---

## Author

jeremyl14, 2026-06-10