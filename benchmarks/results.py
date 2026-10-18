"""Validation and persistence for Yeny benchmark results.

Results are stored as readable JSON and never silently overwrite an earlier
run. Writes use a temporary file followed by ``os.replace`` so readers do not
observe partially-written documents.

Validation is deliberately deep but dependency-free: beyond the top-level
structure it checks timestamps, the frozen dataset/query hashes, raw-sample
versus summary coherence, per-engine metric matrix completeness, and
round-trip fidelity. A result that fails any check must never be accepted
as an official benchmark artifact.
"""

from __future__ import annotations

import json
import math
import os
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping, Optional, Sequence, Set, Tuple

from .config import (
    EXPECTED_GENERATOR_VERSION,
    EXPECTED_QUERY_SET_VERSION,
    load_profiles,
    load_reference_hashes,
)
from .metrics import summarize_samples


SUPPORTED_SCHEMA_VERSION = "1.0"
VALID_UNITS = {"ns", "bytes", "count"}
VALID_ENGINES = {"core", "lite"}
VALID_BACKENDS = {"json", "sqlite", "mmap"}
VALID_PHASES = {"build", "load_json", "load_sqlite", "load_mmap"}
VALID_QUERY_CATEGORIES = {
    "common",
    "rare",
    "multi",
    "no_result",
    "repeated",
}
EXPECTED_QUERY_COUNT = 17
"""Fixed size of the ``queries_v1`` set: four per category plus repeated."""

MEMORY_MEASUREMENT_NAMES = {
    "memory_baseline_rss",
    "memory_peak_rss",
    "memory_peak_rss_delta",
    "memory_stable_rss",
    "memory_max_processes",
}

REQUIRED_RESULT_FIELDS = {
    "schema_version",
    "run_id",
    "started_at_utc",
    "finished_at_utc",
    "environment",
    "configuration",
    "datasets",
    "queries",
    "measurements",
}

_BUILD_PHASE_NAMES = {
    "dataset_generation",
    "index_build",
    "index_e2e_json",
    "search_first",
    "json_save",
    "json_artifact_size",
    "sqlite_save",
    "sqlite_artifact_size",
    "yny_write",
    "yny_artifact_size",
    "mmap_load",
    "search_first_mmap",
}


def _parse_timestamp(value: Any, field: str) -> datetime:
    """Parse one ISO 8601 timestamp with an explicit timezone."""
    if not isinstance(value, str) or not value:
        raise ValueError(f"{field} must be a non-empty string")
    text = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        raise ValueError(
            f"{field} must be an ISO 8601 timestamp: {value!r}"
        ) from None
    if parsed.tzinfo is None:
        raise ValueError(f"{field} must include a timezone: {value!r}")
    return parsed


def _require_sha256(value: Any, field: str) -> str:
    """Validate one lowercase hexadecimal SHA-256 digest."""
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(char not in "0123456789abcdef" for char in value)
    ):
        raise ValueError(f"{field} must be a 64-character lowercase hex hash")
    return value


def _require_non_negative_int(value: Any, field: str) -> None:
    """Validate one non-negative integer field."""
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{field} must be a non-negative integer")


def _validate_top_level(result: Mapping[str, Any]) -> None:
    """Validate required fields and the result schema version."""
    if not isinstance(result, Mapping):
        raise ValueError("result must be an object")

    missing = sorted(REQUIRED_RESULT_FIELDS.difference(result))
    if missing:
        raise ValueError(
            f"result is missing fields: {', '.join(missing)}"
        )
    if result["schema_version"] != SUPPORTED_SCHEMA_VERSION:
        raise ValueError("Unsupported result schema_version")
    if not isinstance(result["run_id"], str) or not result["run_id"]:
        raise ValueError("run_id must be a non-empty string")
    for field in ("environment", "configuration"):
        if not isinstance(result[field], Mapping):
            raise ValueError(f"{field} must be an object")
    for field in ("datasets", "measurements"):
        value = result[field]
        if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
            raise ValueError(f"{field} must be an array")
    if not isinstance(result["queries"], Mapping):
        raise ValueError("queries must be an object")


def _validate_timestamps(result: Mapping[str, Any]) -> None:
    """Validate start/finish timestamps and their ordering."""
    started = _parse_timestamp(result["started_at_utc"], "started_at_utc")
    finished = _parse_timestamp(result["finished_at_utc"], "finished_at_utc")
    if finished < started:
        raise ValueError("finished_at_utc is earlier than started_at_utc")


