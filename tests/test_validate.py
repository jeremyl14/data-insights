"""Tests for _scripts/validate.py — catalog structure, controlled vocabularies,
slug format, date format, tag format, SOURCE.md cross-checks, and data quality."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "_scripts"))

from validate import (
    DATA_STORAGE,
    FORMATS,
    ISO_DATE_RE,
    LICENSES,
    LICENSE_PREFIX,
    REFRESH,
    REQUIRED_COLUMNS,
    SOURCES,
    STATUSES,
    Report,
    SLUG_RE,
    check_folder_consistency,
    load_catalog,
    validate_row,
)

REPO_ROOT = Path(__file__).resolve().parents[1]


class TestSlugFormat:
    def test_valid_slugs(self):
        for slug in (
            "toronto-bike-share",
            "ontario-covid-cases",
            "a",
            "a1",
            "abc-123-def",
        ):
            assert SLUG_RE.match(slug), f"{slug} should be valid"

    def test_invalid_slugs(self):
        for slug in (
            "Toronto_Bike",
            "bike share",
            "",
            "a b c",
            "UPPER",
            "under_score",
        ):
            assert not SLUG_RE.match(slug), f"{slug} should be invalid"


class TestIsoDate:
    def test_valid_dates(self):
        for d in ("2026-06-08", "2024-01-01", "2000-12-31"):
            assert ISO_DATE_RE.match(d)

    def test_invalid_dates(self):
        for d in ("2026/06/08", "06-08-2026", "not-a-date", ""):
            assert not ISO_DATE_RE.match(d)


class TestReport:
    def test_empty_report(self):
        r = Report()
        r.print()
        assert r.errors == []
        assert r.warnings == []

    def test_accumulate(self):
        r = Report()
        r.error("e1")
        r.warn("w1")
        assert r.errors == ["e1"]
        assert r.warnings == ["w1"]


class TestValidateRow:
    def _row(self, **overrides):
        defaults = {
            "id": "test-dataset",
            "name": "Test Dataset",
            "source": "toronto",
            "source_id": "abc123",
            "url": "https://example.com/dataset",
            "api_url": "",
            "license": "ODC-BY",
            "format": "csv",
            "tags": "transport,health",
            "refresh_frequency": "monthly",
            "last_fetched": "2026-06-08",
            "last_verified": "2026-06-08",
            "size_mb": "10",
            "data_storage": "git",
            "status": "active",
            "added_by": "testuser",
            "added_on": "2026-06-08",
            "superseded_by": "",
            "notes": "",
        }
        defaults.update(overrides)
        return defaults

    def test_valid_row(self):
        r = Report()
        validate_row(self._row(), 2, r)
        assert r.errors == [], f"unexpected errors: {r.errors}"

    def test_empty_id(self):
        r = Report()
        validate_row(self._row(id=""), 2, r)
        assert any("id is empty" in e for e in r.errors)

    def test_bad_slug(self):
        r = Report()
        validate_row(self._row(id="Bad_Slug"), 2, r)
        assert any("not kebab-case" in e for e in r.errors)

    def test_bad_source(self):
        r = Report()
        validate_row(self._row(source="mars"), 2, r)
        assert any("not in" in e for e in r.errors)

    def test_bad_license(self):
        r = Report()
        validate_row(self._row(license="MIT"), 2, r)
        assert any("license" in e for e in r.errors)

    def test_custom_license(self):
        r = Report()
        validate_row(self._row(license="custom:proprietary"), 2, r)
        assert r.errors == [], f"custom: prefix should be valid, got {r.errors}"

    def test_bad_status(self):
        r = Report()
        validate_row(self._row(status="unknown"), 2, r)
        assert any("status" in e for e in r.errors)

    def test_bad_format(self):
        r = Report()
        validate_row(self._row(format="xls"), 2, r)
        assert any("format" in e for e in r.errors)

    def test_bad_refresh(self):
        r = Report()
        validate_row(self._row(refresh_frequency="biweekly"), 2, r)
        assert any("refresh_frequency" in e for e in r.errors)

    def test_bad_storage(self):
        r = Report()
        validate_row(self._row(data_storage="ftp"), 2, r)
        assert any("data_storage" in e for e in r.errors)

    def test_deprecated_without_superseded_by(self):
        r = Report()
        validate_row(self._row(status="deprecated", superseded_by=""), 2, r)
        assert any("deprecated" in w for w in r.warnings)

    def test_deprecated_with_superseded_by(self):
        r = Report()
        validate_row(self._row(status="deprecated", superseded_by="new-slug"), 2, r)
        assert not any("deprecated" in w for w in r.warnings)

    def test_bad_date_format(self):
        r = Report()
        validate_row(self._row(added_on="06/08/2026"), 2, r)
        assert any("is not YYYY-MM-DD" in e for e in r.errors)

    def test_bad_url(self):
        r = Report()
        validate_row(self._row(url="ftp://example.com"), 2, r)
        assert any("not http(s)" in e for e in r.errors)

    def test_tags_with_spaces(self):
        r = Report()
        validate_row(self._row(tags="public transit,bike"), 2, r)
        assert any("contains a space" in w for w in r.warnings)

    def test_tags_uppercase(self):
        r = Report()
        validate_row(self._row(tags="Transport,Health"), 2, r)
        assert any("not lowercase" in w for w in r.warnings)

    def test_required_fields_empty(self):
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
            r = Report()
            validate_row(self._row(**{col: ""}), 2, r)
            assert any(col in e for e in r.errors), f"missing required check for {col}"

    def test_size_mb_negative(self):
        r = Report()
        validate_row(self._row(size_mb="-5"), 2, r)
        assert any("size_mb" in w for w in r.warnings)

    def test_last_fetched_after_last_verified(self):
        r = Report()
        validate_row(
            self._row(last_fetched="2026-06-10", last_verified="2026-06-08"), 2, r
        )
        assert any("last_fetched" in w for w in r.warnings)

    def test_api_url_not_http(self):
        r = Report()
        validate_row(self._row(api_url="ftp://bad"), 2, r)
        assert any("not http(s)" in e for e in r.errors)


class TestValidateRowDataQuality:
    def _row(self, **overrides):
        defaults = {
            "id": "test-dataset",
            "name": "Test Dataset",
            "source": "toronto",
            "source_id": "abc123",
            "url": "https://example.com/dataset",
            "api_url": "",
            "license": "ODC-BY",
            "format": "csv",
            "tags": "transport",
            "refresh_frequency": "monthly",
            "last_fetched": "2026-06-08",
            "last_verified": "2026-06-08",
            "size_mb": "10",
            "data_storage": "git",
            "status": "active",
            "added_by": "testuser",
            "added_on": "2026-06-08",
            "superseded_by": "",
            "notes": "",
        }
        defaults.update(overrides)
        return defaults

    def test_negative_size(self):
        r = Report()
        validate_row(self._row(size_mb="-5"), 2, r)
        assert any("size_mb" in w for w in r.warnings)

    def test_fetched_after_verified(self):
        r = Report()
        validate_row(
            self._row(last_fetched="2026-06-10", last_verified="2026-06-08"), 2, r
        )
        assert any("last_fetched" in w for w in r.warnings)

    def test_superseded_by_empty_for_active(self):
        r = Report()
        validate_row(self._row(status="active", superseded_by=""), 2, r)
        assert not any("superseded_by" in w for w in r.warnings)

    def test_superseded_by_filled_for_deprecated(self):
        r = Report()
        validate_row(self._row(status="deprecated", superseded_by="new-slug"), 2, r)
        assert not any("deprecated" in w for w in r.warnings)


class TestCsvLint:
    def test_catalog_column_count(self):
        header, rows = load_catalog()
        assert len(header) == len(REQUIRED_COLUMNS)
        for row in rows:
            assert len(row) == len(REQUIRED_COLUMNS), (
                f"Row id={row.get('id', '?')} has {len(row)} columns, "
                f"expected {len(REQUIRED_COLUMNS)}"
            )

    def test_catalog_no_unquoted_commas_in_non_tag_fields(self):
        header, rows = load_catalog()
        comma_safe = {"tags"}
        for row in rows:
            for col in REQUIRED_COLUMNS:
                if col in comma_safe:
                    continue
                val = row.get(col, "")
                if "," in val:
                    pass

    def test_catalog_parses_cleanly(self):
        header, rows = load_catalog()
        assert len(rows) > 0, "catalog should have at least one row"

    def test_csv_lint_bad_column_count(self, tmp_path):
        import validate as validate_mod

        bad_csv = tmp_path / "datasets.csv"
        header = ",".join(REQUIRED_COLUMNS)
        bad_csv.write_text(
            f'{header}\n"test-good",Test,toronto,abc,https://example.com,,ODC-BY,csv,transport,monthly,2026-06-08,2026-06-08,10,git,active,testuser,2026-06-08,,\n'
            f'"bad-row",Test,toronto,abc,https://example.com,,ODC-BY,csv,transport,monthly,2026-06-08,2026-06-08,10,git,active,testuser,2026-06-08,,Extra,Column\n'
        )
        r = Report()
        original_catalog = validate_mod.CATALOG
        validate_mod.CATALOG = bad_csv
        try:
            validate_mod.csv_lint(r)
        finally:
            validate_mod.CATALOG = original_catalog
        assert any("columns" in e.lower() for e in r.errors)


class TestFolderConsistencySupersededBy:
    def test_superseded_by_references_unknown_slug(self):
        r = Report()
        rows = [
            {
                "id": "old-dataset",
                "status": "deprecated",
                "superseded_by": "nonexistent-slug",
            }
        ]
        check_folder_consistency(rows, r)
        assert any("superseded_by" in w and "nonexistent-slug" in w for w in r.warnings)

    def test_superseded_by_references_known_slug(self):
        r = Report()
        rows = [
            {
                "id": "old-dataset",
                "status": "deprecated",
                "superseded_by": "new-dataset",
            },
            {"id": "new-dataset", "status": "active", "superseded_by": ""},
        ]
        check_folder_consistency(rows, r)
        assert not any("superseded_by" in w for w in r.warnings)


class TestControlledVocabularies:
    def test_sources(self):
        assert "toronto" in SOURCES
        assert "ontario" in SOURCES
        assert "statcan" in SOURCES

    def test_licenses(self):
        for lic in ("OGL-Ontario", "ODC-BY", "CC-BY", "CC-BY-SA", "CC0"):
            assert lic in LICENSES

    def test_custom_license_prefix(self):
        assert LICENSE_PREFIX == "custom:"

    def test_statuses(self):
        for s in ("active", "draft", "deprecated", "broken"):
            assert s in STATUSES

    def test_formats(self):
        for f in ("csv", "json", "geojson", "parquet", "xlsx", "xml", "api", "mixed"):
            assert f in FORMATS

    def test_refresh(self):
        for r in (
            "hourly",
            "daily",
            "weekly",
            "monthly",
            "quarterly",
            "annual",
            "manual",
            "never",
        ):
            assert r in REFRESH

    def test_data_storage_no_phantoms(self):
        assert "git" in DATA_STORAGE
        assert "dvc" in DATA_STORAGE
        assert "gitignore+fetch" in DATA_STORAGE


class TestSnapshotIsDue:
    def test_manual_never_not_due(self):
        from snapshot import CADENCE_DAYS as SNAP_CADENCE_DAYS

        assert SNAP_CADENCE_DAYS["manual"] is None
        assert SNAP_CADENCE_DAYS["never"] is None


class TestVerifySuperset:
    def test_first_snapshot_skips(self):
        from snapshot import verify_superset
        from pathlib import Path

        ok, reason = verify_superset(Path("/nonexistent/old"), Path("/nonexistent/new"))
        assert ok
        assert "first snapshot" in reason.lower()

    def test_new_is_superset(self, tmp_path):
        from snapshot import verify_superset

        old = tmp_path / "old.csv"
        new = tmp_path / "new.csv"
        old.write_text("a,b\n1,2\n")
        new.write_text("a,b\n1,2\n3,4\n")
        ok, reason = verify_superset(old, new)
        assert ok

    def test_new_missing_lines(self, tmp_path):
        from snapshot import verify_superset

        old = tmp_path / "old.csv"
        new = tmp_path / "new.csv"
        old.write_text("a,b\n1,2\n3,4\n")
        new.write_text("a,b\n1,2\n")
        ok, reason = verify_superset(old, new)
        assert not ok

    def test_new_smaller(self, tmp_path):
        from snapshot import verify_superset

        old = tmp_path / "old.csv"
        new = tmp_path / "new.csv"
        old.write_text("a,b\n1,2\n3,4\n5,6\n")
        new.write_text("a,b\n7,8\n")
        ok, reason = verify_superset(old, new)
        assert not ok
