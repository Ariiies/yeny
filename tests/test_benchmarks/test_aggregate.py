"""Tests for reproducible aggregation of benchmark runs."""

import json

import pytest


from benchmarks.aggregate import (
    AggregateError,
    aggregate_results,
    load_run,
    render_aggregate_markdown,
    run_fingerprint,
    write_aggregate,
)
from benchmarks.metrics import summarize_samples

from .result_fixtures import build_valid_result


def _run(run_id, **environment_overrides):
    result = build_valid_result()
    result["run_id"] = run_id
    result["environment"].update(environment_overrides)
    return result


def _set_median(result, name, value, *, backend=None):
    """Rewrite one measurement's samples and summary around ``value``."""
    for measurement in result["measurements"]:
        if measurement["name"] != name:
            continue
        if backend is not None and measurement.get("backend") != backend:
            continue
        measurement["samples"] = [value]
        measurement["summary"] = summarize_samples([float(value)])
        return measurement
    raise AssertionError(f"measurement not found: {name}")


@pytest.mark.unit
def test_fingerprint_covers_the_campaign_contract():
    fingerprint = run_fingerprint(_run("run-a"))

    assert set(fingerprint) == {
        "schema_version",
        "yeny_version",
        "git_commit",
        "python_minor",
        "profile",
        "dataset_sha256",
        "queries_sha256",
        "engines",
        "warmups",
        "repetitions",
        "require_memory",
    }
    assert fingerprint["python_minor"] == "3.12"
    assert fingerprint["engines"] == ("core",)


@pytest.mark.unit
def test_aggregate_combines_compatible_runs_deterministically():
    runs = [_run("run-a"), _run("run-b"), _run("run-c")]

    first = aggregate_results(runs)
    second = aggregate_results(list(reversed(runs)))

    assert len(first["groups"]) == 1
    group = first["groups"][0]
    assert group["runs"] == 3
    assert group["run_ids"] == ["run-a", "run-b", "run-c"]
    reversed_group = second["groups"][0]
    assert group["metrics"] == reversed_group["metrics"]


@pytest.mark.unit
def test_aggregate_statistics_use_median_of_medians():
    run_a = _run("run-a")
    run_b = _run("run-b")
    run_c = _run("run-c")
    _set_median(run_a, "index_build", 1_000)
    _set_median(run_b, "index_build", 2_000)
    _set_median(run_c, "index_build", 9_000)

    aggregate = aggregate_results([run_a, run_b, run_c])
    metrics = {
        metric["name"]: metric
        for metric in aggregate["groups"][0]["metrics"]
    }

    index_build = metrics["index_build"]
    assert index_build["median"] == 2_000.0
    assert index_build["median_min"] == 1_000.0
    assert index_build["median_max"] == 9_000.0
    assert index_build["p95"] == 2_000.0
    assert index_build["runs"] == 3
    assert index_build["status"] == "ok"


@pytest.mark.unit
def test_aggregate_rejects_empty_input():
    with pytest.raises(AggregateError, match="at least one"):
        aggregate_results([])


@pytest.mark.unit
@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("yeny_version", "0.2.0"),
        ("git_commit", "ffffff"),
        ("python_version", "3.13.0"),
    ],
)
def test_aggregate_rejects_mismatched_environment(field, value):
    run_a = _run("run-a")
    run_b = _run("run-b", **{field: value})

    with pytest.raises(AggregateError, match="incompatible"):
        aggregate_results([run_a, run_b])


@pytest.mark.unit
@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("warmups", 5),
        ("repetitions", 20),
        ("require_memory", True),
    ],
)
def test_aggregate_rejects_mismatched_configuration(field, value):
    run_a = _run("run-a")
    run_b = _run("run-b")
    run_b["configuration"][field] = value

    with pytest.raises(AggregateError, match="incompatible"):
        aggregate_results([run_a, run_b])


@pytest.mark.unit
def test_aggregate_rejects_mismatched_engines():
    run_a = _run("run-a")
    run_b = build_valid_result(engines=("core", "lite"))
    run_b["run_id"] = "run-b"

    with pytest.raises(AggregateError, match="engines"):
        aggregate_results([run_a, run_b])


@pytest.mark.unit
def test_aggregate_rejects_mismatched_profile():
    run_a = _run("run-a")
    run_b = build_valid_result(profile="small")
    run_b["run_id"] = "run-b"

    with pytest.raises(AggregateError, match="profile"):
        aggregate_results([run_a, run_b])



@pytest.mark.unit
def test_aggregate_rejects_mismatched_dataset_hash():
    run_a = _run("run-a")
    run_b = _run("run-b")
    other_hash = "0" * 64
    run_b["datasets"][0]["sha256"] = other_hash
    run_b["queries"]["dataset_sha256"] = other_hash

    with pytest.raises(AggregateError, match="dataset_sha256"):
        aggregate_results([run_a, run_b])


