"""Integration tests for isolated benchmark execution."""

import json
from pathlib import Path

import pytest

from benchmarks.config import BenchmarkRunConfig
from benchmarks.runner import run_benchmarks


@pytest.mark.integration
def test_tiny_benchmark_runs_both_engines_and_writes_json(tmp_path):
    config = BenchmarkRunConfig(
        profile="tiny",
        engines=("core", "lite"),
        warmups=0,
        repetitions=1,
        output_dir=tmp_path,
    )

    result, output_path = run_benchmarks(config)

    assert output_path.exists()
    assert json.loads(output_path.read_text(encoding="utf-8")) == result
    assert result["datasets"][0]["documents"] == 100
    assert result["configuration"]["engines"] == ["core", "lite"]
    assert {item["engine"] for item in result["measurements"]} == {
        "core",
        "lite",
    }
    assert {item["name"] for item in result["measurements"]}.issuperset(
        {
            "dataset_generation",
            "index_build",
            "index_e2e_json",
            "search_first",
            "search_warm",
            "json_save",
            "json_artifact_size",
            "sqlite_save",
            "sqlite_artifact_size",
            "lcs_write",
            "lcs_artifact_size",
            "load_standard",
            "search_first_after_load",
            "search_warm_after_load",
            "mmap_load",
            "search_first_mmap",
            "search_warm_mmap",
            "roundtrip_verified",
        }
    )


@pytest.mark.integration
def test_tiny_benchmark_roundtrips_every_backend(tmp_path):
    config = BenchmarkRunConfig(
        profile="tiny",
        engines=("core", "lite"),
        warmups=0,
        repetitions=1,
        output_dir=tmp_path,
    )

    result, _ = run_benchmarks(config)

    load_backends = {
        (item["engine"], item["backend"])
        for item in result["measurements"]
        if item["name"] == "load_standard"
    }
    assert load_backends == {
        ("core", "json"),
        ("core", "sqlite"),
        ("lite", "json"),
        ("lite", "sqlite"),
    }

    roundtrips = [
        item
        for item in result["measurements"]
        if item["name"] == "roundtrip_verified"
    ]
    assert {
        (item["engine"], item["backend"]) for item in roundtrips
    } == {
        ("core", "json"),
        ("core", "sqlite"),
        ("core", "mmap"),
        ("lite", "json"),
        ("lite", "sqlite"),
        ("lite", "mmap"),
    }
    verified_counts = {tuple(item["samples"]) for item in roundtrips}
    assert verified_counts == {(result["queries"]["queries"],)}


@pytest.mark.integration
def test_tiny_benchmark_reports_memory_explicitly(tmp_path):
    config = BenchmarkRunConfig(
        profile="tiny",
        engines=("core",),
        warmups=0,
        repetitions=1,
        output_dir=tmp_path,
    )

    result, _ = run_benchmarks(config)

    memory_measurements = [
        item
        for item in result["measurements"]
        if item["name"].startswith("memory_")
    ]
    expected_names = {
        "memory_baseline_rss",
        "memory_peak_rss",
        "memory_peak_rss_delta",
        "memory_stable_rss",
        "memory_max_processes",
    }
    assert {
        (item["name"], item["phase"]) for item in memory_measurements
    } == {
        (name, phase)
        for name in expected_names
        for phase in ("build", "load_json", "load_sqlite", "load_mmap")
    }

    for item in memory_measurements:
        assert item["status"] in {"ok", "unavailable"}
        if item["status"] == "ok":
            assert item["samples"]
            assert item["summary"]["median"] is not None
            assert item["summary"]["median"] > 0
        else:
            assert item["samples"] == []
            assert item["summary"]["median"] is None
            assert item["limitations"]


@pytest.mark.unit
def test_require_memory_without_mechanism_raises(tmp_path, monkeypatch):
    from benchmarks.runner import MemoryUnavailableError

    monkeypatch.setattr(
        "benchmarks.runner.memory_mechanisms",
        lambda: [],
    )
    config = BenchmarkRunConfig(
        profile="tiny",
        engines=("core",),
        warmups=0,
        repetitions=1,
        output_dir=tmp_path,
        require_memory=True,
    )

    with pytest.raises(MemoryUnavailableError):
        run_benchmarks(config)


@pytest.mark.integration
def test_worker_temporary_directory_is_cleaned(tmp_path, monkeypatch):
    import benchmarks.runner as runner_module

    original = runner_module.tempfile.TemporaryDirectory
    created = []

    def tracked_temporary_directory(*args, **kwargs):
        directory = original(*args, **kwargs)
        created.append(Path(directory.name))
        return directory

    monkeypatch.setattr(
        runner_module.tempfile,
        "TemporaryDirectory",
        tracked_temporary_directory,
    )
    config = BenchmarkRunConfig(
        profile="tiny",
        engines=("core",),
        warmups=0,
        repetitions=1,
        output_dir=tmp_path,
    )

    run_benchmarks(config)

    assert created
    assert all(not path.exists() for path in created)


