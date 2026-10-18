"""Shared builders for fully valid benchmark result fixtures.

The deep result contract requires a complete metric matrix per engine plus
the frozen dataset/query hashes, so tests build their documents through
these helpers instead of hand-writing partial JSON.
"""

from __future__ import annotations

from benchmarks.config import load_profiles, load_reference_hashes
from benchmarks.metrics import summarize_samples
from benchmarks.results import (
    EXPECTED_QUERY_COUNT,
    MEMORY_MEASUREMENT_NAMES,
    VALID_PHASES,
    VALID_QUERY_CATEGORIES,
)


def build_measurement(name, samples=(1_000,), **context):
    """Build one measurement whose summary always matches its samples."""
    raw = list(samples)
    unit = context.pop("unit", "ns")
    return {
        "name": name,
        "unit": unit,
        "samples": raw,
        "summary": summarize_samples([float(value) for value in raw]),
        **context,
    }


def build_measurements(engine, query_count=EXPECTED_QUERY_COUNT):
    """Build the complete per-engine metric matrix required by the contract."""
    measurements = []

    def add(name, samples=(1_000,), **context):
        measurements.append(
            build_measurement(name, samples, engine=engine, **context)
        )

    for name in ("dataset_generation", "index_build", "index_e2e_json"):
        add(name)
    add("search_first", query_category="common")
    for category in sorted(VALID_QUERY_CATEGORIES):
        add("search_warm", query_category=category)
    add("json_save")
    add("json_artifact_size", unit="bytes")
    add("sqlite_save")
    add("sqlite_artifact_size", unit="bytes")
    add("yny_write")
    add("yny_artifact_size", unit="bytes")
    for backend in ("json", "sqlite"):
        add("load_standard", backend=backend)
        add(
            "search_first_after_load",
            backend=backend,
            query_category="common",
        )
        for category in sorted(VALID_QUERY_CATEGORIES):
            add(
                "search_warm_after_load",
                backend=backend,
                query_category=category,
            )
    add("mmap_load")
    add("search_first_mmap", query_category="common")
    for category in sorted(VALID_QUERY_CATEGORIES):
        add("search_warm_mmap", query_category=category)
    for backend in ("json", "sqlite", "mmap"):
        add(
            "roundtrip_verified",
            (query_count,),
            unit="count",
            backend=backend,
        )
    for phase in sorted(VALID_PHASES):
        for name in sorted(MEMORY_MEASUREMENT_NAMES):
            unit = "count" if name == "memory_max_processes" else "bytes"
            add(name, unit=unit, phase=phase, scope="process_tree")
    return measurements


def build_valid_result(engines=("core",), profile="tiny"):
    """Build a result document that satisfies the full deep contract."""
    profile_config = load_profiles()[profile]
    reference = load_reference_hashes()[profile]
    return {
        "schema_version": "1.0",
        "run_id": "20260729T120000Z-abc123",
        "started_at_utc": "2026-07-29T12:00:00+00:00",
        "finished_at_utc": "2026-07-29T12:01:00+00:00",
        "environment": {
            "python_version": "3.12.3",
            "python_implementation": "CPython",
            "platform": "Linux-7.0",
            "system": "Linux",
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
            "profile": profile,
            "engines": list(engines),
            "warmups": 3,
            "repetitions": 10,
            "require_memory": False,
        },
        "datasets": [
            {
                "profile": profile,
                "generator_version": "lexical_zipf_v1",
                "seed": profile_config.seed,
                "documents": profile_config.documents,
                "total_tokens": 6400,
                "vocabulary_nominal": 2048,
                "vocabulary_observed": 1900,
                "intentional_duplicates": 2,
                "sha256": reference["dataset_sha256"],
            }
        ],
        "queries": {
            "version": "queries_v1",
            "dataset_sha256": reference["dataset_sha256"],
            "queries": EXPECTED_QUERY_COUNT,
            "sha256": reference["queries_sha256"],
        },
        "measurements": [
            measurement
            for engine in engines
            for measurement in build_measurements(engine)
        ],
    }