@pytest.mark.unit
def test_aggregate_separates_different_machines_into_groups():
    linux = _run("linux-run")
    windows = _run(
        "windows-run",
        system="Windows",
        machine="AMD64",
        cpu_model="Windows CPU",
    )

    aggregate = aggregate_results([linux, windows])

    assert len(aggregate["groups"]) == 2
    systems = {group["system"] for group in aggregate["groups"]}
    assert systems == {"Linux", "Windows"}
    for group in aggregate["groups"]:
        assert group["runs"] == 1


@pytest.mark.unit
def test_aggregate_preserves_run_ids_and_sources():
    runs = [_run("run-a"), _run("run-b")]

    aggregate = aggregate_results(runs, sources=["a.json", "b.json"])

    assert aggregate["sources"] == [
        {"run_id": "run-a", "path": "a.json"},
        {"run_id": "run-b", "path": "b.json"},
    ]


@pytest.mark.unit
def test_aggregate_warns_about_dirty_tree():
    clean = _run("clean-run")
    dirty = _run("dirty-run", git_dirty=True)

    aggregate = aggregate_results([clean, dirty])

    assert any(
        "dirty" in warning and "dirty-run" in warning
        for warning in aggregate["warnings"]
    )


@pytest.mark.unit
def test_aggregate_warns_about_missing_metadata():
    run = _run("run-a", cpu_model=None, total_ram_bytes=None)

    aggregate = aggregate_results([run])

    assert any("cpu model" in warning for warning in aggregate["warnings"])
    assert any("total RAM" in warning for warning in aggregate["warnings"])


@pytest.mark.unit
def test_aggregate_warns_about_high_variability_without_failing():
    run_a = _run("run-a")
    run_b = _run("run-b")
    _set_median(run_a, "index_build", 1_000)
    _set_median(run_b, "index_build", 2_500)

    aggregate = aggregate_results([run_a, run_b])

    assert any(
        "variability" in warning and "index_build" in warning
        for warning in aggregate["warnings"]
    )
    metrics = {
        metric["name"]: metric
        for metric in aggregate["groups"][0]["metrics"]
    }
    assert metrics["index_build"]["median"] == 1_750.0


@pytest.mark.unit
def test_aggregate_marks_unavailable_metrics():
    run_a = _run("run-a")
    for measurement in run_a["measurements"]:
        if measurement["name"] == "memory_baseline_rss":
            measurement["samples"] = []
            measurement["status"] = "unavailable"
            measurement["summary"] = {
                "count": 0,
                "min": None,
                "median": None,
                "p95": None,
                "max": None,
            }

    aggregate = aggregate_results([run_a])
    metrics = {
        (metric["name"], metric["phase"]): metric
        for metric in aggregate["groups"][0]["metrics"]
    }

    baseline = metrics[("memory_baseline_rss", "build")]
    assert baseline["status"] == "unavailable"
    assert baseline["median"] is None


@pytest.mark.unit
def test_render_aggregate_markdown_shows_groups_sources_and_warnings():
    run_a = _run("run-a")
    run_b = _run("run-b", git_dirty=True)
    aggregate = aggregate_results([run_a, run_b], sources=["a.json", "b.json"])

    markdown = render_aggregate_markdown(aggregate)

    assert "# Yeny benchmark aggregate" in markdown
    assert "Linux / x86_64 / Test CPU 9000" in markdown
    assert "run-a" in markdown
    assert "a.json" in markdown
    assert "## Warnings" in markdown
    assert "index_build" in markdown


@pytest.mark.unit
def test_load_run_reads_and_validates(tmp_path):
    path = tmp_path / "run.json"
    path.write_text(json.dumps(_run("run-a")), encoding="utf-8")

    assert load_run(path)["run_id"] == "run-a"

    broken = tmp_path / "broken.json"
    broken.write_text("{not json", encoding="utf-8")
    with pytest.raises(AggregateError, match="cannot read"):
        load_run(broken)

    invalid = tmp_path / "invalid.json"
    invalid.write_text('{"schema_version": "2.0"}', encoding="utf-8")
    with pytest.raises(AggregateError, match="not a valid result"):
        load_run(invalid)


@pytest.mark.unit
def test_write_aggregate_writes_markdown_and_json_without_overwriting(
    tmp_path,
):
    aggregate = aggregate_results([_run("run-a")], sources=["a.json"])
    output = tmp_path / "summary.md"

    markdown_path, json_path = write_aggregate(aggregate, output)

    assert markdown_path.exists()
    assert json_path.exists()
    assert json_path.name == "summary.aggregate.json"
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert payload["kind"] == "yeny-benchmark-aggregate"
    assert payload["groups"][0]["run_ids"] == ["run-a"]

    with pytest.raises(AggregateError, match="already exists"):
        write_aggregate(aggregate, output)
