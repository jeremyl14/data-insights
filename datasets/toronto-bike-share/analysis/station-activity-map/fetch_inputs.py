"""Build the small reference inputs for the station activity map.

Writes, into inputs/:
  station-locations.csv  one row per (station_id, location) span, built from the
                         live GBFS station_information feed plus every distinct
                         Wayback Machine capture of it (closed stations and
                         reused IDs are only recoverable from the archive)
  stations.csv           one row per station_id: latest name/lat/lon/capacity,
                         first/last seen, max movement between observations
  wards.geojson          City of Toronto 25-ward boundaries, simplified
  lake.geojson           Lake Ontario within city limits plus the harbour and
                         Toronto Island water features, simplified; drawn over the
                         wards so the shoreline and islands show (ward 10's
                         boundary runs through the water around the islands)
  captures.txt           the Wayback captures used, for provenance

Usage:
    python fetch_inputs.py [--cache DIR]

--cache keeps downloaded captures between runs (the Wayback Machine rate-limits).
"""

import argparse
import csv
import gzip
import json
import math
import pathlib
import time
import urllib.request
from datetime import datetime, timezone

HERE = pathlib.Path(__file__).resolve().parent
INPUTS_DIR = HERE / "inputs"

GBFS_URL = "https://tor.publicbikesystem.net/ube/gbfs/v1/en/station_information"
WAYBACK_URLS = [
    "tor.publicbikesystem.net/ube/gbfs/v1/en/station_information",
    "feeds.bikesharetoronto.com/stations/stations.json",
]
WARDS_URL = (
    "https://ckan0.cf.opendata.inter.prod-toronto.ca/dataset/5e7a8234-f805-43ac-820f-03d7c360b588"
    "/resource/737b29e0-8329-4260-b6af-21555ab24f28/download/city-wards-data-4326.geojson"
)
WATER_URL = (
    "https://ckan0.cf.opendata.inter.prod-toronto.ca/dataset/f352a9e9-4077-4c59-b0a9-f35a56fb24be"
    "/resource/41ab6d6b-72ac-4711-a540-7ea4e8589a36/download/water-body-4326.geojson"
)

# Locations within this distance are treated as the same physical spot
SAME_SPOT_M = 25
# Ward outline simplification tolerance, in degrees (~11 m)
SIMPLIFY_DEG = 0.0001
# Shoreline tolerance (~5 m), finer so the islands and spits keep their shape
SHORE_SIMPLIFY_DEG = 0.00005
# Harbour / Toronto Island area (lon min, lon max, lat min, lat max) whose
# water features are drawn in addition to Lake Ontario
WATERFRONT = (-79.43, -79.31, 43.60, 43.66)


def fetch(url, retries=5):
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(url, timeout=60) as resp:
                body = resp.read()
            return gzip.decompress(body) if body[:2] == b"\x1f\x8b" else body
        except Exception as e:
            if attempt == retries - 1:
                raise
            wait = 15 * (attempt + 1)
            print(f"  retry in {wait}s: {e}")
            time.sleep(wait)


def list_captures():
    captures = []
    for url in WAYBACK_URLS:
        cdx = (
            "https://web.archive.org/cdx/search/cdx?url="
            f"{url}&fl=timestamp,original&filter=statuscode:200&collapse=digest"
        )
        for line in fetch(cdx).decode().splitlines():
            ts, original = line.split()
            captures.append((ts, original))
    return sorted(captures)


def parse_feed(body, date):
    data = json.loads(body)
    if "data" in data:  # GBFS
        for s in data["data"]["stations"]:
            yield dict(id=str(s["station_id"]), name=s["name"].strip(), lat=float(s["lat"]),
                       lon=float(s["lon"]), cap=s.get("capacity"), date=date)
    else:  # pre-GBFS Bike Share Toronto stations.json
        for s in data["stationBeanList"]:
            yield dict(id=str(s["id"]), name=s["stationName"].strip(), lat=float(s["latitude"]),
                       lon=float(s["longitude"]), cap=s.get("totalDocks"), date=date)


def metres(a, b):
    dy = (a["lat"] - b["lat"]) * 111_320
    dx = (a["lon"] - b["lon"]) * 111_320 * math.cos(math.radians(a["lat"]))
    return math.hypot(dx, dy)


def build_stations(observations):
    by_id = {}
    for o in sorted(observations, key=lambda o: o["date"]):
        by_id.setdefault(o["id"], []).append(o)

    stations, spans = [], []
    for sid in sorted(by_id, key=int):
        obs = by_id[sid]
        last = obs[-1]
        stations.append(dict(
            station_id=sid, name=last["name"], lat=round(last["lat"], 6), lon=round(last["lon"], 6),
            capacity=last["cap"] if last["cap"] is not None else "",
            first_seen=obs[0]["date"], last_seen=last["date"],
            in_live_feed=last["live"], n_snapshots=len({o["date"] for o in obs}),
            max_move_m=round(max(metres(obs[0], o) for o in obs)),
        ))
        span = None
        for o in obs:
            if span and metres(span, o) < SAME_SPOT_M:
                span["last_seen"] = o["date"]
                continue
            span = dict(station_id=sid, name=o["name"], lat=round(o["lat"], 6), lon=round(o["lon"], 6),
                        first_seen=o["date"], last_seen=o["date"])
            spans.append(span)
    return stations, spans