def _tracked_worker(monkeypatch):
    """Wrap ``_run_worker`` so tests can inspect every phase response."""
    import benchmarks.runner as runner_module

    original = runner_module._run_worker
    calls = []

    def tracked(engine, config, workspace, phase, temporary_path):
        response = original(engine, config, workspace, phase, temporary_path)
        calls.append({"phase": phase, "response": response})
        return response

    monkeypatch.setattr(runner_module, "_run_worker", tracked)
    return calls


@pytest.mark.integration
def test_each_phase_runs_in_a_distinct_process(tmp_path, monkeypatch):
    calls = _tracked_worker(monkeypatch)
    config = BenchmarkRunConfig(
        profile="tiny",
        engines=("core",),
        warmups=0,
        repetitions=1,
        output_dir=tmp_path,
    )

    run_benchmarks(config)

    assert [call["phase"] for call in calls] == [
        "build",
        "load_json",
        "load_sqlite",
        "load_mmap",
    ]
    pids = [call["response"]["pid"] for call in calls]
    assert len(set(pids)) == 4


@pytest.mark.integration
def test_load_workers_return_only_their_own_backend(tmp_path, monkeypatch):
    calls = _tracked_worker(monkeypatch)
    config = BenchmarkRunConfig(
        profile="tiny",
        engines=("core",),
        warmups=0,
        repetitions=1,
        output_dir=tmp_path,
    )

    run_benchmarks(config)

    expected_backends = {
        "load_json": "json",
        "load_sqlite": "sqlite",
        "load_mmap": "mmap",
    }
    for call in calls:
        if call["phase"] == "build":
            continue
        measurements = call["response"]["measurements"]
        assert measurements
        assert {
            item.get("backend", expected_backends[call["phase"]])
            for item in measurements
        } == {expected_backends[call["phase"]]}


@pytest.mark.integration
def test_all_phases_share_the_build_dataset_contract(tmp_path, monkeypatch):
    calls = _tracked_worker(monkeypatch)
    config = BenchmarkRunConfig(
        profile="tiny",
        engines=("core",),
        warmups=0,
        repetitions=1,
        output_dir=tmp_path,
    )

    result, _ = run_benchmarks(config)

    build = calls[0]["response"]
    assert build["dataset"]["sha256"] == result["datasets"][0]["sha256"]
    for call in calls[1:]:
        assert (
            call["response"]["dataset_sha256"]
            == build["dataset"]["sha256"]
        )


@pytest.mark.integration
def test_workspace_is_removed_after_a_worker_failure(
    tmp_path,
    monkeypatch,
):
    import benchmarks.runner as runner_module

    original_temporary = runner_module.tempfile.TemporaryDirectory
    created = []

    def tracked_temporary_directory(*args, **kwargs):
        directory = original_temporary(*args, **kwargs)
        created.append(Path(directory.name))
        return directory

    monkeypatch.setattr(
        runner_module.tempfile,
        "TemporaryDirectory",
        tracked_temporary_directory,
    )
    original_worker = runner_module._run_worker

    def failing_worker(engine, config, workspace, phase, temporary_path):
        if phase == "load_sqlite":
            raise runner_module.BenchmarkExecutionError(
                "core load_sqlite worker exited with 1: boom"
            )
        return original_worker(
            engine, config, workspace, phase, temporary_path
        )

    monkeypatch.setattr(runner_module, "_run_worker", failing_worker)
    config = BenchmarkRunConfig(
        profile="tiny",
        engines=("core",),
        warmups=0,
        repetitions=1,
        output_dir=tmp_path,
    )

    with pytest.raises(runner_module.BenchmarkExecutionError):
        run_benchmarks(config)

    assert created
    assert all(not path.exists() for path in created)


@pytest.mark.unit
def test_worker_failure_identifies_engine_phase_and_stderr(
    tmp_path,
    monkeypatch,
):
    import benchmarks.runner as runner_module

    class FakeProcess:
        pid = 999999999
        returncode = 1

        def communicate(self):
            return "", "sqlite3.OperationalError: database is locked"

    monkeypatch.setattr(
        runner_module.subprocess,
        "Popen",
        lambda *args, **kwargs: FakeProcess(),
    )
    config = BenchmarkRunConfig(
        profile="tiny",
        engines=("core",),
        warmups=0,
        repetitions=1,
        output_dir=tmp_path,
    )

    with pytest.raises(
        runner_module.BenchmarkExecutionError,
    ) as excinfo:
        runner_module._run_worker(
            "core",
            config,
            tmp_path / "workspace",
            "load_sqlite",
            tmp_path,
        )

    message = str(excinfo.value)
    assert "core" in message
    assert "load_sqlite" in message
    assert "database is locked" in message