def _validate_configuration(
    configuration: Mapping[str, Any],
) -> Tuple[str, ...]:
    """Validate the run configuration and return requested engines."""
    profile = configuration.get("profile")
    if profile not in load_profiles():
        raise ValueError(
            f"configuration.profile must be a known profile: {profile!r}"
        )
    engines = configuration.get("engines")
    if (
        isinstance(engines, (str, bytes))
        or not isinstance(engines, Sequence)
        or not engines
    ):
        raise ValueError("configuration.engines must be a non-empty array")
    seen: Set[str] = set()
    for engine in engines:
        if engine not in VALID_ENGINES:
            raise ValueError(
                f"configuration.engines contains an unknown engine: "
                f"{engine!r}"
            )
        if engine in seen:
            raise ValueError(
                f"configuration.engines repeats an engine: {engine!r}"
            )
        seen.add(engine)
    warmups = configuration.get("warmups")
    repetitions = configuration.get("repetitions")
    if isinstance(warmups, bool) or not isinstance(warmups, int) or warmups < 0:
        raise ValueError("configuration.warmups must be a non-negative integer")
    if (
        isinstance(repetitions, bool)
        or not isinstance(repetitions, int)
        or repetitions <= 0
    ):
        raise ValueError("configuration.repetitions must be a positive integer")
    if not isinstance(configuration.get("require_memory"), bool):
        raise ValueError("configuration.require_memory must be a boolean")
    return tuple(str(engine) for engine in engines)


def _validate_dataset(
    datasets: Sequence[Any],
    profile_name: str,
) -> Mapping[str, Any]:
    """Validate the dataset manifest against the frozen reference hashes."""
    if len(datasets) != 1:
        raise ValueError("datasets must contain exactly one dataset manifest")
    dataset = datasets[0]
    if not isinstance(dataset, Mapping):
        raise ValueError("datasets[0] must be an object")
    if dataset.get("profile") != profile_name:
        raise ValueError(
            f"dataset profile {dataset.get('profile')!r} does not match "
            f"the configured profile {profile_name!r}"
        )
    if dataset.get("generator_version") != EXPECTED_GENERATOR_VERSION:
        raise ValueError("dataset generator_version is not supported")

    profile = load_profiles()[profile_name]
    if dataset.get("seed") != profile.seed:
        raise ValueError("dataset seed does not match the profile seed")
    if dataset.get("documents") != profile.documents:
        raise ValueError(
            "dataset documents does not match the profile document count"
        )
    for field in (
        "documents",
        "total_tokens",
        "vocabulary_nominal",
        "vocabulary_observed",
        "intentional_duplicates",
    ):
        _require_non_negative_int(dataset.get(field), f"dataset.{field}")

    sha256 = _require_sha256(dataset.get("sha256"), "dataset.sha256")
    expected = load_reference_hashes()[profile_name]
    if sha256 != expected["dataset_sha256"]:
        raise ValueError(
            "dataset.sha256 does not match the frozen reference hash; "
            "the result cannot be trusted"
        )
    return dataset


def _validate_queries(
    queries: Mapping[str, Any],
    dataset: Mapping[str, Any],
) -> int:
    """Validate the query manifest and return the expected query count."""
    if queries.get("version") != EXPECTED_QUERY_SET_VERSION:
        raise ValueError("queries.version is not supported")
    if queries.get("dataset_sha256") != dataset["sha256"]:
        raise ValueError("query manifest belongs to another dataset")
    if queries.get("queries") != EXPECTED_QUERY_COUNT:
        raise ValueError(
            f"queries.queries must be {EXPECTED_QUERY_COUNT} for "
            f"{EXPECTED_QUERY_SET_VERSION}"
        )
    return EXPECTED_QUERY_COUNT


def _validate_samples(measurement: Mapping[str, Any], name: str) -> None:
    """Validate raw samples and their coherence with the summary."""
    samples = measurement.get("samples")
    if isinstance(samples, (str, bytes)) or not isinstance(samples, Sequence):
        raise ValueError(f"measurement {name!r}: samples must be an array")
    for value in samples:
        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(value)
            or value < 0
        ):
            raise ValueError(
                f"measurement {name!r}: samples must be finite, "
                f"non-negative numbers"
            )

    summary = measurement.get("summary")
    if not isinstance(summary, Mapping):
        raise ValueError(f"measurement {name!r}: summary must be an object")
    missing = {"count", "min", "median", "p95", "max"}.difference(summary)
    if missing:
        raise ValueError(
            f"measurement {name!r}: summary is missing "
            f"{', '.join(sorted(missing))}"
        )

    status = measurement.get("status", "ok")
    if status not in {"ok", "unavailable"}:
        raise ValueError(
            f"measurement {name!r}: status must be 'ok' or 'unavailable'"
        )
    if not samples:
        if status != "unavailable":
            raise ValueError(
                f"measurement {name!r}: empty samples are only allowed "
                f"when status is 'unavailable'"
            )
        if summary["count"] != 0 or any(
            summary[key] is not None
            for key in ("min", "median", "p95", "max")
        ):
            raise ValueError(
                f"measurement {name!r}: an unavailable measurement must "
                f"have count 0 and null summaries"
            )
        return

    expected = summarize_samples([float(value) for value in samples])
    if summary["count"] != len(samples):
        raise ValueError(
            f"measurement {name!r}: summary.count contradicts the samples"
        )
    for key in ("min", "median", "p95", "max"):
        if summary[key] != expected[key]:
            raise ValueError(
                f"measurement {name!r}: summary.{key} contradicts the "
                f"raw samples"
            )


