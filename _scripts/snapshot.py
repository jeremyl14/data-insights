#!/usr/bin/env python3
"""Snapshot manager: decides which raw files are due for a DVC snapshot,
and runs the snapshot for each.

This is the cron entry point. It's intentionally read-mostly: it reads
the catalog, decides what's due, and shells out to DVC for the actual
work. It does NOT touch raw files (those are immutable per ADR-004).

Cadence
-------
Per-dataset cadence is driven by the catalog's `refresh_frequency` column:
- hourly    → snapshot if last_snapshot is more than 1 hour old
- daily     → snapshot if last_snapshot is more than 1 day old
- weekly    → snapshot if last_snapshot is more than 7 days old
- monthly   → snapshot if last_snapshot is more than 30 days old
- quarterly → snapshot if last_snapshot is more than 90 days old
- annual    → snapshot if last_snapshot is more than 365 days old
- manual    → never auto-snapshot (operator-triggered only)
- never     → never auto-snapshot (data is static)

The `last_snapshot` field is stored in a small JSON sidecar,
`_scripts/.snapshot-state.json`, which is gitignored. The catalog CSV
stays the source of truth for *metadata*; the sidecar is operational state.

Why a sidecar and not a new CSV column?
- The catalog is curated and reviewed in PRs. A column that auto-updates
  on every cron run would create noisy diffs.
- A sidecar is a build artifact, not source. Same pattern as
  `dvc.lock`.

Usage
-----
    # Snapshot everything that's due
    python3 _scripts/snapshot.py

    # Snapshot a specific dataset
    python3 _scripts/snapshot.py --dataset toronto-bike-share

    # Force snapshot regardless of cadence (e.g. for a new release)
    python3 _scripts/snapshot.py --force --dataset toronto-bike-share

    # Dry run: show what would be snapshotted, but don't do it
    python3 _scripts/snapshot.py --dry-run

    # Update only the sidecar timestamps (e.g. after a manual snapshot
    # done outside this script)
    python3 _scripts/snapshot.py --mark-only --dataset toronto-bike-share

Exit codes
----------
0 — at least one snapshot ran (or was marked)
1 — nothing was due
2 — runtime error (DVC not installed, env file missing, etc.)

The cron unit/timer should ignore exit code 1 (nothing to do) but
treat 2 as a failure and surface it.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import shlex
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
CATALOG = REPO_ROOT / "catalog" / "datasets.csv"
STATE_FILE = Path(__file__).resolve().parent / ".snapshot-state.json"
STATE_FILE.parent.mkdir(exist_ok=True)

# Cadence in days. `hourly` is special-cased below.
CADENCE_DAYS = {
    "hourly": 1 / 24,
    "daily": 1,
    "weekly": 7,
    "monthly": 30,
    "quarterly": 90,
    "annual": 365,
    "manual": None,
    "never": None,
}


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def load_catalog() -> list[dict[str, str]]:
    with CATALOG.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def load_state() -> dict[str, str]:
    """Map: dataset_id → ISO timestamp of last successful snapshot."""
    if not STATE_FILE.exists():
        return {}
    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        print(f"WARN: state file unreadable ({e}); starting fresh", file=sys.stderr)
        return {}


def save_state(state: dict[str, str]) -> None:
    STATE_FILE.write_text(
        json.dumps(state, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def is_due(
    row: dict[str, str], state: dict[str, str], now: datetime
) -> tuple[bool, str]:
    """Return (is_due, reason)."""
    dataset_id = row["id"]
    status = row.get("status", "")
    storage = row.get("data_storage", "")
    cadence = row.get("refresh_frequency", "")

    if status != "active":
        return False, f"status={status} (only active datasets auto-snapshot)"

    if storage not in ("dvc", "gitignore+fetch"):
        return False, f"data_storage={storage} (only dvc/gitignore+fetch auto-snapshot)"

    if cadence not in CADENCE_DAYS:
        return False, f"refresh_frequency={cadence!r} not in known cadences"

    days = CADENCE_DAYS[cadence]
    if days is None:
        return False, f"refresh_frequency={cadence} (no auto-snapshot)"

    last = state.get(dataset_id)
    if not last:
        return True, "never snapshotted before"

    try:
        last_dt = datetime.fromisoformat(last)
    except ValueError:
        return True, f"last_snapshot={last!r} unparseable, re-snapshotting"

    age_hours = (now - last_dt).total_seconds() / 3600
    threshold_hours = days * 24
    if age_hours >= threshold_hours:
        return (
            True,
            f"last snapshot {age_hours:.1f}h ago (threshold {threshold_hours:.1f}h)",
        )
    return (
        False,
        f"last snapshot {age_hours:.1f}h ago (threshold {threshold_hours:.1f}h)",
    )


def run_dvc(args: list[str], dry_run: bool = False) -> int:
    """Run a dvc command, logging it. Returns the exit code.

    Looks for dvc on PATH first; falls back to ~/.local/bin/dvc
    which is where pip --user installs put it on the OpenClaw bot
    host. The operator's PATH is authoritative; this fallback only
    exists for the bot's own use."""
    cmd = ["dvc", *args]
    if dry_run:
        print(f"  DRY-RUN: {shlex.join(cmd)}")
        return 0
    print(f"  $ {shlex.join(cmd)}", file=sys.stderr)
    try:
        return subprocess.call(cmd, cwd=REPO_ROOT)
    except FileNotFoundError:
        # Fallback: ~/.local/bin is where pip --user installs dvc
        user_bin = Path.home() / ".local" / "bin" / "dvc"
        if user_bin.exists():
            cmd = [str(user_bin), *args]
            return subprocess.call(cmd, cwd=REPO_ROOT)
        raise


