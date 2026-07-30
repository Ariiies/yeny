"""Tests for benchmark memory sampling and availability reporting."""

import os
import sys
import time

import pytest

from benchmarks import memory


@pytest.mark.unit
def test_memory_mechanisms_are_explicit():
    mechanisms = memory.memory_mechanisms()

    assert isinstance(mechanisms, list)
    if sys.platform != "win32":
        assert "resource" in mechanisms


@pytest.mark.unit
def test_self_peak_rss_is_positive_on_unix():
    peak = memory.self_peak_rss_bytes()

    if sys.platform == "win32":
        assert peak is None
    else:
        assert peak is not None and peak > 0


@pytest.mark.unit
def test_self_current_rss_is_positive_when_knowable():
    current = memory.self_current_rss_bytes()

    if sys.platform.startswith("linux") or memory.psutil_available():
        assert current is not None and current > 0


@pytest.mark.unit
def test_collect_self_memory_returns_expected_keys():
    report = memory.collect_self_memory()

    assert set(report) == {
        "self_peak_rss_bytes",
        "self_stable_rss_bytes",
    }


@pytest.mark.unit
def test_build_memory_measurements_with_full_tree_data():
    measurements = memory.build_memory_measurements(
        "core",
        "build",
        {"self_peak_rss_bytes": 1000, "self_stable_rss_bytes": 800},
        {
            "baseline_rss_bytes": 500,
            "peak_rss_bytes": 1200,
            "max_processes": 3,
            "sample_count": 10,
        },
    )

    by_name = {item["name"]: item for item in measurements}
    assert by_name["memory_baseline_rss"]["samples"] == [500]
    assert by_name["memory_peak_rss"]["samples"] == [1200]
    assert by_name["memory_peak_rss"]["scope"] == "process_tree"
    assert by_name["memory_peak_rss_delta"]["samples"] == [700]
    assert by_name["memory_peak_rss_delta"]["limitations"]
    assert by_name["memory_stable_rss"]["samples"] == [800]
    assert by_name["memory_stable_rss"]["scope"] == "self_only"
    assert by_name["memory_max_processes"]["samples"] == [3]
    assert by_name["memory_max_processes"]["unit"] == "count"
    assert all(item["status"] == "ok" for item in measurements)
    assert all(item["phase"] == "build" for item in measurements)


@pytest.mark.unit
def test_build_memory_measurements_without_tree_uses_self_fallback():
    measurements = memory.build_memory_measurements(
        "lite",
        "load",
        {"self_peak_rss_bytes": 2048, "self_stable_rss_bytes": None},
        None,
    )

    by_name = {item["name"]: item for item in measurements}
    peak = by_name["memory_peak_rss"]
    assert peak["status"] == "ok"
    assert peak["scope"] == "self_only"
    assert peak["samples"] == [2048]
    assert any("child worker" in note for note in peak["limitations"])

    baseline = by_name["memory_baseline_rss"]
    assert baseline["status"] == "unavailable"
    assert baseline["samples"] == []
    assert baseline["summary"]["median"] is None
    assert baseline["limitations"]

    stable = by_name["memory_stable_rss"]
    assert stable["status"] == "unavailable"
    assert stable["summary"]["median"] is None

    max_processes = by_name["memory_max_processes"]
    assert max_processes["status"] == "unavailable"
    assert max_processes["summary"]["median"] is None


@pytest.mark.unit
def test_unavailable_memory_is_never_reported_as_zero():
    measurements = memory.build_memory_measurements("core", "build", {}, None)

    assert measurements
    for item in measurements:
        assert item["status"] == "unavailable"
        assert item["samples"] == []
        assert item["summary"]["median"] is None
        assert item["summary"]["median"] != 0
        assert item["limitations"]


@pytest.mark.unit
@pytest.mark.skipif(
    not memory.psutil_available(),
    reason="psutil is not installed",
)
def test_tree_sampler_collects_current_process():
    sampler = memory.TreeRssSampler(os.getpid(), interval_seconds=0.005)
    sampler.start()
    time.sleep(0.05)
    sampler.stop()

    summary = sampler.summary()

    assert summary["sample_count"] >= 1
    assert summary["baseline_rss_bytes"] > 0
    assert summary["peak_rss_bytes"] >= summary["baseline_rss_bytes"]
    assert summary["max_processes"] >= 1


@pytest.mark.unit
@pytest.mark.skipif(
    not memory.psutil_available(),
    reason="psutil is not installed",
)
def test_tree_sampler_handles_missing_process():
    sampler = memory.TreeRssSampler(999999999, interval_seconds=0.005)
    sampler.start()
    time.sleep(0.02)
    sampler.stop()

    summary = sampler.summary()

    assert summary["sample_count"] == 0
    assert summary["baseline_rss_bytes"] is None
    assert summary["peak_rss_bytes"] is None
    assert summary["max_processes"] is None


@pytest.mark.unit
def test_tree_sampler_requires_psutil(monkeypatch):
    monkeypatch.setattr(memory, "psutil", None)

    with pytest.raises(memory.MemoryUnavailableError):
        memory.TreeRssSampler(os.getpid())
