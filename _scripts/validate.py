#!/usr/bin/env python3
"""Validate the catalog CSV, dataset folder structure, and (optionally) URLs.

Run from repo root:
    python _scripts/validate.py                  # catalog + folder consistency
    python _scripts/validate.py --check-urls    # also HEAD-check URLs (slower)
    python _scripts/validate.py --check-folders # only folder consistency

Exit codes:
    0 — all checks passed
    1 — validation errors (printed to stderr)
    2 — runtime error (e.g. CSV missing)

The script is intentionally dependency-light. It uses only the Python stdlib
plus `urllib` for HTTP HEAD requests. If the stdlib import is too painful
for someone, they can rewrite this in 5 minutes.
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
CATALOG = REPO_ROOT / "catalog" / "datasets.csv"
DATASETS_DIR = REPO_ROOT / "datasets"

# Controlled vocabularies. Keep in sync with docs/SCHEMA.md.
SOURCES = {"toronto", "ontario", "statcan", "canada-open-data", "other"}
LICENSES = {"OGL-Ontario", "ODC-BY", "CC-BY", "CC-BY-SA", "CC0"}
LICENSE_PREFIX = "custom:"  # anything starting with this is also allowed
STATUSES = {"active", "draft", "deprecated", "broken"}
FORMATS = {"csv", "json", "geojson", "parquet", "xlsx", "xml", "api", "mixed"}
REFRESH = {
    "hourly",
    "daily",
    "weekly",
    "monthly",
    "quarterly",
    "annual",
    "manual",
    "never",
}
DATA_STORAGE = {"git", "gitignore+fetch", "dvc"}

CANONICAL_TAGS = {
    "transport",
    "transit",
    "active-mobility",
    "health",
    "demographics",
    "environment",
    "climate",
    "energy",
    "infrastructure",
    "housing",
    "safety",
    "economy",
    "education",
}

REQUIRED_COLUMNS = [
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

SLUG_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
ISO_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


class Report:
    """Accumulate errors and warnings, then print a clean report."""

    def __init__(self) -> None:
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def error(self, msg: str) -> None:
        self.errors.append(msg)

    def warn(self, msg: str) -> None:
        self.warnings.append(msg)

    def print(self) -> None:
        if self.warnings:
            print(f"⚠️  {len(self.warnings)} warning(s):", file=sys.stderr)
            for w in self.warnings:
                print(f"  - {w}", file=sys.stderr)
        if self.errors:
            print(f"❌ {len(self.errors)} error(s):", file=sys.stderr)
            for e in self.errors:
                print(f"  - {e}", file=sys.stderr)
        else:
            print("✅ Catalog validation passed.", file=sys.stderr)


def load_catalog() -> tuple[list[str], list[dict[str, str]]]:
    if not CATALOG.exists():
        print(f"FATAL: catalog not found at {CATALOG}", file=sys.stderr)
        sys.exit(2)
    with CATALOG.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None:
            print("FATAL: catalog is empty", file=sys.stderr)
            sys.exit(2)
        missing = [c for c in REQUIRED_COLUMNS if c not in reader.fieldnames]
        if missing:
            print(
                f"FATAL: catalog missing required columns: {missing}", file=sys.stderr
            )
            sys.exit(2)
        rows = list(reader)
    return reader.fieldnames, rows


def validate_row(row: dict[str, str], idx: int, report: Report) -> None:
    """Validate a single catalog row. Errors are accumulated, not raised."""
    row_id = row["id"]
    prefix = f"row {idx} (id={row_id!r})"

    # Slug
    if not row_id:
        report.error(f"{prefix}: id is empty")
    elif not SLUG_RE.match(row_id):
        report.error(f"{prefix}: id {row_id!r} is not kebab-case (a-z, 0-9, -)")

    # Required fields
    for col in (
        "name",
        "source",
        "source_id",
        "url",
        "license",
        "status",
        "added_by",
        "added_on",
    ):
        if not row.get(col, "").strip():
            report.error(f"{prefix}: {col} is required and empty")

    # Source
    if row.get("source") and row["source"] not in SOURCES:
        report.error(
            f"{prefix}: source {row['source']!r} not in {sorted(SOURCES)}. "
            f"Add it in docs/SCHEMA.md and SOURCES in _scripts/validate.py."
        )

    # License
    lic = row.get("license", "")
    if lic and lic not in LICENSES and not lic.startswith(LICENSE_PREFIX):
        report.error(
            f"{prefix}: license {lic!r} not in {sorted(LICENSES)} "
            f"and doesn't start with {LICENSE_PREFIX!r}"
        )

    # Status
    if row.get("status") and row["status"] not in STATUSES:
        report.error(f"{prefix}: status {row['status']!r} not in {sorted(STATUSES)}")

    # Format
    fmt = row.get("format", "")
    if fmt and fmt not in FORMATS:
        report.error(f"{prefix}: format {fmt!r} not in {sorted(FORMATS)}")

    # Refresh
    rf = row.get("refresh_frequency", "")
    if rf and rf not in REFRESH:
        report.error(f"{prefix}: refresh_frequency {rf!r} not in {sorted(REFRESH)}")

    # Data storage
    ds = row.get("data_storage", "")
    if ds and ds not in DATA_STORAGE:
        report.error(
            f"{prefix}: data_storage {ds!r} not in {sorted(DATA_STORAGE)}. "
            f"See docs/DECISIONS.md ADR-009 for the storage strategy."
        )

    # Dates
    for col in ("last_fetched", "last_verified", "added_on"):
        val = row.get(col, "")
        if val and not ISO_DATE_RE.match(val):
            report.error(f"{prefix}: {col} {val!r} is not YYYY-MM-DD")

    # Deprecation
    if row.get("status") == "deprecated" and not row.get("superseded_by"):
        report.warn(f"{prefix}: status=deprecated but superseded_by is empty")

    # Tags
    tags = row.get("tags", "")
    if tags:
        for tag in tags.split(","):
            tag = tag.strip()
            if not tag:
                report.warn(f"{prefix}: empty tag in list")
            elif " " in tag:
                report.warn(f"{prefix}: tag {tag!r} contains a space")
            elif tag != tag.lower():
                report.warn(f"{prefix}: tag {tag!r} is not lowercase")
            elif tag not in CANONICAL_TAGS:
                report.warn(
                    f"{prefix}: tag {tag!r} is not in the canonical tag list "
                    f"(see docs/SCHEMA.md). If this is a new tag, add it to "
                    f"CANONICAL_TAGS in _scripts/validate.py and the table in "
                    f"docs/SCHEMA.md."
                )

    # URL is a URL
    url = row.get("url", "")
    if url and not (url.startswith("http://") or url.startswith("https://")):
        report.error(f"{prefix}: url {url!r} is not http(s)")

    # api_url is a URL if present
    api_url = row.get("api_url", "")
    if api_url and not (
        api_url.startswith("http://") or api_url.startswith("https://")
    ):
        report.error(f"{prefix}: api_url {api_url!r} is not http(s)")

    # Data quality: size_mb should be non-negative
    size_mb = row.get("size_mb", "")
    if size_mb:
        try:
            if float(size_mb) < 0:
                report.warn(f"{prefix}: size_mb is negative ({size_mb})")
        except ValueError:
            report.warn(f"{prefix}: size_mb {size_mb!r} is not a number")

    # Data quality: last_fetched should not be after last_verified
    fetched = row.get("last_fetched", "")
    verified = row.get("last_verified", "")
    if fetched and verified and fetched > verified:
        report.warn(
            f"{prefix}: last_fetched ({fetched}) is after last_verified ({verified}); "
            f"usually fetched <= verified"
        )

    # Data quality: superseded_by should be empty for non-deprecated rows,
    # and should reference a known slug (warning only)
    sup = row.get("superseded_by", "")
    if sup and row.get("status") not in ("deprecated", "broken"):
        report.warn(
            f"{prefix}: superseded_by is set but status is {row.get('status')!r}"
        )


def check_folder_consistency(rows: list[dict[str, str]], report: Report) -> None:
    """Each row's id should have a folder, and each folder should have a row."""
    csv_ids = {row["id"] for row in rows if row["id"]}

    # Skip the example file
    folder_ids: set[str] = set()
    if DATASETS_DIR.exists():
        for p in DATASETS_DIR.iterdir():
            if p.is_dir() and not p.name.startswith(".") and not p.name.startswith("_"):
                if SLUG_RE.match(p.name):
                    folder_ids.add(p.name)
                else:
                    report.warn(f"folder {p.name!r} is not a valid slug")

    # Folders without CSV rows
    for fid in sorted(folder_ids - csv_ids):
        report.error(f"folder datasets/{fid}/ has no matching row in catalog")

    # CSV rows without folders (warning, not error, for broken/legacy)
    for cid in sorted(csv_ids - folder_ids):
        row = next(r for r in rows if r["id"] == cid)
        if row.get("status") == "broken":
            report.warn(
                f"row {cid!r} is status=broken with no folder "
                f"— ensure this is intentional"
            )
        else:
            report.error(f"row {cid!r} has no matching folder datasets/{cid}/")

    # Required files per folder
    for fid in sorted(folder_ids):
        folder = DATASETS_DIR / fid
        readme = folder / "README.md"
        if not readme.exists():
            report.error(f"folder datasets/{fid}/ missing README.md")
        # If raw/ exists, SOURCE.md should too
        raw = folder / "raw"
        if raw.exists() and any(raw.iterdir()):
            source = raw / "SOURCE.md"
            if not source.exists():
                report.warn(
                    f"folder datasets/{fid}/raw/ has files but no SOURCE.md "
                    f"(provenance required)"
                )

    # Cross-check SOURCE.md snapshot dates against catalog last_verified
    for row in rows:
        dataset_id = row.get("id", "")
        if not dataset_id:
            continue
        raw_source = DATASETS_DIR / dataset_id / "raw" / "SOURCE.md"
        if not raw_source.exists():
            continue
        source_text = raw_source.read_text(encoding="utf-8")
        snapshot_date = None
        for line in source_text.splitlines():
            m = re.match(
                r"\s*[-*]\s*\*?\*?Snapshot date:?\*?\*?\s*(\d{4}-\d{2}-\d{2})",
                line,
                re.IGNORECASE,
            )
            if m:
                snapshot_date = m.group(1)
                break
        if not snapshot_date:
            continue
        last_verified = row.get("last_verified", "").strip()
        if last_verified and snapshot_date != last_verified:
            report.warn(
                f"row id={dataset_id!r}: SOURCE.md snapshot date "
                f"({snapshot_date}) differs from catalog last_verified "
                f"({last_verified})"
            )

    # Cross-check superseded_by references a known slug
    all_ids = {row["id"] for row in rows if row.get("id")}
    for row in rows:
        sup = row.get("superseded_by", "").strip()
        if sup and sup not in all_ids:
            report.warn(
                f"row id={row.get('id', '?')!r}: superseded_by {sup!r} "
                f"does not match any catalog id"
            )


