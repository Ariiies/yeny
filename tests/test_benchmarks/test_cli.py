"""Tests for the public benchmark command-line interface."""

import json
from pathlib import Path

import pytest

from benchmarks.cli import main

from .result_fixtures import build_valid_result



def _result():
    return {
        "measurements": [
            {
                "name": "index_build",
                "engine": "core",
                "unit": "ns",
                "samples": [1000],
                "summary": {
                    "count": 1,
                    "min": 1000.0,
                    "median": 1000.0,
                    "p95": 1000.0,
                    "max": 1000.0,
                },
            }
        ]
    }


@pytest.mark.unit
def test_cli_run_prints_table_and_result_path(monkeypatch, capsys, tmp_path):
    output_path = tmp_path / "result.json"

    monkeypatch.setattr(
        "benchmarks.cli.run_benchmarks",
        lambda config, progress: (_result(), output_path),
    )

    exit_code = main(
        [
            "run",
            "--profile",
            "tiny",
            "--engine",
            "core",
            "--output",
            str(tmp_path),
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "index_build" in captured.out
    assert str(output_path) in captured.out


@pytest.mark.unit
def test_cli_returns_two_for_invalid_counts(capsys):
    exit_code = main(["run", "--warmups", "-1"])
    captured = capsys.readouterr()

    assert exit_code == 2
    assert "Configuration error" in captured.err


@pytest.mark.unit
def test_cli_require_memory_without_mechanism_returns_three(
    monkeypatch,
    capsys,
    tmp_path,
):
    monkeypatch.setattr(
        "benchmarks.runner.memory_mechanisms",
        lambda: [],
    )

    exit_code = main(
        ["run", "--require-memory", "--output", str(tmp_path)]
    )
    captured = capsys.readouterr()

    assert exit_code == 3
    assert "no RSS mechanism" in captured.err


def _saved_result(tmp_path):
    payload = build_valid_result()
    path = tmp_path / f"yeny-benchmark-{payload['run_id']}.json"
    path.write_text(
        json.dumps(payload),
        encoding="utf-8",
    )
    return path



@pytest.mark.unit
def test_cli_validate_accepts_valid_result(capsys, tmp_path):
    path = _saved_result(tmp_path)

    exit_code = main(["validate", str(path)])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "Valid benchmark result" in captured.out


@pytest.mark.unit
def test_cli_validate_rejects_missing_file(capsys, tmp_path):
    exit_code = main(["validate", str(tmp_path / "missing.json")])
    captured = capsys.readouterr()

    assert exit_code == 4
    assert "Validation error" in captured.err


@pytest.mark.unit
def test_cli_validate_rejects_invalid_contract(capsys, tmp_path):
    path = tmp_path / "broken.json"
    path.write_text('{"schema_version": "2.0"}', encoding="utf-8")

    exit_code = main(["validate", str(path)])
    captured = capsys.readouterr()

    assert exit_code == 4
    assert "Validation error" in captured.err


@pytest.mark.unit
def test_cli_report_writes_markdown_without_overwriting(capsys, tmp_path):
    path = _saved_result(tmp_path)

    exit_code = main(["report", str(path)])
    captured = capsys.readouterr()

    assert exit_code == 0
    report = path.with_suffix(".md")
    assert report.exists()
    content = report.read_text(encoding="utf-8")
    assert "# Yeny benchmark report" in content
    assert "20260729T120000Z-abc123" in content
    assert "Markdown report" in captured.out


    second_exit = main(["report", str(path)])
    second_captured = capsys.readouterr()

    assert second_exit == 4
    assert "already exists" in second_captured.err


@pytest.mark.unit
def test_cli_report_rejects_invalid_result(capsys, tmp_path):
    path = tmp_path / "broken.json"
    path.write_text('{"schema_version": "2.0"}', encoding="utf-8")

    exit_code = main(["report", str(path)])
    captured = capsys.readouterr()

    assert exit_code == 4
    assert "Report error" in captured.err
    assert not path.with_suffix(".md").exists()


def _saved_run(tmp_path, run_id):
    payload = build_valid_result()
    payload["run_id"] = run_id
    path = tmp_path / f"yeny-benchmark-{run_id}.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


@pytest.mark.unit
def test_cli_aggregate_writes_markdown_and_json(capsys, tmp_path):
    first = _saved_run(tmp_path, "run-a")
    second = _saved_run(tmp_path, "run-b")
    output = tmp_path / "summary.md"

    exit_code = main(
        ["aggregate", str(first), str(second), "--output", str(output)]
    )
    captured = capsys.readouterr()

    assert exit_code == 0
    assert output.exists()
    aggregate_json = tmp_path / "summary.aggregate.json"
    assert aggregate_json.exists()
    markdown = output.read_text(encoding="utf-8")
    assert "# Yeny benchmark aggregate" in markdown
    assert "run-a" in markdown
    assert "run-b" in markdown
    assert "Markdown summary" in captured.out


@pytest.mark.unit
def test_cli_aggregate_rejects_incompatible_runs(capsys, tmp_path):
    first = _saved_run(tmp_path, "run-a")
    second_payload = build_valid_result()
    second_payload["run_id"] = "run-b"
    second_payload["configuration"]["repetitions"] = 99
    second = tmp_path / "yeny-benchmark-run-b.json"
    second.write_text(json.dumps(second_payload), encoding="utf-8")

    exit_code = main(
        [
            "aggregate",
            str(first),
            str(second),
            "--output",
            str(tmp_path / "summary.md"),
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 4
    assert "incompatible" in captured.err
    assert "repetitions" in captured.err
    assert not (tmp_path / "summary.md").exists()


@pytest.mark.unit
def test_cli_aggregate_rejects_invalid_result(capsys, tmp_path):
    broken = tmp_path / "broken.json"
    broken.write_text('{"schema_version": "2.0"}', encoding="utf-8")

    exit_code = main(
        [
            "aggregate",
            str(broken),
            "--output",
            str(tmp_path / "summary.md"),
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 4
    assert "Aggregation error" in captured.err


@pytest.mark.unit
def test_cli_aggregate_refuses_to_overwrite(capsys, tmp_path):
    first = _saved_run(tmp_path, "run-a")
    output = tmp_path / "summary.md"
    output.write_text("# existing", encoding="utf-8")

    exit_code = main(
        ["aggregate", str(first), "--output", str(output)]
    )
    captured = capsys.readouterr()

    assert exit_code == 4
    assert "already exists" in captured.err
    assert output.read_text(encoding="utf-8") == "# existing"

