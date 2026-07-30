"""Tests for the benchmark result contract."""

import copy
import json
from pathlib import Path

import pytest

from benchmarks.results import validate_result, write_result

from .result_fixtures import build_valid_result


def _valid_result():
    return build_valid_result()


def _corrupt(mutator):
    """Return a deep-copied valid result altered by ``mutator``."""
    result = copy.deepcopy(_valid_result())
    mutator(result)
    return result


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
def test_validate_result_accepts_complete_contract():
    validate_result(_valid_result())


@pytest.mark.unit
def test_validate_result_accepts_both_engines():
    validate_result(build_valid_result(engines=("core", "lite")))


@pytest.mark.unit
@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("schema_version", "2.0"),
        ("run_id", ""),
        ("environment", []),
        ("configuration", []),
        ("datasets", {}),
        ("queries", []),
        ("measurements", "not-an-array"),
    ],
)
def test_validate_result_rejects_invalid_contract(field, value):
    def mutate(result):
        result[field] = value

    with pytest.raises(ValueError):
        validate_result(_corrupt(mutate))


@pytest.mark.unit
def test_validate_result_reports_missing_fields():
    def mutate(result):
        del result["measurements"]

    with pytest.raises(ValueError, match="measurements"):
        validate_result(_corrupt(mutate))


@pytest.mark.unit
@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("started_at_utc", "not-a-date", "ISO 8601"),
        ("started_at_utc", "2026-07-29 12:00:00", "timezone"),

        ("finished_at_utc", "", "non-empty"),
        ("started_at_utc", "2026-07-29T12:00:00", "timezone"),
    ],
)
def test_validate_result_rejects_bad_timestamps(field, value, message):
    def mutate(result):
        result[field] = value

    with pytest.raises(ValueError, match=message):
        validate_result(_corrupt(mutate))


@pytest.mark.unit
def test_validate_result_rejects_finish_before_start():
    def mutate(result):
        result["finished_at_utc"] = "2026-07-29T11:00:00+00:00"

    with pytest.raises(ValueError, match="earlier"):
        validate_result(_corrupt(mutate))


@pytest.mark.unit
def test_validate_result_rejects_dataset_hash_mismatch():
    def mutate(result):
        result["datasets"][0]["sha256"] = "a" * 64

    with pytest.raises(ValueError, match="frozen reference"):
        validate_result(_corrupt(mutate))


@pytest.mark.unit
def test_validate_result_rejects_malformed_dataset_hash():
    def mutate(result):
        result["datasets"][0]["sha256"] = "deadbeef"

    with pytest.raises(ValueError, match="hex hash"):
        validate_result(_corrupt(mutate))


@pytest.mark.unit
def test_validate_result_rejects_query_manifest_from_another_dataset():
    def mutate(result):
        result["queries"]["dataset_sha256"] = "b" * 64

    with pytest.raises(ValueError, match="another dataset"):
        validate_result(_corrupt(mutate))


@pytest.mark.unit
def test_validate_result_rejects_wrong_query_count():
    def mutate(result):
        result["queries"]["queries"] = 16

    with pytest.raises(ValueError, match="queries"):
        validate_result(_corrupt(mutate))


@pytest.mark.unit
def test_validate_result_rejects_unknown_profile():
    def mutate(result):
        result["configuration"]["profile"] = "unknown"

    with pytest.raises(ValueError, match="profile"):
        validate_result(_corrupt(mutate))


@pytest.mark.unit
def test_validate_result_rejects_negative_dataset_counts():
    def mutate(result):
        result["datasets"][0]["total_tokens"] = -1

    with pytest.raises(ValueError, match="non-negative"):
        validate_result(_corrupt(mutate))


@pytest.mark.unit
@pytest.mark.parametrize("bad_sample", [-1, float("inf"), float("nan"), True])
def test_validate_result_rejects_non_finite_or_negative_samples(bad_sample):
    def mutate(result):
        measurement = result["measurements"][0]
        measurement["samples"] = [bad_sample]

    with pytest.raises(ValueError, match="samples"):
        validate_result(_corrupt(mutate))


@pytest.mark.unit
def test_validate_result_rejects_summary_contradicting_samples():
    def mutate(result):
        measurement = result["measurements"][0]
        measurement["summary"]["median"] += 1.0

    with pytest.raises(ValueError, match="contradicts"):
        validate_result(_corrupt(mutate))


@pytest.mark.unit
def test_validate_result_rejects_wrong_sample_count():
    def mutate(result):
        measurement = result["measurements"][0]
        measurement["summary"]["count"] += 1

    with pytest.raises(ValueError, match="contradicts"):
        validate_result(_corrupt(mutate))


@pytest.mark.unit
def test_validate_result_rejects_unknown_unit():
    def mutate(result):
        result["measurements"][0]["unit"] = "seconds"

    with pytest.raises(ValueError, match="unit"):
        validate_result(_corrupt(mutate))