def head_check(url: str, timeout: int = 10) -> tuple[bool, str]:
    """HEAD-check a URL. Returns (ok, message)."""
    if not url:
        return True, "empty url"
    req = urllib.request.Request(url, method="HEAD")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            code = resp.status
            if 200 <= code < 400:
                return True, f"HTTP {code}"
            return False, f"HTTP {code}"
    except urllib.error.HTTPError as e:
        # 405 = method not allowed; try GET as a fallback
        if e.code in (405, 403):
            try:
                req2 = urllib.request.Request(url, method="GET")
                with urllib.request.urlopen(req2, timeout=timeout) as resp2:
                    return True, f"HTTP {resp2.status} (GET fallback)"
            except Exception as e2:
                return False, f"GET fallback failed: {e2}"
        return False, f"HTTPError: {e.code}"
    except urllib.error.URLError as e:
        return False, f"URLError: {e.reason}"
    except Exception as e:
        return False, f"{type(e).__name__}: {e}"


def check_urls(
    rows: list[dict[str, str]], max_urls: int | None, report: Report
) -> None:
    print(f"Checking URLs (max={max_urls or 'all'})…", file=sys.stderr)
    checked = 0
    for idx, row in enumerate(rows, start=2):  # row 1 is header
        url = row.get("url", "").strip()
        if not url:
            continue
        ok, msg = head_check(url)
        checked += 1
        prefix = f"row {idx} (id={row['id']!r})"
        if ok:
            print(f"  ✓ {row['id']:35s} {url}  [{msg}]", file=sys.stderr)
        else:
            report.error(f"{prefix}: url {url} unreachable: {msg}")
        if max_urls and checked >= max_urls:
            break


