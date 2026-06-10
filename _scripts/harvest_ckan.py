#!/usr/bin/env python3
"""Harvester: pull package metadata from a CKAN portal into a CSV skeleton.

Both data.ontario.ca and open.toronto.ca expose a CKAN API at
/api/3/action/package_search. This script pulls a slice of packages and
prints a CSV row per package, suitable for pasting into
catalog/datasets.csv (you'll need to fill in license, tags, status by hand).

Examples:
    # Pull 50 packages from Ontario
    python _scripts/harvest_ckan.py --portal https://data.ontario.ca --rows 50

    # Pull everything from Toronto (rate-limited, will be slow)
    python _scripts/harvest_ckan.py --portal https://open.toronto.ca --rows 1000

    # Filter by tag (CKAN q=)
    python _scripts/harvest_ckan.py --portal https://data.ontario.ca --q tags:health

    # Output only what you need
    python _scripts/harvest_ckan.py --portal https://open.toronto.ca --rows 20 \\
        --columns id,name,source_id,url,license,format

The script does NOT write to the catalog file. It prints to stdout. You
decide what gets committed. This is intentional — harvesting is not the
same as curating.

Stdlib only. urllib + json + csv. If you need authenticated requests or
Socrata-specific quirks, swap in `ckanapi` or `sodapy`.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Iterator

LICENSE_MAP = {
    "OGL-Ontario": "OGL-Ontario",
    "Open Government Licence – Ontario": "OGL-Ontario",
    "Open Government Licence - Ontario": "OGL-Ontario",
    "Open Data Commons – Open Database License": "ODC-BY",
    "Open Data Commons - Open Database License": "ODC-BY",
    "ODC-ODbL": "ODC-BY",
    "ODbL": "ODC-BY",
    "Open Data Commons Attribution License": "ODC-BY",
    "Creative Commons Attribution": "CC-BY",
    "CC BY": "CC-BY",
    "CC0": "CC0",
    "Creative Commons CC0": "CC0",
}

FORMAT_MAP = {
    "csv": "csv",
    "CSV": "csv",
    "json": "json",
    "JSON": "json",
    "geojson": "geojson",
    "GeoJSON": "geojson",
    "xml": "xml",
    "XML": "xml",
    "xlsx": "xlsx",
    "XLSX": "xlsx",
    "xls": "xlsx",
    "XLS": "xlsx",
    "parquet": "parquet",
    "Parquet": "parquet",
    "pdf": "xlsx",  # treat pdfs as xlsx-formatted "other" — better: add a pdf token to schema
    "api": "api",
    "API": "api",
}

DEFAULT_COLUMNS = [
    "id",
    "name",
    "source",
    "source_id",
    "url",
    "api_url",
    "license",
    "format",
    "tags",
    "refresh_frequency",
    "last_fetched",
    "last_verified",
    "size_mb",
    "status",
    "added_by",
    "added_on",
    "superseded_by",
    "notes",
]


def http_get_json(url: str, timeout: int = 30) -> dict:
    req = urllib.request.Request(
        url, headers={"User-Agent": "data-analysis-harvester/0.1"}
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def slugify(name: str) -> str:
    """Best-effort slug from a dataset name."""
    s = name.lower()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    s = s.strip("-")
    return s[:80]  # cap to keep slugs readable


def portal_source(portal: str) -> str:
    p = portal.lower()
    if "ontario" in p:
        return "ontario"
    if "toronto" in p:
        return "toronto"
    if "statcan" in p or "statcan.gc.ca" in p:
        return "statcan"
    if "canada.ca" in p or "open.canada" in p:
        return "canada-open-data"
    return "other"


def normalize_license(raw: str) -> str:
    if not raw:
        return ""
    raw = raw.strip()
    if raw in LICENSE_MAP.values():
        return raw
    if raw in LICENSE_MAP:
        return LICENSE_MAP[raw]
    return f"custom:{raw[:60]}"


def normalize_format(resources: list[dict]) -> str:
    """Pick the dominant format from a package's resources."""
    if not resources:
        return ""
    counts: dict[str, int] = {}
    for r in resources:
        fmt = (r.get("format") or "").strip()
        if not fmt:
            continue
        mapped = FORMAT_MAP.get(
            fmt, "mixed" if len(set(FORMAT_MAP.values())) > 1 else "mixed"
        )
        counts[mapped] = counts.get(mapped, 0) + 1
    if not counts:
        return ""
    if len(counts) == 1:
        return next(iter(counts))
    return "mixed"


