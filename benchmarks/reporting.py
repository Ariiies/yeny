"""Plain-text reporting for interactive benchmark runs.

The formatter intentionally uses only the Python standard library so the
benchmark command remains available after a normal Lucis development install.
"""

from __future__ import annotations

from typing import Any, Dict, List, Sequence, Tuple


def format_duration(nanoseconds: float) -> str:
    """Format a nanosecond duration using a readable unit.

    Args:
        nanoseconds: Duration expressed in nanoseconds.

    Returns:
        Compact duration string in ns, µs, ms, or seconds.
    """
    if nanoseconds < 1_000:
        return f"{nanoseconds:.0f} ns"
    if nanoseconds < 1_000_000:
        return f"{nanoseconds / 1_000:.2f} µs"
    if nanoseconds < 1_000_000_000:
        return f"{nanoseconds / 1_000_000:.2f} ms"
    return f"{nanoseconds / 1_000_000_000:.2f} s"


def format_bytes(size: float) -> str:
    """Format a byte count using binary units.

    Args:
        size: Non-negative byte count.

    Returns:
        Compact size string in B, KiB, MiB, or GiB.
    """
    if size < 1024:
        return f"{size:.0f} B"
    if size < 1024 ** 2:
        return f"{size / 1024:.2f} KiB"
    if size < 1024 ** 3:
        return f"{size / 1024 ** 2:.2f} MiB"
    return f"{size / 1024 ** 3:.2f} GiB"


def _format_value(unit: str, value: float) -> str:
    """Format one summary value according to its measurement unit."""
    if value is None:
        return "n/a"
    if unit == "bytes":
        return format_bytes(value)
    if unit == "count":
        return str(int(value))
    return format_duration(value)


def _render_table(headers: Sequence[str], rows: Sequence[Sequence[str]]) -> str:
    """Render rows as an aligned, dependency-free terminal table."""
    widths = [
        max(len(headers[index]), *(len(row[index]) for row in rows))
        for index in range(len(headers))
    ]
    header = "  ".join(
        value.ljust(widths[index])
        for index, value in enumerate(headers)
    )
    separator = "  ".join("-" * width for width in widths)
    body = [
        "  ".join(
            value.ljust(widths[index])
            for index, value in enumerate(row)
        )
        for row in rows
    ]
    return "\n".join([header, separator, *body])


def render_results_table(result: Dict[str, Any]) -> str:
    """Render all measurements from one benchmark result.

    Args:
        result: Valid result dictionary produced by
            :func:`benchmarks.runner.run_benchmarks`.

    Returns:
        Human-readable table with engine, metric, backend, category,
        median, p95, and sample count. Median and p95 follow each
        measurement's unit.
    """
    rows: List[List[str]] = []
    for measurement in result["measurements"]:
        summary = measurement["summary"]
        unit = measurement.get("unit", "ns")
        rows.append(
            [
                measurement.get("engine", "-"),
                measurement["name"],
                measurement.get("backend", "-"),
                measurement.get("query_category", "-"),
                _format_value(unit, summary["median"]),
                _format_value(unit, summary["p95"]),
                str(summary["count"]),
            ]
        )
    return _render_table(
        (
            "Engine",
            "Metric",
            "Backend",
            "Category",
            "Median",
            "p95",
            "Samples",
        ),
        rows,
    )


_MEASUREMENT_GROUPS: Sequence[Tuple[str, Sequence[str]]] = (
    (
        "Construction and search after build",
        (
            "dataset_generation",
            "index_build",
            "index_e2e_json",
            "search_first",
            "search_warm",
        ),
    ),
    (
        "Persistence",
        (
            "json_save",
            "json_artifact_size",
            "sqlite_save",
            "sqlite_artifact_size",
            "lcs_write",
            "lcs_artifact_size",
        ),
    ),
    (
        "Standard loads",
        (
            "load_standard",
            "search_first_after_load",
            "search_warm_after_load",
        ),
    ),
    (
        "Memory-mapped loads",
        (
            "mmap_load",
            "search_first_mmap",
            "search_warm_mmap",
        ),
    ),
)


def _md_table(
    headers: Sequence[str],
    rows: Sequence[Sequence[str]],
) -> List[str]:
    """Render rows as a Markdown pipe table."""
    table = [
        "| " + " | ".join(headers) + " |",
        "|" + "|".join("---" for _ in headers) + "|",
    ]
    table.extend("| " + " | ".join(row) + " |" for row in rows)
    return table


def _field_table(rows: Sequence[Tuple[str, Any]]) -> List[str]:
    """Render key/value pairs as a two-column Markdown table."""
    return _md_table(
        ("Field", "Value"),
        [(key, str(value)) for key, value in rows],
    )


def _measurement_row(measurement: Dict[str, Any]) -> List[str]:
    """Render one measurement as a standard summary table row."""
    summary = measurement["summary"]
    unit = measurement.get("unit", "ns")
    return [
        str(measurement.get("engine", "-")),
        str(measurement["name"]),
        str(measurement.get("backend", "-")),
        str(measurement.get("query_category", "-")),
        _format_value(unit, summary.get("median")),
        _format_value(unit, summary.get("p95")),
        str(summary.get("count", 0)),
    ]


def _grouped_measurements_section(
    measurements: Sequence[Dict[str, Any]],
) -> List[str]:
    """Render timing and size measurements grouped by scenario."""
    lines: List[str] = []
    headers = (
        "Engine",
        "Metric",
        "Backend",
        "Category",
        "Median",
        "p95",
        "Samples",
    )
    for title, names in _MEASUREMENT_GROUPS:
        wanted = set(names)
        rows = [
            _measurement_row(measurement)
            for measurement in measurements
            if measurement["name"] in wanted
        ]
        if not rows:
            continue
        lines.append(f"## {title}")
        lines.append("")
        lines.extend(_md_table(headers, rows))
        lines.append("")
    return lines