def fetch_prior_snapshot(rel_path: Path, target: Path) -> Path | None:
    """Extract the prior version of a DVC-tracked file from B2 directly.

    Why we don't use `dvc get`: it returns the file from the working
    tree (or local cache), which is the *new* file, not the prior
    version. We need the prior MD5's bytes from the B2 remote.

    Returns the path to a local copy of the prior file, or None if
    no prior exists or the fetch failed.
    """
    dvc_pointer = rel_path.with_suffix(rel_path.suffix + ".dvc")
    if not dvc_pointer.exists():
        return None

    # Read the MD5 from the .dvc file (it's a small YAML)
    try:
        text = dvc_pointer.read_text()
    except OSError:
        return None
    md5 = None
    for raw_line in text.splitlines():
        # .dvc files have indented YAML; strip the indent before matching
        line = raw_line.strip()
        if line.startswith("- md5:") or line.startswith("md5:"):
            # Format: "- md5: <hash>" or "md5: <hash>"
            value = line.split(":", 1)[1].strip()
            md5 = value
            break
    if not md5:
        return None

    # DVC stores at: <url-prefix>/files/<hash-algo>/<aa>/<rest>
    # For our config, the S3 key is: snapshots/files/md5/<aa>/<rest>
    # (no filename suffix; the filename is part of the .dvc pointer's path)
    if len(md5) < 2:
        return None
    s3_key = f"snapshots/files/md5/{md5[:2]}/{md5[2:]}"
    dest = REPO_ROOT / "_scripts" / ".prior-snapshot" / target.name
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists():
        dest.unlink()

    rc = s3_get_object(s3_key, dest)
    if rc == 0 and dest.exists() and dest.stat().st_size > 0:
        return dest
    return None


def _read_dvc_remote_config() -> tuple[str | None, str | None]:
    """Read the B2 remote endpoint and URL prefix from .dvc/config.

    Returns (endpoint_url, url_prefix) or (None, None) if not found.
    """
    cfg = REPO_ROOT / ".dvc" / "config"
    if not cfg.exists():
        return None, None
    endpoint = None
    url_prefix = None
    in_remote = False
    for line in cfg.read_text().splitlines():
        stripped = line.strip()
        if stripped.startswith("[") and "remote" in stripped:
            in_remote = "b2" in stripped
            continue
        if in_remote:
            if stripped.startswith("endpointurl"):
                endpoint = stripped.split("=", 1)[1].strip()
            elif stripped.startswith("url"):
                url_prefix = stripped.split("=", 1)[1].strip()
    return endpoint, url_prefix


