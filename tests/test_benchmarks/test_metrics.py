"""Tests for benchmark timing and statistical helpers."""

import pytest

from benchmarks.metrics import (
    make_measurement,
    measure_once,
    measure_operation,
    summarize_samples,
)


@pytest.mark.unit
def test_summarize_samples_reports_robust_statistics():
    summary = summarize_samples([50, 10, 30, 20, 40])

    assert summary == {
        "count": 5,
        "min": 10.0,
        "median": 30.0,
        "p95": 50.0,
        "max": 50.0,
    }


@pytest.mark.unit
def test_summarize_samples_rejects_empty_input():
    with pytest.raises(ValueError, match="cannot be empty"):
        summarize_samples([])


@pytest.mark.unit
def test_measure_operation_runs_requested_repetitions():
    calls = []

    samples = measure_operation(lambda: calls.append(True), repetitions=3)

    assert calls == [True, True, True]
    assert len(samples) == 3
    assert all(sample >= 0 for sample in samples)


@pytest.mark.unit
def test_measure_operation_rejects_invalid_repetitions():
    with pytest.raises(ValueError, match="greater than zero"):
        measure_operation(lambda: None, repetitions=0)


@pytest.mark.unit
def test_measure_once_preserves_return_value():
    value, elapsed = measure_once(lambda: "result")

    assert value == "result"
    assert elapsed >= 0


@pytest.mark.unit
def test_make_measurement_preserves_raw_samples_and_context():
    measurement = make_measurement(
        "search_warm",
        [10, 20],
        engine="core",
        query_category="rare",
    )

    assert measurement["unit"] == "ns"
    assert measurement["samples"] == [10, 20]
    assert measurement["summary"]["median"] == 15.0
    assert measurement["engine"] == "core"
    assert measurement["query_category"] == "rare"


@pytest.mark.unit
def test_make_measurement_supports_custom_units():
    measurement = make_measurement(
        "json_artifact_size",
        [128],
        unit="bytes",
        engine="core",
    )

    assert measurement["unit"] == "bytes"
    assert measurement["samples"] == [128]
    assert measurement["summary"]["median"] == 128.0
