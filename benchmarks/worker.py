"""Isolated benchmark worker for one Lucis engine.

The parent runner starts this module twice per engine in fresh Python
processes. The ``build`` phase generates the deterministic corpus, builds a
controlled-word index, runs search measurements, and persists JSON, SQLite,
and ``.lcs`` artifacts. The ``load`` phase reloads those artifacts in a new
interpreter and verifies that result IDs survive every round-trip. Workers
never write inside ``src/``.

This module is an internal implementation detail. Users should invoke
``python -m benchmarks run`` instead.
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List

from lucis import Lucis
from lucis.utils.nlp import word_tokenizer

from .config import (
    BenchmarkProfile,
    load_profiles,
    load_reference_hashes,
)
from .datasets import GeneratedDataset, generate_dataset
from .memory import collect_self_memory
from .metrics import make_measurement, measure_once, measure_operation
from .queries import QuerySpec, build_queries
from .scenarios.mmap_load import measure_lcs_write, measure_mmap_load
from .scenarios.persistence import (
    measure_json_save,
    measure_sqlite_save,
    measure_standard_load,
)
from .scenarios.roundtrip import collect_result_sequence


@dataclass(frozen=True)
class _RequestContext:
    """Validated fields shared by both worker phases.

    Attributes:
        profile: Validated deterministic dataset profile.
        engine: Engine key, either ``"core"`` or ``"lite"``.
        warmups: Unmeasured searches executed before each query.
        repetitions: Measured searches per non-repeated query.
        workspace: Per-engine directory shared by the build and load
            phases inside one temporary tree.
    """

    profile: BenchmarkProfile
    engine: str
    warmups: int
    repetitions: int
    workspace: Path


def _read_json_object(path: Path) -> Dict[str, Any]:
    """Read one JSON object from disk."""
    with path.open("r", encoding="utf-8") as stream:
        payload = json.load(stream)
    if not isinstance(payload, dict):
        raise ValueError(f"Expected a JSON object: {path}")
    return payload


def _write_json_object(path: Path, payload: Dict[str, Any]) -> None:
    """Write one JSON object as UTF-8 JSON."""
    with path.open("w", encoding="utf-8") as stream:
        json.dump(payload, stream, indent=2, ensure_ascii=False)
        stream.write("\n")


def _parse_request(request: Dict[str, Any]) -> _RequestContext:
    """Validate the fields shared by both worker phases.

    Args:
        request: JSON-compatible worker request.

    Returns:
        Validated, immutable request context.

    Raises:
        ValueError: If the profile or engine is unknown, or the repetition
            values are invalid.
    """
    profiles = load_profiles()
    profile_name = str(request["profile"])
    if profile_name not in profiles:
        raise ValueError(f"Unknown benchmark profile: {profile_name}")

    engine = str(request["engine"])
    if engine not in {"core", "lite"}:
        raise ValueError(f"Unknown Lucis engine: {engine}")

    warmups = int(request["warmups"])
    repetitions = int(request["repetitions"])
    if warmups < 0:
        raise ValueError("warmups cannot be negative")
    if repetitions <= 0:
        raise ValueError("repetitions must be greater than zero")

    workspace = Path(request["workspace"]).resolve()
    workspace.mkdir(parents=True, exist_ok=True)

    return _RequestContext(
        profile=profiles[profile_name],
        engine=engine,
        warmups=warmups,
        repetitions=repetitions,
        workspace=workspace,
    )


def _warm_search(
    lucis: Lucis,
    query: QuerySpec,
    warmups: int,
) -> None:
    """Run unmeasured warm-up searches for one query."""
    for _ in range(warmups):
        lucis.search(query.text, top_k=10)


def _verify_reference_hashes(
    context: _RequestContext,
    dataset: GeneratedDataset,
    queries_sha256: str,
) -> None:
    """Compare generated hashes against the frozen campaign contract.

    Args:
        context: Validated worker request fields.
        dataset: Freshly generated deterministic corpus.
        queries_sha256: Hash of the freshly built query set.

    Raises:
        RuntimeError: If the profile's dataset or query hash differs from
            the frozen reference. A mismatch blocks the campaign and must
            be investigated, never silenced.
    """
    expected = load_reference_hashes().get(context.profile.name)
    if expected is None:
        raise RuntimeError(
            f"Profile {context.profile.name!r} has no frozen reference hash"
        )
    actual = {
        "dataset_sha256": dataset.manifest.sha256,
        "queries_sha256": queries_sha256,
    }
    for field, expected_value in expected.items():
        if actual[field] != expected_value:
            raise RuntimeError(
                f"{field} mismatch for profile "
                f"{context.profile.name!r}: campaign blocked. Expected "
                f"{expected_value}, generated {actual[field]}. Investigate "
                f"the deterministic operation that diverges."
            )


def _execute_build_phase(context: _RequestContext) -> Dict[str, Any]:
    """Run construction, search, and persistence for one engine.

    The phase also records the expected per-query result IDs that the load
    phase uses to prove round-trip fidelity.

    Args:
        context: Validated worker request fields.

    Returns:
        JSON-compatible response with dataset/query manifests and all
        build-phase measurements.

    Raises:
        RuntimeError: If a generated present query unexpectedly finds no
            results, or the corpus diverges from the frozen hashes.
    """
    engine = context.engine
    dataset, generation_elapsed = measure_once(
        lambda: generate_dataset(context.profile)
    )
    queries = build_queries(dataset)
    _verify_reference_hashes(context, dataset, queries.manifest.sha256)
    measurements: List[Dict[str, Any]] = [
        make_measurement(
            "dataset_generation",
            [generation_elapsed],
            engine=engine,
        )
    ]

    build_instance = Lucis(
        name=f"benchmark_{engine}_build",
        engine=engine,
        storage_dir=str(context.workspace / "build"),
        preprocessor=word_tokenizer,
        autoload=False,
        binary_dir=None,
    )
    build_samples = measure_operation(
        lambda: build_instance.index(dataset.documents, persist=False)
    )
    measurements.append(
        make_measurement("index_build", build_samples, engine=engine)
    )

    e2e_holder: List[Lucis] = []

    def _index_e2e() -> None:
        e2e_holder.append(
            Lucis.from_dict(
                dataset.documents,
                name=f"benchmark_{engine}_e2e",
                engine=engine,
                storage_dir=str(context.workspace / "e2e"),
                preprocessor=word_tokenizer,
                binary_dir=None,
            )
        )

    e2e_samples = measure_operation(_index_e2e)
    measurements.append(
        make_measurement("index_e2e_json", e2e_samples, engine=engine)
    )

    first_query = queries.items[0]
    cold_samples = measure_operation(
        lambda: build_instance.search(first_query.text, top_k=10)
    )
    measurements.append(
        make_measurement(
            "search_first",
            cold_samples,
            engine=engine,
            query_category=first_query.category,
        )
    )

    category_samples: Dict[str, List[int]] = {}
    for query in queries.items:
        validation = build_instance.search(query.text, top_k=10)
        if query.category == "no_result":
            if validation.results:
                raise RuntimeError(
                    f"No-result query {query.query_id!r} returned matches"
                )
        elif not validation.results:
            raise RuntimeError(
                f"Present query {query.query_id!r} returned no matches"
            )

        _warm_search(build_instance, query, context.warmups)
        measured_repetitions = (
            query.repetitions
            if query.category == "repeated"
            else context.repetitions
        )
        samples = measure_operation(
            lambda query_text=query.text: build_instance.search(
                query_text,
                top_k=10,
            ),
            repetitions=measured_repetitions,
        )
        category_samples.setdefault(query.category, []).extend(samples)

    for category, samples in category_samples.items():
        measurements.append(
            make_measurement(
                "search_warm",
                samples,
                engine=engine,
                query_category=category,
            )
        )

    expected_results = collect_result_sequence(build_instance, queries)
    _write_json_object(
        context.workspace / "expected_results.json",
        {
            "engine": engine,
            "profile": context.profile.name,
            "dataset_sha256": dataset.manifest.sha256,
            "results": expected_results,
        },
    )

    measurements.extend(measure_json_save(build_instance, engine=engine))

    sqlite_dir = context.workspace / "sqlite"
    sqlite_dir.mkdir(parents=True, exist_ok=True)
    sqlite_instance = Lucis(
        name=f"benchmark_{engine}_sqlite",
        engine=engine,
        storage_type="sqlite",
        db_path=str(sqlite_dir / "benchmark.db"),
        preprocessor=word_tokenizer,
        autoload=False,
        binary_dir=None,
    )
    sqlite_instance.index(dataset.documents, persist=False)
    measurements.extend(measure_sqlite_save(sqlite_instance, engine=engine))
    sqlite_instance.storage.close()

    lcs_path = context.workspace / "lcs" / f"benchmark_{engine}.lcs"
    measurements.extend(
        measure_lcs_write(build_instance, lcs_path, engine=engine)
    )

    build_instance.close()
    for instance in e2e_holder:
        instance.close()

    return {
        "engine": engine,
        "profile": context.profile.name,
        "dataset": dataset.manifest.to_dict(),
        "queries": queries.manifest.to_dict(),
        "measurements": measurements,
        "memory": collect_self_memory(),
    }


def _execute_load_phase(context: _RequestContext) -> Dict[str, Any]:
    """Reload persisted artifacts in a fresh interpreter.

    Regenerating the corpus is deterministic and doubles as a cross-process
    determinism check against the build-phase manifest.

    Args:
        context: Validated worker request fields.

    Returns:
        JSON-compatible response with the regenerated dataset hash and all
        load-phase measurements.

    Raises:
        RuntimeError: If the build-phase expectations belong to another
            engine or corpus, or a persistence round-trip changes result
            IDs.
    """
    dataset, _ = measure_once(lambda: generate_dataset(context.profile))
    queries = build_queries(dataset)

    expectations = _read_json_object(
        context.workspace / "expected_results.json"
    )
    if expectations.get("engine") != context.engine:
        raise RuntimeError(
            "Build-phase expectations belong to another engine"
        )
    if expectations.get("dataset_sha256") != dataset.manifest.sha256:
        raise RuntimeError("Dataset hash changed between worker processes")
    expected_results = expectations["results"]

    engine = context.engine
    measurements: List[Dict[str, Any]] = []
    measurements.extend(
        measure_standard_load(
            "json",
            lambda: Lucis(
                name=f"benchmark_{engine}_build",
                engine=engine,
                storage_dir=str(context.workspace / "build"),
                preprocessor=word_tokenizer,
                autoload=True,
                binary_dir=None,
            ),
            engine=engine,
            queries=queries,
            expected_results=expected_results,
            warmups=context.warmups,
            repetitions=context.repetitions,
        )
    )
    measurements.extend(
        measure_standard_load(
            "sqlite",
            lambda: Lucis(
                name=f"benchmark_{engine}_sqlite",
                engine=engine,
                storage_type="sqlite",
                db_path=str(context.workspace / "sqlite" / "benchmark.db"),
                preprocessor=word_tokenizer,
                autoload=True,
                binary_dir=None,
            ),
            engine=engine,
            queries=queries,
            expected_results=expected_results,
            warmups=context.warmups,
            repetitions=context.repetitions,
        )
    )
    measurements.extend(
        measure_mmap_load(
            lambda: Lucis(
                name=f"benchmark_{engine}_mmap",
                engine=engine,
                storage_dir=str(context.workspace / "mmap"),
                preprocessor=word_tokenizer,
                autoload=False,
                binary_dir=None,
            ),
            context.workspace / "lcs" / f"benchmark_{engine}.lcs",
            engine=engine,
            queries=queries,
            expected_results=expected_results,
            warmups=context.warmups,
            repetitions=context.repetitions,
        )
    )

    return {
        "engine": engine,
        "profile": context.profile.name,
        "dataset_sha256": dataset.manifest.sha256,
        "measurements": measurements,
        "memory": collect_self_memory(),
    }


def execute_request(request: Dict[str, Any]) -> Dict[str, Any]:
    """Execute one engine/profile benchmark phase.

    Args:
        request: JSON-compatible request containing ``phase``, ``engine``,
            ``profile``, ``warmups``, ``repetitions``, and ``workspace``.

    Returns:
        JSON-compatible worker response. The build phase includes the
        dataset and query manifests; the load phase includes its
        regenerated dataset hash.

    Raises:
        ValueError: If the request contains an unknown phase, profile, or
            engine, or invalid repetition values.
        RuntimeError: If a generated present query unexpectedly finds no
            results, or a persistence round-trip changes result IDs.
    """
    context = _parse_request(request)
    phase = str(request.get("phase", ""))
    if phase == "build":
        return _execute_build_phase(context)
    if phase == "load":
        return _execute_load_phase(context)
    raise ValueError(f"Unknown worker phase: {phase!r}")


def main(argv: List[str] | None = None) -> int:
    """Run the file-based worker protocol.

    Args:
        argv: Two paths: input request JSON and output response JSON.

    Returns:
        ``0`` after a successful response.

    Raises:
        ValueError: If exactly two paths are not provided.
    """
    arguments = list(sys.argv[1:] if argv is None else argv)
    if len(arguments) != 2:
        raise ValueError("Worker expects request and response paths")

    request_path = Path(arguments[0])
    response_path = Path(arguments[1])
    response = execute_request(_read_json_object(request_path))
    _write_json_object(response_path, response)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