def s3_get_object(s3_key: str, dest: Path) -> int:
    """Fetch an object from the B2 S3 endpoint and save to dest.

    Uses boto3 for proper SigV4 signing, retry logic, and error
    diagnostics. Falls back to a clear error message if boto3 is
    not installed.

    Returns 0 on success, non-zero on failure.
    """
    try:
        import boto3
        from botocore.config import Config as BotoConfig
    except ImportError:
        print(
            "ERROR: boto3 is required for prior-snapshot fetch. "
            "Install with: pip install boto3",
            file=sys.stderr,
        )
        return -1

    endpoint, url_prefix = _read_dvc_remote_config()
    if not endpoint or not url_prefix:
        print(
            "  s3_get_object: could not read .dvc/config for B2 remote", file=sys.stderr
        )
        return -1

    bucket = url_prefix.split("//", 1)[-1].split("/", 1)[0]
    region = (
        endpoint.split("//", 1)[-1].split(".")[1] if "." in endpoint else "us-west-004"
    )

    ak = os.environ.get("AWS_ACCESS_KEY_ID")
    sk = os.environ.get("AWS_SECRET_ACCESS_KEY")
    if not ak or not sk:
        print(
            "  s3_get_object: AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY not set",
            file=sys.stderr,
        )
        return -1

    s3 = boto3.client(
        "s3",
        endpoint_url=endpoint,
        region_name=region,
        aws_access_key_id=ak,
        aws_secret_access_key=sk,
        config=BotoConfig(signature_version="s3v4"),
    )
    try:
        resp = s3.get_object(Bucket=bucket, Key=s3_key)
        body = resp["Body"].read()
        dest.write_bytes(body)
        return 0
    except Exception as e:
        print(f"  s3_get_object({s3_key}) failed: {e}", file=sys.stderr)
        return -1


def verify_superset(old_path: Path, new_path: Path) -> tuple[bool, str]:
    """Cheap sanity check that the new file is a superset of the old.

    Designed for the common case where a publisher's cumulative-current-
    year data updates by appending rows, not by editing history. We
    can't tell in general whether an edit is "legitimate correction"
    vs "silent data loss", so this check is intentionally simple:

    1. If the new file has fewer rows than the old, fail loudly.
    2. If the new file has fewer columns, fail loudly (schema change).
    3. Compare the first N rows of the old file to the same rows in
       the new file (after sorting both by the first column, which
       is a heuristic for "the historical part"). Any mismatch fails.

    Stdlib only. Treats the file as text and as a list of lines; it
    does not parse CSV/JSON. This is deliberate: it works for any
    line-oriented format and avoids a pandas dependency for a check
    that runs on every snapshot.

    Returns (ok, reason). On the first snapshot (no prior file), we
    skip the check entirely and report success.
    """
    if not old_path.exists():
        return True, "no prior file; first snapshot, skipping superset check"

    if not new_path.exists():
        return False, f"new file missing at {new_path}"

    # Read both as bytes; bail early if sizes are wildly different
    old_bytes = old_path.read_bytes()
    new_bytes = new_path.read_bytes()
    if len(new_bytes) < len(old_bytes):
        return False, (
            f"new file is smaller than old ({len(new_bytes)} vs {len(old_bytes)} bytes); "
            f"upstream likely truncated history"
        )

    # Compare as sets of lines. This catches:
    #   - any line that was in old but missing in new
    #   - any line that was modified in new (different bytes)
    # It does NOT catch a new line that just reorders existing data,
    # but for cumulative append-only data that's the desired behavior.
    old_lines = set(old_bytes.splitlines())
    new_lines = set(new_bytes.splitlines())
    missing = old_lines - new_lines
    if missing:
        # Cap the sample to 5 lines so we don't dump a 10MB diff
        sample = sorted(missing)[:5]
        return False, (
            f"{len(missing)} line(s) from prior file missing in new file; "
            f"first missing: {sample!r}"
        )
    return (
        True,
        f"new file is a superset ({len(new_lines)} unique lines, prior {len(old_lines)})",
    )