def fetch_packages(portal: str, rows: int, q: str | None) -> Iterator[dict]:
    """Yield package dicts, paginated."""
    base = portal.rstrip("/")
    endpoint = f"{base}/api/3/action/package_search"
    page_size = 100
    fetched = 0
    start = 0
    while fetched < rows:
        take = min(page_size, rows - fetched)
        params = {"rows": take, "start": start}
        if q:
            params["q"] = q
        url = f"{endpoint}?{urllib.parse.urlencode(params)}"
        try:
            data = http_get_json(url)
        except urllib.error.URLError as e:
            print(f"FATAL: could not fetch {url}: {e}", file=sys.stderr)
            return
        results = data.get("result", {}).get("results", [])
        if not results:
            return
        for pkg in results:
            yield pkg
        fetched += len(results)
        start += len(results)
        if len(results) < take:
            return
        time.sleep(0.3)  # be polite


def row_from_package(pkg: dict, portal: str) -> dict[str, str]:
    name = (pkg.get("title") or pkg.get("name") or "").strip()
    name_translated = pkg.get("title_translated") or {}
    if isinstance(name_translated, dict):
        name = name_translated.get("en", name) or name
    pid = pkg.get("id") or pkg.get("name") or ""
    slug = slugify(name) or slugify(pid)
    src = portal_source(portal)
    url = pkg.get("url") or ""
    if not url:
        # fall back to CKAN package_show URL
        url = f"{portal.rstrip('/')}/dataset/{pkg.get('name', pid)}"
    api_url = f"{portal.rstrip('/')}/api/3/action/package_show?id={pid}"
    # license: prefer the string, else guess from license_id
    license_str = pkg.get("license_title") or ""
    if not license_str and pkg.get("license_id"):
        license_str = pkg["license_id"]
    license_norm = normalize_license(license_str)
    fmt = normalize_format(pkg.get("resources", []))
    # tags
    tags_field = pkg.get("tags") or []
    tag_list = []
    for t in tags_field:
        if isinstance(t, dict):
            tn = (t.get("display_name") or t.get("name") or "").strip().lower()
        else:
            tn = str(t).strip().lower()
        if tn and tn not in tag_list:
            tag_list.append(tn)
    return {
        "id": slug,
        "name": name,
        "source": src,
        "source_id": pid,
        "url": url,
        "api_url": api_url,
        "license": license_norm,
        "format": fmt,
        "tags": ",".join(tag_list[:10]),
        "refresh_frequency": "",
        "last_fetched": "",
        "last_verified": "",
        "size_mb": "",
        "status": "draft",
        "added_by": "",
        "added_on": "",
        "superseded_by": "",
        "notes": (pkg.get("notes_translated", {}) or {}).get("en", "")[:200]
        if isinstance(pkg.get("notes_translated"), dict)
        else (pkg.get("notes", "") or "")[:200],
    }


def main() -> int:
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    p.add_argument(
        "--portal",
        required=True,
        help="base URL of the CKAN portal, e.g. https://data.ontario.ca",
    )
    p.add_argument(
        "--rows", type=int, default=50, help="max packages to fetch (default: 50)"
    )
    p.add_argument(
        "--q", default=None, help="CKAN search query, e.g. 'tags:health' or 'covid'"
    )
    p.add_argument(
        "--columns",
        default=",".join(DEFAULT_COLUMNS),
        help="comma-separated subset of columns to output",
    )
    args = p.parse_args()

    cols = [c.strip() for c in args.columns.split(",") if c.strip()]
    unknown = [c for c in cols if c not in DEFAULT_COLUMNS]
    if unknown:
        print(f"FATAL: unknown columns: {unknown}", file=sys.stderr)
        return 2

    writer = csv.DictWriter(sys.stdout, fieldnames=cols, extrasaction="ignore")
    writer.writeheader()
    count = 0
    for pkg in fetch_packages(args.portal, args.rows, args.q):
        row = row_from_package(pkg, args.portal)
        writer.writerow({c: row.get(c, "") for c in cols})
        count += 1
    print(f"# harvested {count} package(s) from {args.portal}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