def csv_lint(report: Report) -> None:
    """Low-level CSV structure checks that catch common editing mistakes.

    These catch problems that csv.DictReader silently tolerates: unquoted
    commas, inconsistent quoting, wrong column count, and trailing whitespace.
    """
    if not CATALOG.exists():
        return
    with CATALOG.open(newline="", encoding="utf-8") as f:
        lines = f.readlines()

    if not lines:
        report.error("catalog/datasets.csv is empty")
        return

    header = lines[0].rstrip("\n")
    num_cols = header.count(",") + 1

    for lineno, line in enumerate(lines, start=1):
        stripped = line.rstrip("\n")

        # Blank lines inside CSV are almost always a mistake
        if stripped == "" and lineno < len(lines):
            report.warn(f"line {lineno}: blank line in CSV")
            continue

        # Trailing whitespace
        if stripped != stripped.rstrip():
            report.warn(f"line {lineno}: trailing whitespace")

        # Column count: count commas outside quoted fields
        in_quotes = False
        comma_count = 0
        for ch in stripped:
            if ch == '"':
                in_quotes = not in_quotes
            elif ch == "," and not in_quotes:
                comma_count += 1

        if comma_count != num_cols - 1:
            report.error(
                f"line {lineno}: expected {num_cols} columns "
                f"(found {comma_count + 1}). "
                f"Check for unquoted commas in {('tags', 'notes', 'name') if comma_count > num_cols - 1 else ('url', 'api_url')}."
            )

    # Also check that every value in non-tag fields is free of
    # unquoted commas (tags use commas as delimiters and should be quoted)
    _, rows = load_catalog()
    comma_safe = {"tags"}
    for idx, row in enumerate(rows, start=2):
        for col in REQUIRED_COLUMNS:
            if col in comma_safe:
                continue
            val = row.get(col, "")
            if "," in val:
                report.warn(
                    f"row {idx} (id={row.get('id', '?')}): "
                    f"column {col!r} contains a comma — "
                    f"should be quoted in the CSV"
                )