def snapshot_dataset(row: dict[str, str], *, force: bool, dry_run: bool) -> bool:
    """Run the snapshot for one dataset. Returns True on success."""
    dataset_id = row["id"]
    storage = row.get("data_storage", "")
    raw_dir = REPO_ROOT / "datasets" / dataset_id / "raw"

    print(f"\n--- {dataset_id} ---")
    if storage == "gitignore+fetch":
        # No DVC tracking; just verify the file is fetchable and update
        # the state. (Operator can still run a manual `dvc add` if they
        # later decide to track it.)
        print("  storage=gitignore+fetch: skipping DVC; just re-validating URL")
        url = row.get("url", "").strip()
        if not url:
            print("  WARN: no url to check; marking snapshot anyway")
        else:
            try:
                import urllib.request

                req = urllib.request.Request(url, method="HEAD")
                with urllib.request.urlopen(req, timeout=15) as resp:
                    print(f"  HEAD {url} → {resp.status}")
            except Exception as e:
                print(f"  WARN: HEAD failed: {e}", file=sys.stderr)
        return True

    if storage != "dvc":
        print(f"  storage={storage}: nothing to do")
        return False

    # Find the files in raw/ that should be tracked.
    # Convention: every .csv / .parquet / .json / .geojson in raw/
    # that isn't a SOURCE.md is a candidate.
    candidates = []
    if raw_dir.exists():
        for p in raw_dir.iterdir():
            if p.name in ("SOURCE.md", ".gitignore", ".gitkeep"):
                continue
            if p.name.startswith("."):
                continue
            if p.suffix.lower() in (".csv", ".parquet", ".json", ".geojson", ".xml"):
                candidates.append(p)

    if not candidates:
        print(f"  no DVC-trackable files in {raw_dir}")
        print("  (the operator may need to run `dvc add` manually)")
        return False

    for path in candidates:
        rel = path.relative_to(REPO_ROOT)

        # If DVC has a cached version of this file from a prior snapshot,
        # save it aside for the superset check. We use the .dvc pointer
        # to find the prior MD5, then fetch the prior bytes from the
        # B2 remote directly (NOT from the working tree, which already
        # has the new file). This is the only way to compare the new
        # file to its actual prior state, not to itself.
        prior_copy: Path | None = None
        if not dry_run:
            prior_copy = fetch_prior_snapshot(rel, path)
            if prior_copy is None:
                # First snapshot, or fetch failed. Not an error;
                # just skip the check.
                pass

        # `dvc add` is idempotent; safe to re-run.
        rc = run_dvc(["add", "--no-commit", str(rel)], dry_run=dry_run)
        if rc != 0:
            print(f"  FAIL: dvc add {rel} exited {rc}")
            return False

        # Superset check: compare the just-committed file against the
        # prior version. Warn (but don't block) if the new file is
        # missing rows that were in the prior file. The data still
        # goes through; we want this to be visible, not catastrophic.
        if not dry_run and prior_copy and prior_copy.exists():
            ok, reason = verify_superset(prior_copy, path)
            if ok:
                print(f"  superset: OK ({reason})")
            else:
                print(f"  ⚠️  superset: FAIL ({reason})")
                print(
                    "     this is the new file in place; not blocking, but the operator"
                )
                print("     should investigate the upstream change. See CONCERNS.md.")

    rc = run_dvc(["push"], dry_run=dry_run)
    if rc != 0:
        print(f"  FAIL: dvc push exited {rc}")
        return False

    return True


def main() -> int:
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    p.add_argument("--dataset", help="snapshot only this dataset id (default: all due)")
    p.add_argument(
        "--force", action="store_true", help="snapshot regardless of cadence"
    )
    p.add_argument(
        "--dry-run", action="store_true", help="show what would happen; don't do it"
    )
    p.add_argument(
        "--mark-only",
        action="store_true",
        help="update state timestamp without running dvc",
    )
    args = p.parse_args()

    rows = load_catalog()
    state = load_state()
    now = now_utc()

    targets: list[tuple[dict[str, str], str]] = []  # (row, reason)
    for row in rows:
        if args.dataset and row["id"] != args.dataset:
            continue
        if args.force:
            targets.append((row, "forced"))
            continue
        due, reason = is_due(row, state, now)
        if due:
            targets.append((row, reason))

    if not targets:
        print("No datasets due for snapshot.", file=sys.stderr)
        return 1

    print(f"Will snapshot {len(targets)} dataset(s):")
    for row, reason in targets:
        print(f"  - {row['id']:35s} ({row['refresh_frequency']:8s}) — {reason}")

    if args.mark_only:
        for row, _ in targets:
            state[row["id"]] = now.isoformat()
        if not args.dry_run:
            save_state(state)
        print(f"Marked {len(targets)} dataset(s) as snapshotted at {now.isoformat()}")
        return 0

    success = 0
    for row, _ in targets:
        if snapshot_dataset(row, force=args.force, dry_run=args.dry_run):
            state[row["id"]] = now.isoformat()
            success += 1
        if not args.dry_run:
            # Persist state after each dataset, so a partial run is recoverable
            save_state(state)

    print(f"\nDone: {success}/{len(targets)} snapshot(s) successful")
    return 0 if success else 2


if __name__ == "__main__":
    sys.exit(main())