def simplify(points, tol):
    """Ramer-Douglas-Peucker on a list of [lon, lat]."""
    if len(points) < 3:
        return points
    (x1, y1), (x2, y2) = points[0], points[-1]
    dx, dy = x2 - x1, y2 - y1
    norm = math.hypot(dx, dy) or 1e-12
    idx, dmax = 0, 0.0
    for i in range(1, len(points) - 1):
        x, y = points[i]
        d = abs(dy * x - dx * y + x2 * y1 - y2 * x1) / norm
        if d > dmax:
            idx, dmax = i, d
    if dmax <= tol:
        return [points[0], points[-1]]
    return simplify(points[: idx + 1], tol)[:-1] + simplify(points[idx:], tol)


def simplify_ring(ring, tol):
    pts = [[round(x, 5), round(y, 5)] for x, y, *_ in ring]
    # A closed ring starts and ends on the same point, which RDP can't
    # measure against; split it at the vertex farthest from the start.
    far = max(range(len(pts)), key=lambda i: math.dist(pts[0], pts[i]))
    return simplify(pts[: far + 1], tol)[:-1] + simplify(pts[far:], tol)


def build_wards():
    gj = json.loads(fetch(WARDS_URL))
    features = []
    for f in gj["features"]:
        props = f["properties"]
        geom = f["geometry"]
        polys = geom["coordinates"] if geom["type"] == "MultiPolygon" else [geom["coordinates"]]
        rings = []
        for poly in polys:
            for ring in poly:
                pts = simplify_ring(ring, SIMPLIFY_DEG)
                if len(pts) >= 4:
                    rings.append(pts)
        features.append(dict(
            type="Feature",
            properties=dict(ward=int(props["AREA_SHORT_CODE"]), name=props["AREA_NAME"]),
            geometry=dict(type="MultiPolygon", coordinates=[[r] for r in rings]),
        ))
    return dict(type="FeatureCollection", features=features)


def build_lake():
    """Lake Ontario plus the water features of the harbour and Toronto Island
    (Toronto Harbour, Keating Channel, island lagoons...), which the City maps
    as separate polygons. Each feature keeps all its rings, to be filled on
    its own with the even-odd rule."""
    gj = json.loads(fetch(WATER_URL))
    features = []
    for f in gj["features"]:
        geom = f["geometry"]
        polys = geom["coordinates"] if geom["type"] == "MultiPolygon" else [geom["coordinates"]]
        outer = [pt for poly in polys for pt in poly[0]]
        lons, lats = [pt[0] for pt in outer], [pt[1] for pt in outer]
        name = f["properties"].get("WATERBODY_NAME")
        in_waterfront = (min(lons) >= WATERFRONT[0] and max(lons) <= WATERFRONT[1]
                         and min(lats) >= WATERFRONT[2] and max(lats) <= WATERFRONT[3])
        if name != "Lake Ontario" and not (in_waterfront and len(outer) >= 50):
            continue
        rings = []
        for poly in polys:
            for ring in poly:
                pts = simplify_ring(ring, SHORE_SIMPLIFY_DEG)
                if len(pts) >= 4:
                    rings.append(pts)
        if rings:
            features.append(dict(type="Feature", properties=dict(name=name),
                                 geometry=dict(type="Polygon", coordinates=rings)))
    return dict(type="FeatureCollection", features=features)


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--cache", type=pathlib.Path, help="directory to cache Wayback captures in")
    args = parser.parse_args()
    INPUTS_DIR.mkdir(exist_ok=True)

    observations = []
    captures = list_captures()
    print(f"Wayback captures: {len(captures)}")
    for ts, original in captures:
        cached = args.cache / f"{ts}.json" if args.cache else None
        if cached and cached.exists():
            body = cached.read_bytes()
        else:
            body = fetch(f"https://web.archive.org/web/{ts}id_/{original}")
            if cached:
                cached.parent.mkdir(parents=True, exist_ok=True)
                cached.write_bytes(body)
            time.sleep(6)
        date = f"{ts[:4]}-{ts[4:6]}-{ts[6:8]}"
        observations += [dict(o, live=False) for o in parse_feed(body, date)]

    live = fetch(GBFS_URL)
    live_date = datetime.fromtimestamp(json.loads(live)["last_updated"], timezone.utc).strftime("%Y-%m-%d")
    observations += [dict(o, live=True) for o in parse_feed(live, live_date)]

    # Drop (0, 0) placeholders and the pre-July-2016 system's IDs (< 7000),
    # which no trip record carrying a station ID uses.
    observations = [o for o in observations
                    if abs(o["lat"]) > 1 and abs(o["lon"]) > 1 and int(o["id"]) >= 7000]
    stations, spans = build_stations(observations)

    with open(INPUTS_DIR / "stations.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(stations[0]))
        w.writeheader()
        w.writerows(stations)
    with open(INPUTS_DIR / "station-locations.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(spans[0]))
        w.writeheader()
        w.writerows(spans)
    with open(INPUTS_DIR / "captures.txt", "w") as fh:
        fh.write(f"# live GBFS {GBFS_URL} last_updated {live_date}\n")
        fh.writelines(f"{ts} {original}\n" for ts, original in captures)
    (INPUTS_DIR / "wards.geojson").write_text(json.dumps(build_wards(), separators=(",", ":")))
    (INPUTS_DIR / "lake.geojson").write_text(json.dumps(build_lake(), separators=(",", ":")))

    print(f"stations: {len(stations)} ({sum(not s['in_live_feed'] for s in stations)} no longer in live feed)")
    print(f"location spans: {len(spans)}")
    print(f"Saved inputs to {INPUTS_DIR}")


if __name__ == "__main__":
    main()
