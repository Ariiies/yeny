"""Tests for the public benchmark command-line interface."""

import json
from pathlib import Path

import pytest

from benchmarks.cli import main


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
    payload = {
        "schema_version": "1.0",
        "run_id": "test-run",
        "started_at_utc": "2026-07-29T00:00:00+00:00",
        "finished_at_utc": "2026-07-29T00:01:00+00:00",
        "environment": {"python_version": "3.12.3"},
        "configuration": {"profile": "tiny", "engines": ["core"]},
        "datasets": [
            {
                "profile": "tiny",
                "generator_version": "lexical_zipf_v1",
                "seed": 20260117,
                "documents": 100,
                "total_tokens": 6400,
                "vocabulary_nominal": 8192,
                "vocabulary_observed": 3900,
                "intentional_duplicates": 2,
                "sha256": "deadbeef",
            }
        ],
        "queries": {"version": "queries_v1", "queries": 17, "sha256": "aa"},
        "measurements": [],
    }
    path = tmp_path / "lucis-benchmark-test-run.json"
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
    assert "# Lucis benchmark report" in content
    assert "test-run" in content
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
