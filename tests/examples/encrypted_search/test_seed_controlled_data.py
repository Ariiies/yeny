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
            "target-luis-aries",
            "target-aries-lucis",
            "target-aries-netcommerce",
            "target-real-madrid",
            "target-honda-user",
        ):
            assert expected in refs

    def test_null_dates_kept_as_none(self):
        rows = {row["reference"]: row for row in scd.TARGET_LEADS}
        assert rows["target-aries-lucis"]["created_at"] is None
        assert rows["target-honda-user"]["created_at"] is None
        # Dated targets keep their fixed, documented dates (reproducibility):
        assert rows["target-luis-aries"]["created_at"] == datetime(2026, 2, 19)

    def test_rows_match_database_schema(self):
        import database

        for row in scd.TARGET_LEADS:
            assert set(row) == set(database.ROW_KEYS)

    def test_main_is_callable(self):
        """The script must expose main() and guard execution."""
        assert callable(scd.main)