def _validate_context(measurement: Mapping[str, Any], name: str) -> None:
    """Validate engine, backend, phase, and category labels."""
    engine = measurement.get("engine")
    if engine not in VALID_ENGINES:
        raise ValueError(
            f"measurement {name!r}: engine must be one of "
            f"{sorted(VALID_ENGINES)}"
        )
    backend = measurement.get("backend")
    if backend is not None and backend not in VALID_BACKENDS:
        raise ValueError(
            f"measurement {name!r}: unknown backend {backend!r}"
        )
    phase = measurement.get("phase")
    if phase is not None and phase not in VALID_PHASES:
        raise ValueError(
            f"measurement {name!r}: unknown phase {phase!r}"
        )
    category = measurement.get("query_category")
    if category is not None and category not in VALID_QUERY_CATEGORIES:
        raise ValueError(
            f"measurement {name!r}: unknown query category {category!r}"
        )
    if name in MEMORY_MEASUREMENT_NAMES and phase is None:
        raise ValueError(
            f"measurement {name!r}: memory measurements must declare "
            f"their phase"
        )


def _context_key(measurement: Mapping[str, Any]) -> Tuple[Any, ...]:
    """Build the uniqueness key for one measurement context."""
    return (
        measurement.get("engine"),
        measurement["name"],
        measurement.get("backend"),
        measurement.get("query_category"),
        measurement.get("phase"),
    )


def _validate_metric_matrix(
    measurements: Sequence[Mapping[str, Any]],
    engines: Tuple[str, ...],
    query_count: int,
) -> None:
    """Validate per-engine matrix completeness and round-trip fidelity."""
    found_engines = {measurement["engine"] for measurement in measurements}
    if found_engines != set(engines):
        raise ValueError(
            f"measurement engines {sorted(found_engines)} do not match "
            f"the requested engines {sorted(engines)}"
        )

    seen_contexts: Set[Tuple[Any, ...]] = set()
    for measurement in measurements:
        key = _context_key(measurement)
        if key in seen_contexts:
            raise ValueError(
                f"duplicated measurement context: "
                f"engine={key[0]} name={key[1]} backend={key[2]} "
                f"category={key[3]} phase={key[4]}"
            )
        seen_contexts.add(key)

    for engine in engines:
        own = [
            measurement
            for measurement in measurements
            if measurement["engine"] == engine
        ]
        names = {measurement["name"] for measurement in own}
        missing = sorted(_BUILD_PHASE_NAMES.difference(names))
        if missing:
            raise ValueError(
                f"engine {engine!r} is missing required measurements: "
                f"{', '.join(missing)}"
            )

        warm_categories = {
            measurement.get("query_category")
            for measurement in own
            if measurement["name"] == "search_warm"
        }
        if warm_categories != VALID_QUERY_CATEGORIES:
            raise ValueError(
                f"engine {engine!r}: search_warm must cover every query "
                f"category"
            )

        for backend in ("json", "sqlite"):
            load_names = {
                measurement["name"]
                for measurement in own
                if measurement.get("backend") == backend
            }
            for required in (
                "load_standard",
                "search_first_after_load",
                "search_warm_after_load",
                "roundtrip_verified",
            ):
                if required not in load_names:
                    raise ValueError(
                        f"engine {engine!r} backend {backend!r} is "
                        f"missing {required}"
                    )
            after_load_categories = {
                measurement.get("query_category")
                for measurement in own
                if measurement["name"] == "search_warm_after_load"
                and measurement.get("backend") == backend
            }
            if after_load_categories != VALID_QUERY_CATEGORIES:
                raise ValueError(
                    f"engine {engine!r} backend {backend!r}: "
                    f"search_warm_after_load must cover every category"
                )

        mmap_categories = {
            measurement.get("query_category")
            for measurement in own
            if measurement["name"] == "search_warm_mmap"
        }
        if mmap_categories != VALID_QUERY_CATEGORIES:
            raise ValueError(
                f"engine {engine!r}: search_warm_mmap must cover every "
                f"query category"
            )

        roundtrips = {
            measurement.get("backend"): measurement
            for measurement in own
            if measurement["name"] == "roundtrip_verified"
        }
        if set(roundtrips) != VALID_BACKENDS:
            raise ValueError(
                f"engine {engine!r}: roundtrip_verified must exist for "
                f"json, sqlite, and mmap"
            )
        for backend, measurement in roundtrips.items():
            if list(measurement["samples"]) != [query_count]:
                raise ValueError(
                    f"engine {engine!r} backend {backend!r}: "
                    f"roundtrip_verified must equal the query count "
                    f"({query_count})"
                )

        memory_phases = {
            (measurement["name"], measurement.get("phase"))
            for measurement in own
            if measurement["name"] in MEMORY_MEASUREMENT_NAMES
        }
        expected_memory = {
            (name, phase)
            for name in MEMORY_MEASUREMENT_NAMES
            for phase in VALID_PHASES
        }
        if memory_phases != expected_memory:
            raise ValueError(
                f"engine {engine!r}: memory measurements must cover "
                f"every metric and phase (build, load_json, load_sqlite, "
                f"load_mmap)"
            )


