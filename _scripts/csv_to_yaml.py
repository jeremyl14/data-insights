#!/usr/bin/env python3
"""Convert catalog/datasets.csv to per-dataset YAML files.

This is a one-way converter for the planned migration from a single CSV
to per-dataset YAML front-matter (see docs/CONCERNS.md). It produces
one YAML file per dataset row in datasets/<slug>/catalog.yaml.

Usage:
    python3 _scripts/csv_to_yaml.py --dry-run    # preview without writing
    python3 _scripts/csv_to_yaml.py               # write files

The CSV remains the source of truth until the migration is complete.
After migration, the CSV will be generated from the YAML files as a
build artifact.
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
CATALOG = REPO_ROOT / "catalog" / "datasets.csv"
DATASETS_DIR = REPO_ROOT / "datasets"

# Order matters for readability; these go first in the YAML output.
FIELD_ORDER = [
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
    "data_storage",
    "status",
    "added_by",
    "added_on",
    "superseded_by",
    "notes",
]


def csv_to_yaml_rows(rows: list[dict[str, str]]) -> list[str]:
    lines: list[str] = []
    for row in rows:
        lines.append("---")
        for field in FIELD_ORDER:
            val = row.get(field, "")
            if val:
                if field == "tags":
                    lines.append(f"{field}:")
                    for tag in val.split(","):
                        tag = tag.strip()
                        if tag:
                            lines.append(f"  - {tag}")
                elif any(c in val for c in (":", "#", "'", '"', "\n")):
                    escaped = val.replace("'", "''")
                    lines.append(f"{field}: '{escaped}'")
                else:
                    lines.append(f"{field}: {val}")
            # Skip empty fields for cleaner output
        lines.append("---")
        lines.append("")
    return lines


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="print YAML to stdout without writing files",
    )
    args = p.parse_args()

    if not CATALOG.exists():
        print(f"FATAL: {CATALOG} not found", file=sys.stderr)
        return 2

    with CATALOG.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    if args.dry_run:
        for line in csv_to_yaml_rows(rows):
            print(line)
        return 0

    written = 0
    for row in rows:
        slug = row.get("id", "")
        if not slug:
            continue
        dest = DATASETS_DIR / slug / "catalog.yaml"
        dest.parent.mkdir(parents=True, exist_ok=True)
        yaml_lines = csv_to_yaml_rows([row])
        dest.write_text("\n".join(yaml_lines), encoding="utf-8")
        written += 1
        print(f"  wrote {dest}")

    print(f"\nConverted {written} dataset(s) to YAML.")
    print("The CSV is still the source of truth. Commit the YAML files")
    print("when ready to switch, then update the scripts to read YAML.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
