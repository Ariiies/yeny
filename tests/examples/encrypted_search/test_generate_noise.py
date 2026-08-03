"""Unit tests for generate_noise.py — deterministic volume (no MySQL)."""
from datetime import datetime

import pytest

import generate_noise as gn


@pytest.mark.unit
class TestNoiseGenerator:
    def test_deterministic_with_seed(self):
        first = list(gn.generate(50, seed=42))
        second = list(gn.generate(50, seed=42))
        assert first == second

    def test_different_seed_differs(self):
        assert list(gn.generate(50, seed=1)) != list(gn.generate(50, seed=2))

    def test_count_references_and_keys(self):
        rows = list(gn.generate(10, seed=7))
        assert len(rows) == 10
        assert rows[0]["reference"] == "noise-000000001"
        assert rows[-1]["reference"] == "noise-000000010"
        for row in rows:
            assert set(row) == {
                "reference", "name", "email", "number", "ip", "created_at",
            }

    def test_global_random_untouched(self):
        """The generator must not consume the global RNG state."""
        import random

        random.seed(1234)
        expected = random.random()
        random.seed(1234)
        list(gn.generate(25, seed=99))
        assert random.random() == expected

    def test_null_dates_present(self):
        rows = list(gn.generate(200, seed=5))
        nulls = [r for r in rows if r["created_at"] is None]
        dated = [r for r in rows if r["created_at"] is not None]
        assert nulls, "expected NULL created_at rows for universal-shard testing"
        assert dated
        for row in dated:
            assert datetime(2020, 1, 1) <= row["created_at"] <= datetime(2026, 3, 1)

    def test_streaming(self):
        """generate() must be lazy (a generator), not a materialized list."""
        import types

        gen = gn.generate(1_000_000, seed=1)
        assert isinstance(gen, types.GeneratorType)
        assert next(gen)["reference"] == "noise-000000001"