def validate_result(result: Mapping[str, Any]) -> None:
    """Validate the full result contract without extra dependencies.

    The check covers the top-level structure, timestamp ordering, the
    configured engines, the frozen dataset/query hashes, raw-sample versus
    summary coherence, per-engine metric matrix completeness, and
    round-trip fidelity for all three persistence backends.

    Args:
        result: Result object to validate.

    Raises:
        ValueError: If any part of the contract is violated. Messages are
            written to be actionable by the person running the campaign.
    """
    _validate_top_level(result)
    _validate_timestamps(result)
    engines = _validate_configuration(result["configuration"])
    dataset = _validate_dataset(
        result["datasets"],
        str(result["configuration"]["profile"]),
    )
    query_count = _validate_queries(result["queries"], dataset)

    measurements = result["measurements"]
    if not measurements:
        raise ValueError("measurements must not be empty")
    for measurement in measurements:
        if not isinstance(measurement, Mapping):
            raise ValueError("each measurement must be an object")
        name = measurement.get("name")
        if not isinstance(name, str) or not name:
            raise ValueError("each measurement must have a name")
        if measurement.get("unit") not in VALID_UNITS:
            raise ValueError(
                f"measurement {name!r}: unit must be one of "
                f"{sorted(VALID_UNITS)}"
            )
        _validate_context(measurement, name)
        _validate_samples(measurement, name)
    _validate_metric_matrix(measurements, engines, query_count)


def _write_atomically(target: Path, text: str) -> None:
    """Write text through a temporary sibling plus ``os.replace``."""
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{target.stem}-",
        suffix=".tmp",
        dir=str(target.parent),
        text=True,
    )
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            stream.write(text)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary_path, target)
    except Exception:
        try:
            temporary_path.unlink()
        except FileNotFoundError:
            pass
        raise


def write_report(markdown: str, result_path: Path) -> Path:
    """Atomically write a Markdown report next to its JSON result.

    Args:
        markdown: Rendered Markdown report text.
        result_path: Path of the JSON result the report belongs to.

    Returns:
        Absolute path of the created ``.md`` file.

    Raises:
        ValueError: If the report file already exists.
        OSError: If the file cannot be written.
    """
    target = result_path.with_suffix(".md")
    if target.exists():
        raise ValueError(f"Report already exists: {target}")
    _write_atomically(target, markdown)
    return target.resolve()


def write_result(
    result: Mapping[str, Any],
    output_dir: Path,
) -> Path:
    """Atomically write one benchmark result as JSON.

    Args:
        result: Validated benchmark result.
        output_dir: Destination directory.

    Returns:
        Absolute path to the created JSON file.

    Raises:
        ValueError: If the result is invalid or the destination already
            exists.
        OSError: If the directory or file cannot be created.
    """
    validate_result(result)
    output_dir.mkdir(parents=True, exist_ok=True)
    target = output_dir / f"yeny-benchmark-{result['run_id']}.json"
    if target.exists():
        raise ValueError(f"Result already exists: {target}")

    descriptor, temporary_name = tempfile.mkstemp(
        prefix=".yeny-benchmark-",
        suffix=".tmp",
        dir=str(output_dir),
        text=True,
    )
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            json.dump(result, stream, indent=2, ensure_ascii=False)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary_path, target)
    except Exception:
        try:
            temporary_path.unlink()
        except FileNotFoundError:
            pass
        raise
    return target.resolve()
