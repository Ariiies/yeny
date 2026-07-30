"""Tests for the benchmark result contract."""

import json
from pathlib import Path

import pytest

from benchmarks.results import validate_result, write_result


def _valid_result():
    return {
        "schema_version": "1.0",
        "run_id": "test-run",
        "started_at_utc": "2026-07-29T00:00:00Z",
        "environment": {},
        "configuration": {},
        "datasets": [],
        "measurements": [],
    }


@pytest.mark.unit
def test_result_schema_file_is_valid_json():
    schema_path = (
        Path(__file__).parents[2]
        / "benchmarks"
        / "schema"
        / "result.schema.json"
    )

    schema = json.loads(schema_path.read_text(encoding="utf-8"))

    assert schema["type"] == "object"
    assert schema["properties"]["schema_version"]["const"] == "1.0"
    assert set(schema["required"]).issuperset(_valid_result())


@pytest.mark.unit
def test_validate_result_accepts_minimum_contract():
    validate_result(_valid_result())


@pytest.mark.unit
@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("schema_version", "2.0"),
        ("run_id", ""),
        ("environment", []),
        ("configuration", []),
        ("datasets", {}),
        ("measurements", "not-an-array"),
    ],
)
def test_validate_result_rejects_invalid_contract(field, value):
    result = _valid_result()
    result[field] = value

    with pytest.raises(ValueError):
        validate_result(result)


@pytest.mark.unit
def test_validate_result_reports_missing_fields():
    result = _valid_result()
    del result["measurements"]

    with pytest.raises(ValueError, match="measurements"):
        validate_result(result)


@pytest.mark.unit
def test_write_result_creates_readable_json(tmp_path):
    result = _valid_result()

    output_path = write_result(result, tmp_path)

    assert output_path.parent == tmp_path
    assert json.loads(output_path.read_text(encoding="utf-8")) == result
    assert list(tmp_path.glob("*.tmp")) == []


@pytest.mark.unit
def test_write_result_does_not_overwrite_existing_run(tmp_path):
    result = _valid_result()
    write_result(result, tmp_path)

    with pytest.raises(ValueError, match="already exists"):
        write_result(result, tmp_path)
