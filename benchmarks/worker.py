"""Isolated benchmark worker for one Lucis engine.

The parent runner starts this module four times per engine in fresh Python
processes. The ``build`` phase generates the deterministic corpus, builds a
controlled-word index, runs search measurements, persists JSON, SQLite, and
``.lcs`` artifacts, and writes the dataset/query contract the load phases
consume. The ``load_json``, ``load_sqlite``, and ``load_mmap`` phases each
reload exactly one backend in a new interpreter, so no backend inherits
Python state warmed by a previous one, and each verifies that result IDs,
ranking, and scores survive the round-trip. Workers never write inside
``src/``.

This module is an internal implementation detail. Users should invoke
``python -m benchmarks run`` instead.
"""

from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Mapping, Tuple

from lucis import Lucis
from lucis.config import LucisOptions
from lucis.utils.nlp import WordTokenizer

from .config import (
    BenchmarkProfile,
    load_profiles,
    load_reference_hashes,
)
from .datasets import GeneratedDataset, generate_dataset
from .memory import collect_self_memory
from .metrics import make_measurement, measure_once, measure_operation
from .queries import (
    GeneratedQueries,
    QuerySpec,
    build_queries,
    queries_from_dict,
)
from .scenarios.mmap_load import measure_lcs_write, measure_mmap_load
from .scenarios.persistence import (
    measure_json_save,
    measure_sqlite_save,
    measure_standard_load,
)
from .scenarios.roundtrip import collect_result_sequence


LOAD_PHASE_BACKENDS: Mapping[str, str] = {
    "load_json": "json",
    "load_sqlite": "sqlite",
    "load_mmap": "mmap",
}
"""Mapping from worker load-phase names to persistence backend labels."""



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
        preprocessor=WordTokenizer(),
        autoload=False,
        options=LucisOptions(
            storage_dir=str(context.workspace / "build"),
            binary_dir=None,
        ),
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
                preprocessor=WordTokenizer(),
                options=LucisOptions(
                    storage_dir=str(context.workspace / "e2e"),
                    binary_dir=None,
                ),
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
        context.workspace / "dataset_manifest.json",
        dataset.manifest.to_dict(),
    )
    _write_json_object(
        context.workspace / "queries.json",
        {
            "manifest": queries.manifest.to_dict(),
            "items": [query.to_dict() for query in queries.items],
        },
    )
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
        preprocessor=WordTokenizer(),
        autoload=False,
        options=LucisOptions(
            storage_type="sqlite",
            db_path=str(sqlite_dir / "benchmark.db"),
            binary_dir=None,
        ),
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
        "pid": os.getpid(),
    }



def _read_workspace_contract(
    context: _RequestContext,
) -> Tuple[GeneratedQueries, Dict[str, Any], str]:
    """Read the build-phase contract without regenerating the corpus.

    Load phases consume the dataset manifest, query set, and expected
    results written by the build phase. Rebuilding the queries from their
    serialized form re-validates the query hash, and both the query
    manifest and the expectations must point back to the build-phase
    dataset hash, which keeps the cross-process chain of custody intact.

    Args:
        context: Validated worker request fields.

    Returns:
        Tuple containing the rebuilt query set, the raw expectations
        object, and the build-phase dataset SHA-256.

    Raises:
        RuntimeError: If the workspace contract belongs to another engine,
            another dataset, or fails its internal hash checks.
    """
    dataset_manifest = _read_json_object(
        context.workspace / "dataset_manifest.json"
    )
    queries = queries_from_dict(
        _read_json_object(context.workspace / "queries.json")
    )
    expectations = _read_json_object(
        context.workspace / "expected_results.json"
    )
    if expectations.get("engine") != context.engine:
        raise RuntimeError(
            "Build-phase expectations belong to another engine"
        )
    dataset_sha256 = str(dataset_manifest.get("sha256", ""))
    if not dataset_sha256:
        raise RuntimeError("Build-phase dataset manifest has no hash")
    if queries.manifest.dataset_sha256 != dataset_sha256:
        raise RuntimeError(
            "Query manifest belongs to another dataset"
        )
    if expectations.get("dataset_sha256") != dataset_sha256:
        raise RuntimeError(
            "Expected results belong to another dataset"
        )
    return queries, expectations, dataset_sha256


