#!/usr/bin/env python3
"""Query the catalog from the command line.

Examples:
    python _scripts/query.py                          # all rows, formatted
    python _scripts/query.py --tag transport          # tag filter
    python _scripts/query.py --source toronto         # source filter
    python _scripts/query.py --status active          # status filter
    python _scripts/query.py --tag health --format csv  # CSV output
    python _scripts/query.py --summary                # counts by source, status, license

Stdlib only. No external deps. If you need something fancier, install DuckDB
and run a one-liner instead (see README).
"""

from __future__ import annotations

import argparse
import csv
import sys
from collections import Counter
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
CATALOG = REPO_ROOT / "catalog" / "datasets.csv"


def load_rows() -> list[dict[str, str]]:
    with CATALOG.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def matches(row: dict[str, str], args: argparse.Namespace) -> bool:
    if args.source and row.get("source") != args.source:
        return False
    if args.status and row.get("status") != args.status:
        return False
    if args.license and row.get("license") != args.license:
        return False
    if args.format and row.get("format") != args.format:
        return False
    if args.id and args.id != row.get("id"):
        return False
    if args.tag:
        tags = [t.strip().lower() for t in row.get("tags", "").split(",") if t.strip()]
        if args.tag.lower() not in tags:
            return False
    if args.search:
        # case-insensitive substring across name, id, notes, source_id
        haystack = " ".join(
            row.get(k, "") for k in ("id", "name", "notes", "source_id", "url")
        ).lower()
        if args.search.lower() not in haystack:
            return False
    return True


def print_table(rows: list[dict[str, str]]) -> None:
    if not rows:
        print("(no rows match)", file=sys.stderr)
        return
    cols = ["id", "name", "source", "status", "license", "tags"]
    widths = {c: max(len(c), max(len(r.get(c, "")) for r in rows)) for c in cols}
    header = "  ".join(c.ljust(widths[c]) for c in cols)
    print(header)
    print("  ".join("-" * widths[c] for c in cols))
    for r in rows:
        print("  ".join(r.get(c, "").ljust(widths[c]) for c in cols))


def print_csv(rows: list[dict[str, str]]) -> None:
    if not rows:
        return
    cols = list(rows[0].keys())
    writer = csv.DictWriter(sys.stdout, fieldnames=cols)
    writer.writeheader()
    for r in rows:
        writer.writerow(r)


def print_summary(rows: list[dict[str, str]]) -> None:
    if not rows:
        print("(no rows)", file=sys.stderr)
        return
    print(f"Total: {len(rows)} datasets\n")
    print("By source:")
    for k, v in Counter(r.get("source", "") for r in rows).most_common():
        print(f"  {k:20s} {v}")
    print("\nBy status:")
    for k, v in Counter(r.get("status", "") for r in rows).most_common():
        print(f"  {k:20s} {v}")
    print("\nBy license:")
    for k, v in Counter(r.get("license", "") for r in rows).most_common():
        print(f"  {k:20s} {v}")
    # Tag tally
    tag_counter: Counter = Counter()
    for r in rows:
        for t in r.get("tags", "").split(","):
            t = t.strip()
            if t:
                tag_counter[t] += 1
    print("\nTop tags:")
    for k, v in tag_counter.most_common(20):
        print(f"  {k:25s} {v}")


def main() -> int:
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    p.add_argument("--tag", help="filter by tag (exact match, case-insensitive)")
    p.add_argument("--source", help="filter by source (toronto, ontario, statcan, ...)")
    p.add_argument(
        "--status", help="filter by status (active, draft, deprecated, broken)"
    )
    p.add_argument("--license", help="filter by exact license string")
    p.add_argument("--format", dest="format", help="filter by format (csv, json, ...)")
    p.add_argument("--id", help="filter by exact slug")
    p.add_argument(
        "--search",
        help="case-insensitive substring search across id/name/notes/source_id/url",
    )
    p.add_argument(
        "--format-output",
        choices=["table", "csv"],
        default="table",
        help="output format",
    )
    p.add_argument(
        "--summary", action="store_true", help="print counts instead of rows"
    )
    args = p.parse_args()

    if not CATALOG.exists():
        print(f"FATAL: catalog not found at {CATALOG}", file=sys.stderr)
        return 2

    rows = load_rows()
    filtered = [r for r in rows if matches(r, args)]

    if args.summary:
        print_summary(filtered)
    elif args.format_output == "csv":
        print_csv(filtered)
    else:
        print_table(filtered)

    return 0


if __name__ == "__main__":
    sys.exit(main())