@pytest.mark.unit
def test_validate_result_rejects_unknown_measurement_engine():
    def mutate(result):
        result["measurements"][0]["engine"] = "other"

    with pytest.raises(ValueError, match="engine"):
        validate_result(_corrupt(mutate))


@pytest.mark.unit
def test_validate_result_rejects_unknown_backend():
    def mutate(result):
        for measurement in result["measurements"]:
            if measurement["name"] == "load_standard":
                measurement["backend"] = "csv"
                break

    with pytest.raises(ValueError, match="backend"):
        validate_result(_corrupt(mutate))


@pytest.mark.unit
def test_validate_result_rejects_engine_mismatch():
    def mutate(result):
        result["configuration"]["engines"] = ["core", "lite"]

    with pytest.raises(ValueError, match="requested engines"):
        validate_result(_corrupt(mutate))


@pytest.mark.unit
@pytest.mark.parametrize(
    "missing_name",
    [
        "index_build",
        "json_save",
        "load_standard",
        "mmap_load",
        "search_warm",
        "memory_peak_rss",
    ],
)
def test_validate_result_rejects_missing_mandatory_metrics(missing_name):
    def mutate(result):
        result["measurements"] = [
            measurement
            for measurement in result["measurements"]
            if measurement["name"] != missing_name
        ]

    with pytest.raises(ValueError, match="missing|must"):
        validate_result(_corrupt(mutate))


@pytest.mark.unit
def test_validate_result_rejects_duplicate_measurement_context():
    def mutate(result):
        result["measurements"].append(result["measurements"][0].copy())

    with pytest.raises(ValueError, match="duplicated"):
        validate_result(_corrupt(mutate))


@pytest.mark.unit
def test_validate_result_rejects_empty_samples_without_unavailable_status():
    def mutate(result):
        measurement = result["measurements"][0]
        measurement["samples"] = []
        measurement["summary"] = {
            "count": 0,
            "min": None,
            "median": None,
            "p95": None,
            "max": None,
        }

    with pytest.raises(ValueError, match="unavailable"):
        validate_result(_corrupt(mutate))


@pytest.mark.unit
def test_validate_result_rejects_unavailable_memory_with_values():
    def mutate(result):
        for measurement in result["measurements"]:
            if measurement["name"] == "memory_peak_rss":
                measurement["samples"] = []
                measurement["status"] = "unavailable"
                break

    with pytest.raises(ValueError, match="null summaries"):
        validate_result(_corrupt(mutate))


@pytest.mark.unit
def test_validate_result_accepts_unavailable_memory_with_null_summary():
    def mutate(result):
        for measurement in result["measurements"]:
            if measurement["name"] == "memory_peak_rss":
                measurement["samples"] = []
                measurement["status"] = "unavailable"
                measurement["summary"] = {
                    "count": 0,
                    "min": None,
                    "median": None,
                    "p95": None,
                    "max": None,
                }

    validate_result(_corrupt(mutate))


@pytest.mark.unit
def test_validate_result_rejects_wrong_roundtrip_count():
    def mutate(result):
        for measurement in result["measurements"]:
            if measurement["name"] == "roundtrip_verified":
                measurement["samples"] = [16]
                measurement["summary"] = {
                    "count": 1,
                    "min": 16.0,
                    "median": 16.0,
                    "p95": 16.0,
                    "max": 16.0,
                }

    with pytest.raises(ValueError, match="roundtrip_verified"):
        validate_result(_corrupt(mutate))


@pytest.mark.unit
def test_validate_result_rejects_missing_roundtrip_backend():
    def mutate(result):
        result["measurements"] = [
            measurement
            for measurement in result["measurements"]
            if not (
                measurement["name"] == "roundtrip_verified"
                and measurement.get("backend") == "mmap"
            )
        ]

    with pytest.raises(ValueError, match="roundtrip"):
        validate_result(_corrupt(mutate))


@pytest.mark.unit
def test_write_result_creates_readable_json(tmp_path):
    result = _valid_result()

    output_path = write_result(result, tmp_path)

    assert output_path.parent == tmp_path
    assert json.loads(output_path.read_text(encoding="utf-8")) == result
    assert list(tmp_path.glob("*.tmp")) == []


@pytest.mark.unit
def test_write_result_rejects_invalid_result(tmp_path):
    result = _corrupt(lambda payload: payload.update(run_id=""))

    with pytest.raises(ValueError):
        write_result(result, tmp_path)
    assert list(tmp_path.glob("*.json")) == []


@pytest.mark.unit
def test_write_result_does_not_overwrite_existing_run(tmp_path):
    result = _valid_result()
    write_result(result, tmp_path)

    with pytest.raises(ValueError, match="already exists"):
        write_result(result, tmp_path)
