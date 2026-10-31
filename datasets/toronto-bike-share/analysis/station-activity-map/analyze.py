"""Station activity map: how much each Bike Share Toronto station is used,
and where, day by day from 2018-01-01 to 2026-09-30.

Activity = trip starts + trip ends at a station. Each frame is the 7-day
rolling sum ending on that day. Stations are placed with the location that
was valid on that date (inputs/station-locations.csv, see fetch_inputs.py).

Outputs:
  outputs/station-activity-map.html  self-contained interactive map
  outputs/summary.csv                per-year row/endpoint counts and coverage
"""

import base64
import bisect
import csv
import datetime as dt
import json
import pathlib

import duckdb
import numpy as np

HERE = pathlib.Path(__file__).resolve().parent
RAW_DIR = HERE.parents[1] / "raw"
INPUTS_DIR = HERE / "inputs"
OUTPUTS_DIR = HERE / "outputs"

DOWNTOWN_WARDS = {10, 11, 13}  # Spadina-Fort York, University-Rosedale, Toronto Centre

START = dt.date(2018, 1, 1)
END = dt.date(2026, 9, 30)
WINDOW = 7
# A run of at least this many days with no trip starts is treated as missing
# upstream data (e.g. November 2022 is absent from the 2022 file), not as zero use.
MIN_GAP_DAYS = 3

# Column positions (1-based) of start id, start time, end id, end time, and the
# timestamp format. 2018 has its own column order; 2019 onward share one.
# 2019-2023 use month-first dates (verified: first field never exceeds 12).
LAYOUT_2018 = (3, 4, 7, 6, "%m/%d/%Y %H:%M")
LAYOUT_SLASH = (3, 4, 6, 7, "%m/%d/%Y %H:%M")
LAYOUT_ISO = (3, 4, 6, 7, "%Y-%m-%d %H:%M:%S")
FILES = [
    (2018, RAW_DIR / "bike-share-toronto-ridership-2018.csv", LAYOUT_2018),
    *[(y, RAW_DIR / f"bike-share-toronto-ridership-{y}.csv", LAYOUT_SLASH) for y in (2019, 2020, 2021)],
    # 2022 re-snapshot with November; the top-level 2022 file is missing it
    (2022, RAW_DIR / "2026-10-31" / "bike-share-toronto-ridership-2022.csv", LAYOUT_SLASH),
    (2023, RAW_DIR / "bike-share-toronto-ridership-2023.csv", LAYOUT_SLASH),
    (2024, RAW_DIR / "bike-share-toronto-ridership-2024.csv", LAYOUT_ISO),
    (2025, RAW_DIR / "bike-share-toronto-ridership-2025.csv", LAYOUT_ISO),
    # Jan-Sep 2026 re-snapshot; the top-level 2026 file is Jan-Mar only
    (2026, RAW_DIR / "2026-10-30" / "bike-share-toronto-ridership-2026.csv", LAYOUT_ISO),
]


def endpoints_sql(year, path, layout):
    """One row per trip endpoint: (year, station_id, day). Rows in some 2020
    files lack the duration column, which shifts every later field left by one;
    those are detected by the start time sitting one column early."""
    sid, st, eid, et, fmt = layout
    src = f"read_csv('{path}', all_varchar=true, header=true, null_padding=true, strict_mode=false)"

    def ts(col):
        return f"try_strptime(trim(#{col}), '{fmt}')"

    shifted = f"({ts(st)} IS NULL AND {ts(st - 1)} IS NOT NULL)"

    def pick(normal, col_shift):
        return f"CASE WHEN {shifted} THEN {col_shift} ELSE {normal} END"

    sid_v = pick(f"#{sid}", f"#{sid - 1}")
    st_v = pick(ts(st), ts(st - 1))
    eid_v = pick(f"#{eid}", f"#{eid - 1}")
    et_v = pick(ts(et), ts(et - 1))
    return f"""
        SELECT {year} AS year, 'start' AS side, {shifted} AS shifted,
               TRY_CAST(TRY_CAST(trim({sid_v}) AS DOUBLE) AS INTEGER) AS station_id,
               CAST({st_v} AS DATE) AS day
        FROM {src}
        UNION ALL
        SELECT {year}, 'end', {shifted},
               TRY_CAST(TRY_CAST(trim({eid_v}) AS DOUBLE) AS INTEGER),
               CAST({et_v} AS DATE)
        FROM {src}
    """


