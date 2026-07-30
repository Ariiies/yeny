"""Memory-mapped ``.lcs`` benchmark scenarios.

Serialization and loading use the engine-level binary API
(``engine.save_binary`` and ``engine.load_mmap``), which is the supported
boundary for non-sharded indexes. Searches still go through the public
``Lucis.search`` facade so results stay comparable with the standard load
scenario.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Dict, List, Mapping, Sequence

from lucis import Lucis

from ..metrics import make_measurement, measure_once, measure_operation
from ..queries import GeneratedQueries
from .persistence import _warm_category_samples
from .roundtrip import collect_result_sequence, verify_roundtrip


def measure_lcs_write(
    lucis: Lucis,
    path: Path,
    *,
    engine: str,
) -> List[Dict[str, Any]]:
    """Measure ``.lcs`` binary serialization and its file size.

    Args:
        lucis: Indexed instance whose engine is serialized.
        path: Destination ``.lcs`` path inside the benchmark workspace.
        engine: Engine key attached to the measurements.

    Returns:
        The ``lcs_write`` duration in nanoseconds and the
        ``lcs_artifact_size`` in bytes.

    Raises:
        FileNotFoundError: If the ``.lcs`` artifact is missing after the
            write.
    """
    samples = measure_operation(lambda: lucis.engine.save_binary(str(path)))
    size = path.stat().st_size
    return [
        make_measurement("lcs_write", samples, engine=engine),
        make_measurement(
            "lcs_artifact_size",
            [size],
            unit="bytes",
            engine=engine,
        ),
    ]


def measure_mmap_load(
    constructor: Callable[[], Lucis],
    path: Path,
    *,
    engine: str,
    queries: GeneratedQueries,
    expected_results: Mapping[str, Sequence[Mapping[str, Any]]],
    warmups: int,
    repetitions: int,
) -> List[Dict[str, Any]]:
    """Measure mmap loading plus first and warm searches over mapped pages.

    The engine loads through ``engine.load_mmap``; the private
    ``_is_indexed`` flag is then enabled so the public ``Lucis.search``
    facade remains the measured search boundary, exactly as in the standard
    load scenario. The instance is always closed, releasing the mmap handle
    before temporary files are removed, which is required on Windows.

    Args:
        constructor: Zero-argument callable returning a fresh, unloaded
            Lucis instance.
        path: Existing ``.lcs`` artifact produced during the build phase.
        engine: Engine key attached to the measurements.
        queries: Deterministic query set used for searches.
        expected_results: Ranked results collected right after the index
            build.
        warmups: Unmeasured searches executed before each query.
        repetitions: Measured searches per query.

    Returns:
        ``mmap_load``, ``search_first_mmap``, ``search_warm_mmap``, and
        ``roundtrip_verified`` measurements.

    Raises:
        RuntimeError: If mmap results differ from ``expected_results``.
    """
    instance = constructor()
    try:
        _, load_elapsed = measure_once(
            lambda: instance.engine.load_mmap(str(path))
        )
        instance._is_indexed = True
        measurements = [
            make_measurement("mmap_load", [load_elapsed], engine=engine),
        ]
        first_query = queries.items[0]
        first_samples = measure_operation(
            lambda: instance.search(first_query.text, top_k=10)
        )
        measurements.append(
            make_measurement(
                "search_first_mmap",
                first_samples,
                engine=engine,
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
                    "search_warm_mmap",
                    samples,
                    engine=engine,
                    query_category=category,
                )
            )
        verified = verify_roundtrip(
            expected_results,
            collect_result_sequence(instance, queries),
            backend="mmap",
        )
        measurements.append(
            make_measurement(
                "roundtrip_verified",
                [verified],
                unit="count",
                engine=engine,
                backend="mmap",
            )
        )
        return measurements
    finally:
        instance.close()
