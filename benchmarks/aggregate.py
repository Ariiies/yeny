"""Reproducible aggregation of several official benchmark runs.

The aggregator combines compatible result JSON files without manual
transcription. Runs are only merged when they share the full campaign
fingerprint (schema, Lucis version, commit, Python minor version, profile,
dataset/query hashes, engines, warm-ups, repetitions, and memory
requirement). Different operating systems or machines are always kept in
separate groups, never blended into a single figure.

Published statistics between runs are deliberately simple: the headline
value is the median of per-run medians, variability is the minimum and
maximum of those medians, and the published p95 is the median of per-run
p95 values. No outliers are discarded; variability above 20% is a warning
for manual review, not an automatic failure.
"""

from __future__ import annotations

import json
import statistics
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

from .reporting import format_bytes, format_duration
from .results import validate_result


AGGREGATE_SCHEMA_VERSION = "1.0"
VARIABILITY_WARNING_THRESHOLD = 0.20


class AggregateError(RuntimeError):
    """Raised when benchmark runs cannot be aggregated together."""


def load_run(path: Path) -> Dict[str, Any]:
    """Read and deeply validate one benchmark result file.

    Args:
        path: Result JSON produced by ``python -m benchmarks run``.

    Returns:
        Validated result dictionary.

    Raises:
        AggregateError: If the file cannot be read or fails validation.
    """
    try:
        with path.open("r", encoding="utf-8") as stream:
            payload = json.load(stream)
    except (OSError, json.JSONDecodeError) as exc:
        raise AggregateError(f"cannot read {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise AggregateError(f"{path} must contain a JSON object")
    try:
        validate_result(payload)
    except ValueError as exc:
        raise AggregateError(f"{path} is not a valid result: {exc}") from exc
    return payload


def _python_minor(version: Any) -> Optional[str]:
    """Reduce a Python version string to its ``major.minor`` prefix."""
    if not isinstance(version, str):
        return None
    parts = version.split(".")
    if len(parts) < 2:
        return version
    return f"{parts[0]}.{parts[1]}"


def run_fingerprint(result: Mapping[str, Any]) -> Dict[str, Any]:
    """Extract the compatibility fingerprint of one benchmark run.

    Args:
        result: Validated result dictionary.

    Returns:
        Mapping with every field that must match across aggregated runs.
    """
    environment = result["environment"]
    configuration = result["configuration"]
    return {
        "schema_version": result["schema_version"],
        "lucis_version": environment.get("lucis_version"),
        "git_commit": environment.get("git_commit"),
        "python_minor": _python_minor(environment.get("python_version")),
        "profile": configuration["profile"],
        "dataset_sha256": result["datasets"][0]["sha256"],
        "queries_sha256": result["queries"]["sha256"],
        "engines": tuple(sorted(configuration["engines"])),
        "warmups": configuration["warmups"],
        "repetitions": configuration["repetitions"],
        "require_memory": configuration["require_memory"],
    }


def _check_compatibility(results: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    """Verify that all runs share one campaign fingerprint.

    Args:
        results: Validated result dictionaries.

    Returns:
        The shared fingerprint.

    Raises:
        AggregateError: If any fingerprint field differs between runs.
            The message names every incompatible field and the runs
            involved.
    """
    fingerprints = [run_fingerprint(result) for result in results]
    reference = fingerprints[0]
    problems: List[str] = []
    for field in reference:
        values = {
            fingerprint[field] for fingerprint in fingerprints
        }
        if len(values) > 1:
            per_run = ", ".join(
                f"{result['run_id']}={fingerprint[field]!r}"
                for result, fingerprint in zip(results, fingerprints)
            )
            problems.append(f"{field} ({per_run})")
    if problems:
        raise AggregateError(
            "incompatible benchmark runs cannot be aggregated: "
            + "; ".join(problems)
        )
    return reference


def _group_key(result: Mapping[str, Any]) -> Tuple[Any, Any, Any]:
    """Build the environment grouping key for one run."""
    environment = result["environment"]
    cpu = environment.get("cpu_model") or environment.get("processor")
    return (
        environment.get("system"),
        environment.get("machine"),
        cpu,
    )


def _measurement_key(
    measurement: Mapping[str, Any],
) -> Tuple[Any, ...]:
    """Build the aggregation key for one measurement context."""
    return (
        measurement.get("engine"),
        measurement["name"],
        measurement.get("backend"),
        measurement.get("query_category"),
        measurement.get("phase"),
    )


def _aggregate_group(
    results: Sequence[Mapping[str, Any]],
    key: Tuple[Any, Any, Any],
) -> Tuple[Dict[str, Any], List[str]]:
    """Aggregate every metric of one environment group.

    Args:
        results: Runs belonging to the group, in input order.
        key: Environment grouping key.

    Returns:
        Tuple with the group summary and its warnings.
    """
    warnings: List[str] = []
    system, machine, cpu = key
    if cpu is None:
        warnings.append(
            f"group {system}/{machine}: cpu model metadata is missing"
        )
    if any(
        result["environment"].get("total_ram_bytes") is None
        for result in results
    ):
        warnings.append(
            f"group {system}/{machine}: total RAM metadata is missing"
        )
    dirty = [
        result["run_id"]
        for result in results
        if result["environment"].get("git_dirty")
    ]
    if dirty:
        warnings.append(
            "runs produced with a dirty Git tree: " + ", ".join(sorted(dirty))
        )

    contexts: Dict[Tuple[Any, ...], List[Mapping[str, Any]]] = {}
    units: Dict[Tuple[Any, ...], str] = {}
    for result in results:
        for measurement in result["measurements"]:
            context = _measurement_key(measurement)
            contexts.setdefault(context, []).append(measurement)
            units[context] = measurement.get("unit", "ns")

    metrics: List[Dict[str, Any]] = []
    for context in sorted(contexts, key=lambda item: tuple(str(v) for v in item)):
        entries = contexts[context]
        medians = [
            entry["summary"]["median"]
            for entry in entries
            if entry["summary"]["median"] is not None
        ]
        p95s = [
            entry["summary"]["p95"]
            for entry in entries
            if entry["summary"]["p95"] is not None
        ]
        engine, name, backend, category, phase = context
        metric: Dict[str, Any] = {
            "engine": engine,
            "name": name,
            "backend": backend,
            "query_category": category,
            "phase": phase,
            "unit": units[context],
            "runs": len(entries),
        }
        if not medians:
            metric.update(
                {
                    "status": "unavailable",
                    "median": None,
                    "median_min": None,
                    "median_max": None,
                    "p95": None,
                }
            )
        else:
            median = float(statistics.median(medians))
            metric.update(
                {
                    "status": "ok",
                    "median": median,
                    "median_min": float(min(medians)),
                    "median_max": float(max(medians)),
                    "p95": float(statistics.median(p95s)) if p95s else None,
                }
            )
            if median > 0:
                variability = (max(medians) - min(medians)) / median
                if variability > VARIABILITY_WARNING_THRESHOLD:
                    warnings.append(
                        f"high variability ({variability:.0%}) in "
                        f"{engine}/{name}"
                        + (f"/{backend}" if backend else "")
                        + (f"/{category}" if category else "")
                        + ": manual review recommended"
                    )
        metrics.append(metric)

    group = {
        "system": system,
        "machine": machine,
        "cpu_model": cpu,
        "runs": len(results),
        "run_ids": sorted(result["run_id"] for result in results),
        "metrics": metrics,
    }
    return group, warnings


def aggregate_results(
    results: Sequence[Mapping[str, Any]],
    *,
    sources: Optional[Sequence[str]] = None,
) -> Dict[str, Any]:
    """Aggregate compatible benchmark runs into one traceable summary.

    Args:
        results: Validated result dictionaries. At least one is required.
        sources: Optional origin labels (usually file paths) parallel to
            ``results``; stored next to each run ID for traceability.

    Returns:
        Aggregate document with the shared fingerprint, sources, groups,
        and warnings. Groups are sorted so equal inputs produce equal
        outputs.

    Raises:
        AggregateError: If no runs are given or the runs are incompatible.
    """
    if not results:
        raise AggregateError("at least one benchmark result is required")
    fingerprint = _check_compatibility(results)
    fingerprint = {
        key: (list(value) if isinstance(value, tuple) else value)
        for key, value in fingerprint.items()
    }

    grouped: Dict[Tuple[Any, Any, Any], List[Mapping[str, Any]]] = {}
    for result in results:
        grouped.setdefault(_group_key(result), []).append(result)

    groups: List[Dict[str, Any]] = []
    warnings: List[str] = []
    for key in sorted(grouped, key=lambda item: tuple(str(v) for v in item)):
        group, group_warnings = _aggregate_group(grouped[key], key)
        groups.append(group)
        warnings.extend(group_warnings)

    origin = sources if sources is not None else [None] * len(results)
    return {
        "schema_version": AGGREGATE_SCHEMA_VERSION,
        "kind": "lucis-benchmark-aggregate",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "fingerprint": fingerprint,
        "sources": [
            {"run_id": result["run_id"], "path": source}
            for result, source in zip(results, origin)
        ],
        "groups": groups,
        "warnings": sorted(warnings),
    }


def _format_metric_value(unit: str, value: Optional[float]) -> str:
    """Format one aggregated metric value for the Markdown table."""
    if value is None:
        return "n/a"
    if unit == "bytes":
        return format_bytes(value)
    if unit == "count":
        return str(int(value))
    return format_duration(value)


def render_aggregate_markdown(aggregate: Mapping[str, Any]) -> str:
    """Render one aggregate document as a readable Markdown summary.

    Args:
        aggregate: Document produced by :func:`aggregate_results`.

    Returns:
        Markdown text with the shared fingerprint, one metrics table per
        environment group, sources, and warnings.
    """
    fingerprint = aggregate["fingerprint"]
    lines: List[str] = [
        "# Lucis benchmark aggregate",
        "",
        "> Aggregated medians of compatible runs. Each environment group is",
        "> reported separately; figures from different systems or machines",
        "> are never merged.",
        "",
        "## Shared configuration",
        "",
        "| Field | Value |",
        "|---|---|",
        f"| profile | {fingerprint['profile']} |",
        f"| engines | {', '.join(fingerprint['engines'])} |",
        f"| warmups | {fingerprint['warmups']} |",
        f"| repetitions | {fingerprint['repetitions']} |",
        f"| require_memory | {fingerprint['require_memory']} |",
        f"| lucis_version | {fingerprint['lucis_version']} |",
        f"| python | {fingerprint['python_minor']} |",
        f"| git_commit | {fingerprint['git_commit']} |",
        f"| dataset_sha256 | {fingerprint['dataset_sha256']} |",
        f"| queries_sha256 | {fingerprint['queries_sha256']} |",
        "",
    ]

    headers = (
        "Engine",
        "Metric",
        "Backend",
        "Category",
        "Phase",
        "Median",
        "Min",
        "Max",
        "p95",
        "Runs",
    )
    for group in aggregate["groups"]:
        title = f"{group['system']} / {group['machine']}"
        if group.get("cpu_model"):
            title += f" / {group['cpu_model']}"
        lines.append(f"## {title}")
        lines.append("")
        lines.append(f"Runs: {group['runs']} ({', '.join(group['run_ids'])})")
        lines.append("")
        lines.append("| " + " | ".join(headers) + " |")
        lines.append("|" + "|".join("---" for _ in headers) + "|")
        for metric in group["metrics"]:
            unit = metric["unit"]
            lines.append(
                "| "
                + " | ".join(
                    [
                        str(metric.get("engine") or "-"),
                        str(metric["name"]),
                        str(metric.get("backend") or "-"),
                        str(metric.get("query_category") or "-"),
                        str(metric.get("phase") or "-"),
                        _format_metric_value(unit, metric["median"]),
                        _format_metric_value(unit, metric["median_min"]),
                        _format_metric_value(unit, metric["median_max"]),
                        _format_metric_value(unit, metric["p95"]),
                        str(metric["runs"]),
                    ]
                )
                + " |"
            )
        lines.append("")

    lines.append("## Sources")
    lines.append("")
    for source in aggregate["sources"]:
        path = source.get("path") or "n/a"
        lines.append(f"- `{source['run_id']}` — {path}")
    lines.append("")

    if aggregate["warnings"]:
        lines.append("## Warnings")
        lines.append("")
        lines.extend(
            f"- {warning}" for warning in aggregate["warnings"]
        )
        lines.append("")

    return "\n".join(lines).rstrip("\n") + "\n"


def write_aggregate(
    aggregate: Mapping[str, Any],
    markdown_path: Path,
) -> Tuple[Path, Path]:
    """Write the aggregate Markdown and JSON without overwriting.

    Args:
        aggregate: Document produced by :func:`aggregate_results`.
        markdown_path: Destination ``.md`` path. The JSON trace is written
            as a sibling with the ``.aggregate.json`` suffix.

    Returns:
        Tuple with the written Markdown and JSON paths.

    Raises:
        AggregateError: If either destination already exists.
        OSError: If the files cannot be written.
    """
    markdown_path = Path(markdown_path)
    json_path = markdown_path.with_suffix(".aggregate.json")
    for target in (markdown_path, json_path):
        if target.exists():
            raise AggregateError(f"Aggregate output already exists: {target}")
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.write_text(
        render_aggregate_markdown(aggregate),
        encoding="utf-8",
    )
    json_path.write_text(
        json.dumps(aggregate, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return markdown_path.resolve(), json_path.resolve()