def _memory_section(
    measurements: Sequence[Dict[str, Any]],
) -> List[str]:
    """Render memory measurements with scope and availability status."""
    rows: List[List[str]] = []
    for measurement in measurements:
        if not measurement["name"].startswith("memory_"):
            continue
        summary = measurement["summary"]
        rows.append(
            [
                str(measurement.get("engine", "-")),
                str(measurement.get("phase", "-")),
                str(measurement["name"]),
                str(measurement.get("scope", "-")),
                _format_value(
                    measurement.get("unit", "bytes"),
                    summary.get("median"),
                ),
                str(measurement.get("status", "ok")),
            ]
        )
    if not rows:
        return []
    return [
        "## Memory",
        "",
        "RSS values are process readings, not exclusive ownership. `n/a` "
        "marks capabilities unavailable on this host; they are never "
        "reported as zero.",
        "",
        *_md_table(
            ("Engine", "Phase", "Metric", "Scope", "Value", "Status"),
            rows,
        ),
        "",
    ]


def _roundtrip_section(
    measurements: Sequence[Dict[str, Any]],
) -> List[str]:
    """Render per-backend round-trip verification results."""
    rows = [
        [
            str(measurement.get("engine", "-")),
            str(measurement.get("backend", "-")),
            _format_value("count", measurement["summary"].get("median")),
        ]
        for measurement in measurements
        if measurement["name"] == "roundtrip_verified"
    ]
    if not rows:
        return []
    return [
        "## Round-trip verification",
        "",
        "Each loaded index returned the same documents, in the same "
        "ranking order, with the same scores as the freshly built index "
        "for every query.",
        "",
        *_md_table(("Engine", "Backend", "Verified queries"), rows),
        "",
    ]


def _limitations_section(
    measurements: Sequence[Dict[str, Any]],
) -> List[str]:
    """Render fixed caveats plus every limitation recorded by the run."""
    collected = sorted(
        {
            limitation
            for measurement in measurements
            for limitation in measurement.get("limitations", [])
        }
    )
    fixed = [
        "Search latencies use the public `Lucis.search` boundary and "
        "include query preprocessing and response wrapping.",
        "The load phase starts in a fresh process after build, but JSON, "
        "SQLite, and mmap are measured sequentially in that process; the "
        "OS page cache is not controlled.",
        "Tree RSS sums resident pages shared by fork (copy-on-write), "
        "so it can overstate exclusive usage.",
        "Sampling-based peaks can miss shorter-lived worker processes.",
    ]
    lines = ["## Limitations", ""]
    lines.extend(f"- {note}" for note in [*fixed, *collected])
    lines.append("")
    return lines


def render_markdown_report(result: Dict[str, Any]) -> str:
    """Render one saved benchmark result as a Markdown document.

    Args:
        result: Valid result dictionary, typically loaded from a
            ``lucis-benchmark-*.json`` file.

    Returns:
        Markdown text with run identity, environment, dataset hashes,
        grouped measurement tables, memory scope, round-trip verification,
        and explicit limitations.
    """
    measurements = result.get("measurements", [])
    environment = result.get("environment", {})
    configuration = result.get("configuration", {})

    lines: List[str] = [
        "# Lucis benchmark report",
        "",
        "> These results describe one machine and one execution "
        "environment. They",
        "> are not search-quality measurements or universal performance "
        "guarantees.",
        "",
        "## Run",
        "",
        *_field_table(
            [
                ("Run ID", result.get("run_id", "n/a")),
                ("Started (UTC)", result.get("started_at_utc", "n/a")),
                ("Finished (UTC)", result.get("finished_at_utc", "n/a")),
                ("Schema version", result.get("schema_version", "n/a")),
            ]
        ),
        "",
        "## Environment",
        "",
        *_field_table(
            [
                (key, environment.get(key, "n/a"))
                for key in (
                    "python_version",
                    "python_implementation",
                    "platform",
                    "machine",
                    "logical_cpu_count",
                    "lucis_version",
                    "git_commit",
                    "git_dirty",
                )
            ]
        ),
        "",
        "## Configuration",
        "",
        *_field_table(
            [
                (key, configuration.get(key, "n/a"))
                for key in (
                    "profile",
                    "engines",
                    "warmups",
                    "repetitions",
                    "require_memory",
                )
            ]
        ),
        "",
    ]

    datasets = result.get("datasets", [])
    if datasets:
        dataset = datasets[0]
        lines.append("## Dataset and queries")
        lines.append("")
        lines.extend(
            _field_table(
                [
                    (key, dataset.get(key, "n/a"))
                    for key in (
                        "profile",
                        "generator_version",
                        "seed",
                        "documents",
                        "total_tokens",
                        "vocabulary_nominal",
                        "vocabulary_observed",
                        "intentional_duplicates",
                        "sha256",
                    )
                ]
            )
        )
        queries = result.get("queries")
        if isinstance(queries, dict):
            lines.append("")
            lines.extend(
                _field_table(
                    [
                        ("query_set_version", queries.get("version", "n/a")),
                        ("query_count", queries.get("queries", "n/a")),
                        ("queries_sha256", queries.get("sha256", "n/a")),
                    ]
                )
            )
        lines.append("")

    lines.extend(_grouped_measurements_section(measurements))
    lines.extend(_memory_section(measurements))
    lines.extend(_roundtrip_section(measurements))
    lines.extend(_limitations_section(measurements))

    return "\n".join(lines).rstrip("\n") + "\n"
