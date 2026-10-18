"""Tests for dependency-free terminal benchmark reporting."""

import pytest

from benchmarks.reporting import (
    format_bytes,
    format_duration,
    render_markdown_report,
    render_results_table,
)


@pytest.mark.unit
@pytest.mark.parametrize(
    ("nanoseconds", "expected"),
    [
        (500, "500 ns"),
        (5_000, "5.00 µs"),
        (5_000_000, "5.00 ms"),
        (5_000_000_000, "5.00 s"),
    ],
)
def test_format_duration_selects_readable_unit(nanoseconds, expected):
    assert format_duration(nanoseconds) == expected


@pytest.mark.unit
@pytest.mark.parametrize(
    ("size", "expected"),
    [
        (512, "512 B"),
        (2048, "2.00 KiB"),
        (5 * 1024**2, "5.00 MiB"),
        (3 * 1024**3, "3.00 GiB"),
    ],
)
def test_format_bytes_selects_readable_unit(size, expected):
    assert format_bytes(size) == expected


@pytest.mark.unit
def test_render_results_table_includes_metric_context():
    result = {
        "measurements": [
            {
                "name": "search_warm",
                "engine": "core",
                "query_category": "rare",
                "summary": {
                    "count": 2,
                    "median": 5_000,
                    "p95": 7_000,
                },
            }
        ]
    }

    table = render_results_table(result)

    assert "Engine" in table
    assert "search_warm" in table
    assert "rare" in table
    assert "5.00 µs" in table


def _sample_result():
    return {
        "schema_version": "1.0",
        "run_id": "20260729T120000Z-abc123",
        "started_at_utc": "2026-07-29T12:00:00+00:00",
        "finished_at_utc": "2026-07-29T12:01:00+00:00",
        "environment": {
            "python_version": "3.12.3",
            "python_implementation": "CPython",
            "platform": "Linux-7.0",
            "machine": "x86_64",
            "cpu_model": "Test CPU 9000",
            "logical_cpu_count": 8,
            "total_ram_bytes": 16 * 1024**3,
            "psutil_version": "7.2.2",
            "memory_mechanisms": ["psutil", "resource", "proc"],
            "yeny_version": "0.1.0",
            "git_commit": "285320e",
            "git_dirty": False,
        },

        "configuration": {
            "profile": "tiny",
            "engines": ["core"],
            "warmups": 1,
            "repetitions": 2,
            "require_memory": False,
        },
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
        "queries": {
            "version": "queries_v1",
            "queries": 17,
            "sha256": "cafef00d",
        },
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
            },
            {
                "name": "memory_peak_rss",
                "engine": "core",
                "phase": "build",
                "scope": "self_only",
                "unit": "bytes",
                "samples": [1048576],
                "summary": {
                    "count": 1,
                    "min": 1048576.0,
                    "median": 1048576.0,
                    "p95": 1048576.0,
                    "max": 1048576.0,
                },
                "status": "ok",
                "limitations": ["self-only peak excludes child workers"],
            },
            {
                "name": "memory_baseline_rss",
                "engine": "core",
                "phase": "build",
                "scope": "process_tree",
                "unit": "bytes",
                "samples": [],
                "summary": {
                    "count": 0,
                    "min": None,
                    "median": None,
                    "p95": None,
                    "max": None,
                },
                "status": "unavailable",
                "limitations": ["psutil not installed"],
            },
            {
                "name": "roundtrip_verified",
                "engine": "core",
                "backend": "json",
                "unit": "count",
                "samples": [17],
                "summary": {
                    "count": 1,
                    "min": 17.0,
                    "median": 17.0,
                    "p95": 17.0,
                    "max": 17.0,
                },
            },
        ],
    }


@pytest.mark.unit
def test_markdown_report_contains_identity_context_and_warning():
    markdown = render_markdown_report(_sample_result())

    assert "# Yeny benchmark report" in markdown
    assert "20260729T120000Z-abc123" in markdown
    assert "not search-quality measurements" in markdown
    assert "deadbeef" in markdown
    assert "cafef00d" in markdown
    assert "3.12.3" in markdown
    assert "index_build" in markdown


@pytest.mark.unit
def test_markdown_report_marks_unavailable_memory_as_na_not_zero():
    markdown = render_markdown_report(_sample_result())

    assert "## Memory" in markdown
    assert "n/a" in markdown
    assert "unavailable" in markdown
    assert "psutil not installed" in markdown
    assert "1.00 MiB" in markdown
    assert "0 B" not in markdown


@pytest.mark.unit
def test_markdown_report_includes_roundtrip_and_limitations():
    markdown = render_markdown_report(_sample_result())

    assert "## Round-trip verification" in markdown
    assert "| core | json | 17 |" in markdown
    assert "## Limitations" in markdown
    assert "page cache" in markdown
    assert "process-cold" in markdown


@pytest.mark.unit
def test_markdown_report_shows_cpu_ram_and_memory_mechanism():
    markdown = render_markdown_report(_sample_result())

    assert "Test CPU 9000" in markdown
    assert "16.00 GiB" in markdown
    assert "psutil, resource, proc" in markdown
    assert "7.2.2" in markdown


@pytest.mark.unit
def test_markdown_report_marks_missing_hardware_as_na_not_zero():
    result = _sample_result()
    result["environment"]["cpu_model"] = None
    result["environment"]["total_ram_bytes"] = None

    markdown = render_markdown_report(result)

    assert "| cpu_model | n/a |" in markdown
    assert "| total_ram_bytes | n/a |" in markdown
    assert "0 B |" not in markdown



@pytest.mark.unit
def test_render_results_table_formats_bytes_and_backend():
    result = {
        "measurements": [
            {
                "name": "json_artifact_size",
                "engine": "core",
                "backend": "json",
                "unit": "bytes",
                "summary": {
                    "count": 1,
                    "median": 2048.0,
                    "p95": 2048.0,
                },
            }
        ]
    }

    table = render_results_table(result)

    assert "Backend" in table
    assert "json" in table
    assert "2.00 KiB" in table
