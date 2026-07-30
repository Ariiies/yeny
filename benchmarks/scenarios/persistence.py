"""JSON and SQLite persistence benchmark scenarios.

Saves are measured through ``Lucis.save`` and loads through a fresh
autoloading ``Lucis`` constructor, which is the boundary a user experiences.
Artifact sizes are recorded in real bytes; the SQLite size is taken after a
commit and includes any journal sidecar files.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Dict, List, Mapping, Sequence

from lucis import Lucis

from ..metrics import make_measurement, measure_once, measure_operation
from ..queries import GeneratedQueries
from .roundtrip import collect_result_sequence, verify_roundtrip


def _sqlite_artifact_size(db_path: Path) -> int:
    """Sum the bytes of one SQLite database and its sidecar files.

    Args:
        db_path: Path to the main SQLite database file.

    Returns:
        Combined size of the database and any ``-wal``/``-shm``/``-journal``
        companions, in bytes.
    """
    candidates = [db_path, *db_path.parent.glob(f"{db_path.name}-*")]
    return sum(
        candidate.stat().st_size
        for candidate in candidates
        if candidate.is_file()
    )


def _warm_category_samples(
    lucis: Lucis,
    queries: GeneratedQueries,
    *,
    warmups: int,
    repetitions: int,
) -> Dict[str, List[int]]:
    """Measure warm public searches grouped by query category.

    Args:
        lucis: Indexed and already loaded Lucis instance.
        queries: Deterministic query set used for searches.
        warmups: Unmeasured searches executed before each query.
        repetitions: Measured searches per query; the ``repeated`` category
            keeps its own preferred repetition count.

    Returns:
        Mapping from query category to raw nanosecond samples.
    """
    category_samples: Dict[str, List[int]] = {}
    for query in queries.items:
        for _ in range(warmups):
            lucis.search(query.text, top_k=10)
        measured_repetitions = (
            query.repetitions
            if query.category == "repeated"
            else repetitions
        )
        samples = measure_operation(
            lambda query_text=query.text: lucis.search(
                query_text,
                top_k=10,
            ),
            repetitions=measured_repetitions,
        )
        category_samples.setdefault(query.category, []).extend(samples)
    return category_samples


def measure_json_save(lucis: Lucis, *, engine: str) -> List[Dict[str, Any]]:
    """Measure JSON persistence and artifact size for one indexed instance.

    Args:
        lucis: Indexed instance using ``JSONStorage``.
        engine: Engine key attached to the measurements.

    Returns:
        The ``json_save`` duration in nanoseconds and the
        ``json_artifact_size`` in bytes.

    Raises:
        FileNotFoundError: If the expected JSON artifact is missing after
            the save.
    """
    samples = measure_operation(lucis.save)
    artifact = Path(lucis.storage.directory) / f"{lucis.name}.json"
    size = artifact.stat().st_size
    return [
        make_measurement("json_save", samples, engine=engine),
        make_measurement(
            "json_artifact_size",
            [size],
            unit="bytes",
            engine=engine,
        ),
    ]


def measure_sqlite_save(lucis: Lucis, *, engine: str) -> List[Dict[str, Any]]:
    """Measure SQLite persistence and on-disk artifact size.

    The connection is committed before reading file sizes so the reported
    bytes describe a complete, readable database.

    Args:
        lucis: Indexed instance using ``SQLiteStorage``.
        engine: Engine key attached to the measurements.

    Returns:
        The ``sqlite_save`` duration in nanoseconds and the
        ``sqlite_artifact_size`` in bytes.
    """
    samples = measure_operation(lucis.save)
    lucis.storage.conn.commit()
    size = _sqlite_artifact_size(Path(lucis.storage.db_path))
    return [
        make_measurement("sqlite_save", samples, engine=engine),
        make_measurement(
            "sqlite_artifact_size",
            [size],
            unit="bytes",
            engine=engine,
        ),
    ]


def measure_standard_load(
    backend: str,
    constructor: Callable[[], Lucis],
    *,
    engine: str,
    queries: GeneratedQueries,
    expected_results: Mapping[str, Sequence[Mapping[str, Any]]],
    warmups: int,
    repetitions: int,
) -> List[Dict[str, Any]]:
    """Measure one cold standard load plus first and warm searches.

    The constructor call is the measured boundary, matching what a user
    pays when opening a persisted index in a new process. The instance is
    always closed afterwards, including the storage connection when the
    backend owns one, so temporary files can be removed on any platform.

    Args:
        backend: Storage backend label, such as ``json`` or ``sqlite``.
        constructor: Zero-argument callable returning a freshly loaded,
            autoloading Lucis instance.
        engine: Engine key attached to the measurements.
        queries: Deterministic query set used for searches.
        expected_results: Ranked results collected right after the index
            build.
        warmups: Unmeasured searches executed before each query.
        repetitions: Measured searches per query.

    Returns:
        ``load_standard``, ``search_first_after_load``,
        ``search_warm_after_load``, and ``roundtrip_verified``
        measurements.

    Raises:
        RuntimeError: If loaded results differ from ``expected_results``.
    """
    instance, load_elapsed = measure_once(constructor)
    try:
        measurements = [
            make_measurement(
                "load_standard",
                [load_elapsed],
                engine=engine,
                backend=backend,
            )
        ]
        first_query = queries.items[0]
        first_samples = measure_operation(
            lambda: instance.search(first_query.text, top_k=10)
        )
        measurements.append(
            make_measurement(
                "search_first_after_load",
                first_samples,
                engine=engine,
                backend=backend,
                query_category=first_query.category,
            )
        )
        category_samples = _warm_category_samples(
            instance,
            queries,
            warmups=warmups,
            repetitions=repetitions,
        )
        for category, samples in category_samples.items():
            measurements.append(
                make_measurement(
                    "search_warm_after_load",
                    samples,
                    engine=engine,
                    backend=backend,
                    query_category=category,
                )
            )
        verified = verify_roundtrip(
            expected_results,
            collect_result_sequence(instance, queries),
            backend=backend,
        )
        measurements.append(
            make_measurement(
                "roundtrip_verified",
                [verified],
                unit="count",
                engine=engine,
                backend=backend,
            )
        )
        return measurements
    finally:
        instance.close()
        close_storage = getattr(instance.storage, "close", None)
        if callable(close_storage):
            close_storage()