def _execute_backend_load_phase(
    context: _RequestContext,
    backend: str,
) -> Dict[str, Any]:
    """Reload exactly one persistence backend in a fresh interpreter.

    Running every backend in its own process keeps each load process-cold
    with respect to Python state: no backend inherits import caches,
    allocators, or engine state warmed by a previous backend. The
    operating-system page cache remains uncontrolled and is documented as
    a limitation.

    Args:
        context: Validated worker request fields.
        backend: Backend label: ``json``, ``sqlite``, or ``mmap``.

    Returns:
        JSON-compatible response with the build-phase dataset hash and
        only the requested backend's measurements.

    Raises:
        RuntimeError: If the workspace contract is inconsistent or the
            round-trip changes result IDs, ranking, or scores.
    """
    queries, expectations, dataset_sha256 = _read_workspace_contract(
        context
    )
    expected_results = expectations["results"]

    engine = context.engine
    if backend == "mmap":
        measurements = measure_mmap_load(
            lambda: Lucis(
                name=f"benchmark_{engine}_mmap",
                engine=engine,
                preprocessor=WordTokenizer(),
                autoload=False,
                options=LucisOptions(
                    storage_dir=str(context.workspace / "mmap"),
                    binary_dir=None,
                ),
            ),
            context.workspace / "lcs" / f"benchmark_{engine}.lcs",
            engine=engine,
            queries=queries,
            expected_results=expected_results,
            warmups=context.warmups,
            repetitions=context.repetitions,
        )
    else:
        constructors = {
            "json": lambda: Lucis(
                name=f"benchmark_{engine}_build",
                engine=engine,
                preprocessor=WordTokenizer(),
                autoload=True,
                options=LucisOptions(
                    storage_dir=str(context.workspace / "build"),
                    binary_dir=None,
                ),
            ),
            "sqlite": lambda: Lucis(
                name=f"benchmark_{engine}_sqlite",
                engine=engine,
                preprocessor=WordTokenizer(),
                autoload=True,
                options=LucisOptions(
                    storage_type="sqlite",
                    db_path=str(context.workspace / "sqlite" / "benchmark.db"),
                    binary_dir=None,
                ),
            ),
        }
        measurements = measure_standard_load(
            backend,
            constructors[backend],
            engine=engine,
            queries=queries,
            expected_results=expected_results,
            warmups=context.warmups,
            repetitions=context.repetitions,
        )

    return {
        "engine": engine,
        "profile": context.profile.name,
        "dataset_sha256": dataset_sha256,
        "measurements": measurements,
        "memory": collect_self_memory(),
        "pid": os.getpid(),
    }



def execute_request(request: Dict[str, Any]) -> Dict[str, Any]:
    """Execute one engine/profile benchmark phase.

    Args:
        request: JSON-compatible request containing ``phase``, ``engine``,
            ``profile``, ``warmups``, ``repetitions``, and ``workspace``.
            ``phase`` is ``build`` or one of the per-backend load phases
            declared in :data:`LOAD_PHASE_BACKENDS`.

    Returns:
        JSON-compatible worker response. The build phase includes the
        dataset and query manifests; each load phase includes the
        build-phase dataset hash and only its own backend's metrics.

    Raises:
        ValueError: If the request contains an unknown phase, profile, or
            engine, or invalid repetition values.
        RuntimeError: If a generated present query unexpectedly finds no
            results, or a persistence round-trip changes result IDs,
            ranking, or scores.
    """
    context = _parse_request(request)
    phase = str(request.get("phase", ""))
    if phase == "build":
        return _execute_build_phase(context)
    backend = LOAD_PHASE_BACKENDS.get(phase)
    if backend is not None:
        return _execute_backend_load_phase(context, backend)
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
