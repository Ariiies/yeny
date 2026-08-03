"""Unit tests for seed_controlled_data.py — the controlled dataset."""
from datetime import datetime

import pytest

import seed_controlled_data as scd


@pytest.mark.unit
class TestTargetLeads:
    def test_references_unique_and_prefixed(self):
        refs = [row["reference"] for row in scd.TARGET_LEADS]
        assert len(refs) == len(set(refs))
        assert all(ref.startswith("target-") for ref in refs)

    def test_expected_targets_exist(self):
        refs = {row["reference"] for row in scd.TARGET_LEADS}
        for expected in (
            "target-aries-meza",
            "target-aries-lucis",
            "target-cristiano-ronaldo",
            "target-real-madrid",
            "target-leo-messi",
            "target-vinicus-junior",
            "target-mcr",
            "target-autos-usados",
            "target-admin-publica",
            "target-dev-service",
        ):
            assert expected in refs

    def test_null_dates_kept_as_none(self):
        rows = {row["reference"]: row for row in scd.TARGET_LEADS}
        assert rows["target-aries-lucis"]["created_at"] is None
        assert rows["target-leo-messi"]["created_at"] is None
        assert rows["target-vinicus-junior"]["created_at"] is None
        # Dated targets keep their fixed, documented dates (reproducibility):
        assert rows["target-aries-meza"]["created_at"] == datetime(2026, 2, 19)

    def test_rows_match_database_schema(self):
        import database

        for row in scd.TARGET_LEADS:
            assert set(row) == set(database.ROW_KEYS)

    def test_main_is_callable(self):
        """The script must expose main() and guard execution."""
        assert callable(scd.main)
