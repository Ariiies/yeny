"""Round-trip verification helpers for persistence benchmark scenarios.

A loaded index is only trustworthy when it returns the same documents, in
the same ranking order, with the same scores as the freshly built one.
These helpers collect per-query result sequences and fail loudly when a
persistence backend changes any of them. The check proves fidelity of the
persistence layer; it is not a relevance metric.
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Mapping, Sequence

from lucis import Lucis

from ..queries import GeneratedQueries


SCORE_REL_TOLERANCE = 1e-9
SCORE_ABS_TOLERANCE = 1e-12


def collect_result_sequence(
    lucis: Lucis,
    queries: GeneratedQueries,
    top_k: int = 10,
) -> Dict[str, List[Dict[str, Any]]]:
    """Collect ranked results for every query in returned order.

    Args:
        lucis: Indexed Lucis instance to query.
        queries: Deterministic query set used for the collection.
        top_k: Maximum results collected per query.

    Returns:
        Mapping from query ID to ordered ``doc_id``/``score`` entries.
        Queries without matches map to an empty list.
    """
    collected: Dict[str, List[Dict[str, Any]]] = {}
    for query in queries.items:
        response = lucis.search(query.text, top_k=top_k)
        collected[query.query_id] = [
            {"doc_id": str(result.doc_id), "score": float(result.score)}
            for result in response.results
        ]
    return collected


def _compare_entry(
    query_id: str,
    position: int,
    expected: Mapping[str, Any],
    actual: Mapping[str, Any],
    backend: str,
) -> None:
    """Compare one ranked result entry, raising on any difference.

    Args:
        query_id: Query being verified.
        position: Ranking position of the entry.
        expected: Entry collected right after building the index.
        actual: Entry collected after loading the index.
        backend: Persistence backend label used in error messages.

    Raises:
        RuntimeError: If the document ID or the score differs.
    """
    if expected["doc_id"] != actual["doc_id"]:
        raise RuntimeError(
            f"{backend} round-trip changed the ranking for query "
            f"{query_id!r} at position {position}: expected doc_id "
            f"{expected['doc_id']!r}, got {actual['doc_id']!r}"
        )
    expected_score = float(expected["score"])
    actual_score = float(actual["score"])
    if not math.isclose(
        expected_score,
        actual_score,
        rel_tol=SCORE_REL_TOLERANCE,
        abs_tol=SCORE_ABS_TOLERANCE,
    ):
        raise RuntimeError(
            f"{backend} round-trip changed the score for query "
            f"{query_id!r} at position {position} (doc_id "
            f"{expected['doc_id']!r}): expected {expected_score!r}, got "
            f"{actual_score!r} (rel_tol={SCORE_REL_TOLERANCE}, "
            f"abs_tol={SCORE_ABS_TOLERANCE})"
        )


def verify_roundtrip(
    expected: Mapping[str, Sequence[Mapping[str, Any]]],
    actual: Mapping[str, Sequence[Mapping[str, Any]]],
    *,
    backend: str,
) -> int:
    """Verify that a loaded index preserves IDs, ranking, and scores.

    Args:
        expected: Ranked entries collected right after building the index.
        actual: Ranked entries collected after loading the index.
        backend: Persistence backend label used in error messages.

    Returns:
        Number of queries whose results match exactly.

    Raises:
        ValueError: If both mappings describe different query sets.
        RuntimeError: If any query changes its result count, document
            IDs, ranking order, or scores beyond the documented
            tolerance.
    """
    if set(expected) != set(actual):
        raise ValueError("Round-trip query sets do not match")
    for query_id in expected:
        expected_entries = list(expected[query_id])
        actual_entries = list(actual[query_id])
        if len(expected_entries) != len(actual_entries):
            raise RuntimeError(
                f"{backend} round-trip changed the result count for "
                f"query {query_id!r}: expected "
                f"{len(expected_entries)}, got {len(actual_entries)}"
            )
        for position, (expected_entry, actual_entry) in enumerate(
            zip(expected_entries, actual_entries)
        ):
            _compare_entry(
                query_id,
                position,
                expected_entry,
                actual_entry,
                backend,
            )
    return len(expected)