def main() -> int:
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    p.add_argument(
        "--check-urls", action="store_true", help="HEAD-check the `url` column"
    )
    p.add_argument(
        "--check-folders", action="store_true", help="only check folder consistency"
    )
    p.add_argument(
        "--csv-lint", action="store_true", help="run low-level CSV structure checks"
    )
    p.add_argument(
        "--max-urls", type=int, default=None, help="cap URL checks (default: all)"
    )
    p.add_argument(
        "--report", type=Path, default=None, help="write a markdown report to this path"
    )
    args = p.parse_args()

    report = Report()

    if args.check_folders:
        # Minimal load for folder check
        _, rows = load_catalog()
        check_folder_consistency(rows, report)
    else:
        _header, rows = load_catalog()
        # CSV structure check (always runs in full validation)
        csv_lint(report)
        for idx, row in enumerate(rows, start=2):
            validate_row(row, idx, report)
        # Slug uniqueness
        seen: dict[str, int] = {}
        for idx, row in enumerate(rows, start=2):
            rid = row["id"]
            if rid in seen:
                report.error(
                    f"row {idx} (id={rid!r}): duplicate id (also at row {seen[rid]})"
                )
            else:
                seen[rid] = idx
        check_folder_consistency(rows, report)

    if args.check_urls:
        check_urls(rows, args.max_urls, report)

    if args.report:
        with args.report.open("w", encoding="utf-8") as f:
            f.write("# Validation report\n\n")
            f.write(f"- Errors: {len(report.errors)}\n")
            f.write(f"- Warnings: {len(report.warnings)}\n\n")
            if report.errors:
                f.write("## Errors\n\n")
                for e in report.errors:
                    f.write(f"- {e}\n")
                f.write("\n")
            if report.warnings:
                f.write("## Warnings\n\n")
                for w in report.warnings:
                    f.write(f"- {w}\n")

    report.print()
    return 1 if report.errors else 0


if __name__ == "__main__":
    sys.exit(main())