def load_endpoints():
    con = duckdb.connect()
    con.execute("CREATE TABLE ep AS " + " UNION ALL ".join(endpoints_sql(*f) for f in FILES))
    counts = con.execute(f"""
        SELECT station_id, day, count(*) AS n
        FROM ep
        WHERE station_id IS NOT NULL AND day BETWEEN DATE '{START}' AND DATE '{END}'
        GROUP BY ALL
    """).fetchall()
    start_days = con.execute(f"""
        SELECT day, count(*) FROM ep
        WHERE side = 'start' AND day BETWEEN DATE '{START}' AND DATE '{END}'
        GROUP BY day
    """).fetchall()
    per_year = con.execute(f"""
        SELECT year,
               count(*) FILTER (WHERE side = 'start') AS trips,
               count(*) FILTER (WHERE side = 'start' AND shifted) AS shifted_rows,
               count(*) AS endpoints,
               count(*) FILTER (WHERE day IS NULL) AS no_time,
               count(*) FILTER (WHERE day IS NOT NULL AND station_id IS NULL) AS no_station_id,
               count(*) FILTER (WHERE day NOT BETWEEN DATE '{START}' AND DATE '{END}') AS out_of_range
        FROM ep GROUP BY year ORDER BY year
    """).fetchall()
    return counts, start_days, per_year


def find_gaps(start_days, ndays):
    """Runs of >= MIN_GAP_DAYS consecutive days with no trip starts, as
    inclusive [first, last] day indices."""
    starts = np.zeros(ndays, dtype=np.int64)
    for day, n in start_days:
        starts[(day - START).days] = n
    gaps, run = [], None
    for d in range(ndays):
        if starts[d] == 0:
            run = [run[0], d] if run else [d, d]
        elif run:
            gaps.append(run)
            run = None
    if run:
        gaps.append(run)
    return [g for g in gaps if g[1] - g[0] + 1 >= MIN_GAP_DAYS]


def load_locations():
    spans = {}
    with open(INPUTS_DIR / "station-locations.csv", newline="") as fh:
        for r in csv.DictReader(fh):
            spans.setdefault(int(r["station_id"]), []).append(r)
    for rows in spans.values():
        rows.sort(key=lambda r: r["first_seen"])
    return spans


def build_dots(counts, spans):
    """A dot is one station at one location. A station seen at several
    locations becomes several dots; each day goes to the span whose
    first_seen is the latest on or before that day (or the first span)."""
    ndays = (END - START).days + 1
    dots, dot_index = [], {}
    for sid, rows in spans.items():
        for k, r in enumerate(rows):
            dot_index[(sid, k)] = len(dots)
            dots.append(dict(id=sid, name=r["name"], lat=float(r["lat"]), lon=float(r["lon"])))
    starts = {sid: [dt.date.fromisoformat(r["first_seen"]) for r in rows] for sid, rows in spans.items()}

    daily = np.zeros((len(dots), ndays), dtype=np.int64)
    unlocated = np.zeros(ndays, dtype=np.int64)
    for sid, day, n in counts:
        d = (day - START).days
        if sid not in spans:
            unlocated[d] += n
            continue
        k = max(bisect.bisect_right(starts[sid], day) - 1, 0)
        daily[dot_index[(sid, k)], d] += n
    return dots, daily, unlocated


def ward_of(lon, lat, wards):
    """Ward number containing the point (ray casting), or 0 if none."""
    for f in wards["features"]:
        for poly in f["geometry"]["coordinates"]:
            ring, inside = poly[0], False
            for (x1, y1), (x2, y2) in zip(ring, ring[1:] + ring[:1]):
                if (y1 > lat) != (y2 > lat) and lon < x1 + (lat - y1) * (x2 - x1) / (y2 - y1):
                    inside = not inside
            if inside:
                return f["properties"]["ward"]
    return 0


def rolling(a, window):
    c = np.cumsum(a, axis=-1)
    out = c.copy()
    out[..., window:] = c[..., window:] - c[..., :-window]
    return out


