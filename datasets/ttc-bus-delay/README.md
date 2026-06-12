# TTC Bus Delay Data

Slug: `ttc-bus-delay`
Status: `active`
Added: 2026-06-10

## Source (required)

- **Publisher:** Toronto Transit Commission (TTC), via City of Toronto Open Data
- **Portal:** https://open.toronto.ca/dataset/ttc-bus-delay-data/
- **URL:** https://open.toronto.ca/dataset/ttc-bus-delay-data/
- **API endpoint:** https://ckan0.cf.opendata.inter.prod-toronto.ca/api/3/action/package_show?id=e271cdae-8788-4980-96ce-6a5c95bc6618
- **Source ID:** e271cdae-8788-4980-96ce-6a5c95bc6618
- **First available:** 2014-01 (historical XLSX); 2025-01 (live CSV datastore)

## License (required)

- **License:** custom:OGL-Toronto
- **Verbatim text:** https://open.toronto.ca/open-data-license/

## What's in the data (required)

### `ttc-bus-delay-data-since-2025.csv`
- **Format:** CSV
- **Encoding:** UTF-8
- **Approx rows:** 84,000 (Jan 2025 – present, growing monthly)
- **Update cadence:** monthly (live datastore dump)
- **Fields:**
  - `_id` (int) — datastore row ID
  - `Date` (date) — date of delay event (YYYY-MM-DD)
  - `Time` (time) — approximate time of delay (HH:MM, 24h)
  - `Day` (string) — day of week
  - `Station` (string) — TTC stop or station name (e.g., "WARDEN STATION")
  - `Code` (string) — TTC delay code (e.g., MFESA, EFHV)
  - `Min Delay` (int) — reported delay duration in minutes
  - `Min Gap` (int) — gap between buses caused by delay, in minutes
  - `Bound` (string) — direction (E/W/N/S or blank)
  - `Line` (string) — bus route number and name (e.g., "102 MARKHAM RD")
  - `Vehicle` (int) — vehicle number

### `ttc-bus-delay-codes.csv`
- **Format:** CSV
- **Rows:** 46
- **Fields:**
  - `_id` (int) — row ID
  - `CODE` (string) — delay code (e.g., EFB, MFCN)
  - `DESCRIPTION` (string) — human-readable description

## Refresh & verification (required)

- **Refresh frequency:** monthly
- **Last fetched:** 2026-06-10
- **Last verified:** 2026-06-10 (by jeremyl14)
- **Verification method:** HEAD-checked URL, confirmed ~84,000 rows for 2025+
- **Storage strategy:** `git` (total ~7.5 MB, under 10 MB threshold per ADR-008)
- **Known re-fetch procedure:**
  ```bash
  cd datasets/ttc-bus-delay/raw
  curl -L -o ttc-bus-delay-data-since-2025.csv \
    "https://ckan0.cf.opendata.inter.prod-toronto.ca/dataset/e271cdae-8788-4980-96ce-6a5c95bc6618/resource/b5725365-9252-4bfe-b6f4-cda7ddf74341/download/ttc-bus-delay-data-since-2025.csv"
  curl -L -o ttc-bus-delay-codes.csv \
    "https://ckan0.cf.opendata.inter.prod-toronto.ca/dataset/e271cdae-8788-4980-96ce-6a5c95bc6618/resource/874ae66c-9f6f-443f-91e0-1d37d416e0d8/download/code-descriptions.csv"
  sha256sum ttc-bus-delay-data-since-2025.csv ttc-bus-delay-codes.csv
  ```

## How to use (required)

```python
import pandas as pd

delays = pd.read_csv("datasets/ttc-bus-delay/raw/ttc-bus-delay-data-since-2025.csv")
delays["Date"] = pd.to_datetime(delays["Date"])
# Filter to 2025
delays_2025 = delays[delays["Date"].dt.year == 2025]

codes = pd.read_csv("datasets/ttc-bus-delay/raw/ttc-bus-delay-codes.csv")
```

## Notes (required)

- `Line` contains bus route numbers and names (e.g., "102 MARKHAM RD"), not line codes like the subway dataset. There are ~170 distinct routes.
- `Station` refers to bus stop or terminal names, not subway stations. Many are intersection names.
- `Min Delay` of 0 means the delay was reported but duration was not recorded or was under 1 minute.
- Bus delay codes (46 codes) are completely different from subway delay codes (200 codes). The first-letter convention (E=Equipment, M=Operations, P=Infrastructure, S=Safety, T=Transportation) still applies.
- Historical data (2014–2024) is available as separate XLSX files per year from the portal but is not included in this snapshot.

## Provenance

See `raw/SOURCE.md` for the exact snapshot date, hash, and license text.

## Analyses

- `analysis/route-delay-ranking/` — which bus routes accumulate the most delay and what drives them
- `analysis/rush-hour-reliability/` — rush vs off-peak delay comparison
- `analysis/delay-cause-taxonomy/` — delay cause categories and bus-vs-subway comparison
- `analysis/dufferin-29-over-time/` — Route 29 Dufferin delay trends over 2025

---

## Author

jeremyl14, 2026-06-10