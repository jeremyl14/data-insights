# Source — station activity map inputs

Small reference files built by `../fetch_inputs.py` on **2026-10-31**.
They are committed so `analyze.py` runs without network access.

## Station locations (`stations.csv`, `station-locations.csv`)

- **Live feed:** Bike Share Toronto GBFS `station_information`
  https://tor.publicbikesystem.net/ube/gbfs/v1/en/station_information
  (`last_updated` 2026-10-31; 1,073 stations)
- **Archived feed:** every distinct Internet Archive Wayback Machine
  capture of that feed and of the pre-GBFS
  `feeds.bikesharetoronto.com/stations/stations.json` feed
  (22 captures, 2016-06-23 to 2026-03-10; listed in `captures.txt`).
  The archive is the only source for stations that have since closed
  and for the earlier locations of stations that moved.
- **License:** City of Toronto Open Government Licence — Toronto
  (https://open.toronto.ca/open-data-license/), as published for the
  Bike Share Toronto dataset on open.toronto.ca.

Station IDs below 7000 belong to the pre-July-2016 system and are
dropped; no trip record that carries a station ID uses them.

`station-locations.csv` has one row per station per physical location:
consecutive sightings within 25 m are merged into one span with
`first_seen` / `last_seen` capture dates. 1,186 stations, 1,400 spans;
113 stations are no longer in the live feed. Some IDs were reused at a
different site (e.g. 7084 and 7086 moved 13–14 km), which is why trips
are joined to the span valid on the trip date rather than to one
coordinate per ID.

Archive coverage has gaps (no captures between 2017-07 and 2019-08, or
during 2018 and 2020), so a move that happened inside a gap is dated to
the next capture.

## Ward boundaries (`wards.geojson`)

- **Source:** City of Toronto Open Data, City Wards (25-ward model),
  resource `737b29e0-8329-4260-b6af-21555ab24f28`, EPSG:4326 GeoJSON
  https://open.toronto.ca/dataset/city-wards/
- **License:** Open Government Licence — Toronto
- **Processing:** coordinates rounded to 5 decimals and simplified with
  Ramer–Douglas–Peucker at 0.0001° (~11 m); only `AREA_SHORT_CODE`
  (as `ward`) and `AREA_NAME` (as `name`) kept.

## Water (`lake.geojson`)

- **Source:** City of Toronto Open Data, Topographic Mapping – Waterbodies
  & Rivers, resource `41ab6d6b-72ac-4711-a540-7ea4e8589a36` (Water Body,
  EPSG:4326 GeoJSON)
  https://open.toronto.ca/dataset/topographic-mapping-waterbodies-and-rivers/
- **License:** Open Government Licence — Toronto
- **Why:** ward 10's boundary runs through the harbour and around Toronto
  Island, so the wards alone draw the islands and harbour as one block of
  land. The water is drawn over the wards to show the real shoreline.
- **Processing:** the `Lake Ontario` feature plus every water feature lying
  entirely inside lon −79.43…−79.31, lat 43.60…43.66 with ≥ 50 outline
  points (Toronto Harbour, Keating Channel, Mooring Basin, Brigantine Cove,
  the island lagoons and ponds); 18 features. Coordinates rounded to
  5 decimals and simplified with Ramer–Douglas–Peucker at 0.00005° (~5 m).

## File hashes (SHA-256)

```
3a9e30830c457ffdef7b286bcfdfa1981ea92d74960573f93b9b0d3573db178a  captures.txt
c0beb3085e503574a5a266537c7d534b37ef7c91922fc28d07f6f0392e8ea8e4  lake.geojson
42343df299db306a4d90dd32fa3e74a58285a8dc071eead332fd6e746057b743  station-locations.csv
64c5974667d2644a7e095031b3694c692a7307b3ade03bd50e6c11d6f98edf09  stations.csv
3936d10118cb30b825cc21eaaf692119332f7f98f274a3144ea65c38ef56cfc8  wards.geojson
```

## Re-fetch

```bash
python fetch_inputs.py --cache /tmp/wayback-cache
```

The live feed changes daily and new Wayback captures appear over time,
so a re-fetch will not reproduce these hashes; commit the new files with
an updated snapshot date here.