def pack(dots, roll):
    """Trim each dot to its active range and pack values as little-endian uint16."""
    assert roll.max() <= 0xFFFF, f"7-day station value {roll.max()} exceeds uint16"
    chunks, meta, offset = [], [], 0
    for i, dot in enumerate(dots):
        nz = np.flatnonzero(roll[i])
        if not len(nz):
            continue
        a, b = int(nz[0]), int(nz[-1]) + 1
        chunks.append(roll[i, a:b].astype("<u2").tobytes())
        meta.append([dot["id"], dot["name"], round(dot["lat"], 5), round(dot["lon"], 5), a, b - a, offset])
        offset += b - a
    return base64.b64encode(b"".join(chunks)).decode(), meta


def main():
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    counts, start_days, per_year = load_endpoints()
    spans = load_locations()
    dots, daily, unlocated = build_dots(counts, spans)
    gaps = find_gaps(start_days, daily.shape[1])
    for a, b in gaps:
        print(f"missing data: {START + dt.timedelta(a)} to {START + dt.timedelta(b)} ({b - a + 1} days)")

    roll = rolling(daily, WINDOW)
    total = roll.sum(axis=0)
    wards = json.loads((INPUTS_DIR / "wards.geojson").read_text())
    downtown = np.array([ward_of(d["lon"], d["lat"], wards) in DOWNTOWN_WARDS for d in dots])
    values_b64, meta = pack(dots, roll)

    # Colour domains come from complete frames only
    complete = np.ones(roll.shape[1], dtype=bool)
    for a, b in gaps:
        complete[a : b + WINDOW] = False
    nonzero = roll[:, complete][roll[:, complete] > 0]
    share = (roll / np.maximum(total, 1))[:, complete][roll[:, complete] > 0]
    payload = dict(
        start=START.isoformat(), ndays=int(roll.shape[1]), window=WINDOW,
        dots=meta, values=values_b64,
        total=total.tolist(), daily=daily.sum(axis=0).tolist(),
        unlocated=rolling(unlocated, WINDOW).tolist(),
        gaps=gaps,
        domain=dict(
            count=[0, int(np.percentile(nonzero, 99.9))],  # cube-root scale in the page
            share=[float(np.percentile(share, 0.1)), float(np.percentile(share, 99.9))],
        ),
        wards=wards,
        lake=json.loads((INPUTS_DIR / "lake.geojson").read_text()),
    )
    template = (HERE / "template.html").read_text()
    html = template.replace("/*__DATA__*/null", json.dumps(payload, separators=(",", ":")))
    (OUTPUTS_DIR / "station-activity-map.html").write_text(html)

    # Per-year summary; "located" is counted by endpoint date, the others by source file
    year_of = np.array([(START + dt.timedelta(days=d)).year for d in range(daily.shape[1])])
    active = (roll > 0).sum(axis=0)
    with open(OUTPUTS_DIR / "summary.csv", "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["year", "trips", "rows_missing_duration_column", "endpoints", "no_time",
                    "no_station_id", "out_of_range", "located", "located_share",
                    "peak_7day_activity", "peak_7day_date", "max_active_stations", "downtown_wards_share"])
        for year, trips, shifted, eps, no_time, no_id, oor in per_year:
            days = (year_of == year) & complete
            loc = int(daily[:, year_of == year].sum())
            in_range = eps - no_time - no_id - oor
            peak = int(np.argmax(np.where(days, total, -1)))
            w.writerow([year, trips, shifted, eps, no_time, no_id, oor, loc,
                        f"{loc / in_range:.4f}" if in_range else "",
                        int(total[peak]), (START + dt.timedelta(days=peak)).isoformat(),
                        int(active[days].max()),
                        f"{daily[downtown][:, year_of == year].sum() / max(loc, 1):.3f}"])

    print(f"dots drawn: {len(meta)} of {len(dots)} station locations")
    print(f"max 7-day station activity: {int(roll.max())}")
    print(f"Saved {OUTPUTS_DIR / 'station-activity-map.html'} "
          f"({(OUTPUTS_DIR / 'station-activity-map.html').stat().st_size / 1e6:.1f} MB)")
    print(f"Saved {OUTPUTS_DIR / 'summary.csv'}")


if __name__ == "__main__":
    main()
