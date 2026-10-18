"""Stable query sets derived from a generated benchmark corpus.

Query categories are selected from measured document frequencies in the
generated corpus. This prevents query selection from changing between engines
or relying on external fixtures.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Mapping, Set, Tuple

from .datasets import GeneratedDataset


QUERY_SET_VERSION = "queries_v1"


@dataclass(frozen=True)
class QuerySpec:
    """One query and the facts needed to interpret it.

    Attributes:
        query_id: Stable identifier within the query set.
        category: Query category such as ``common`` or ``rare``.
        text: Raw text passed to the public Yeny API.
        tokens: Controlled tokens represented by ``text``.
        expected_documents: Documents containing at least one query token.
        repetitions: Preferred repetitions for special repeated-query cases.
    """

    query_id: str
    category: str
    text: str
    tokens: Tuple[str, ...]
    expected_documents: Tuple[str, ...]
    repetitions: int = 1

    def to_dict(self) -> Dict[str, object]:
        """Return the query as a JSON-compatible dictionary.

        Returns:
            Dictionary with tuples converted to JSON arrays.
        """
        payload = asdict(self)
        payload["tokens"] = list(self.tokens)
        payload["expected_documents"] = list(self.expected_documents)
        return payload


@dataclass(frozen=True)
class QueryManifest:
    """Identity metadata for one deterministic query set.

    Attributes:
        version: Query generation contract version.
        dataset_sha256: Hash of the source corpus.
        queries: Number of generated queries.
        sha256: Hash of the canonical query representation.
    """

    version: str
    dataset_sha256: str
    queries: int
    sha256: str

    def to_dict(self) -> Dict[str, object]:
        """Return the manifest as a JSON-compatible dictionary.

        Returns:
            Dictionary containing every manifest field.
        """
        return asdict(self)


@dataclass(frozen=True)
class GeneratedQueries:
    """Generated query specifications and their manifest.

    Attributes:
        items: Immutable sequence of query specifications.
        manifest: Reproducibility metadata for ``items``.
    """

    items: Tuple[QuerySpec, ...]
    manifest: QueryManifest


def _postings(dataset: GeneratedDataset) -> Dict[str, Set[str]]:
    result: Dict[str, Set[str]] = {}
    for doc_id, text in dataset.documents.items():
        for token in set(text.split()):
            result.setdefault(token, set()).add(doc_id)
    return result


def _absent_token(existing: Set[str], index: int) -> str:
    current = index
    letters: List[str] = []
    while True:
        current, remainder = divmod(current, 26)
        letters.append(chr(ord("a") + remainder))
        if current == 0:
            break
        current -= 1
    suffix = "".join(reversed(letters))
    candidate = f"absentbenchmark{suffix}"
    while candidate in existing:
        candidate = f"x{candidate}"
    return candidate


def _query_hash(items: Tuple[QuerySpec, ...]) -> str:
    payload = [item.to_dict() for item in items]
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def build_queries(
    dataset: GeneratedDataset,
    *,
    per_category: int = 4,
) -> GeneratedQueries:
    """Create common, rare, multi-token, absent and repeated queries.

    Args:
        dataset: Deterministic source corpus.
        per_category: Number of common, rare, multi, and absent queries.

    Returns:
        Immutable query set and its manifest.

    Raises:
        ValueError: If ``per_category`` is invalid or the corpus does not
            contain enough vocabulary.
    """
    if per_category <= 0:
        raise ValueError("per_category must be greater than zero")

    postings = _postings(dataset)
    if len(postings) < per_category * 2:
        raise ValueError("Dataset vocabulary is too small for query generation")

    by_common = sorted(
        postings,
        key=lambda token: (-len(postings[token]), token),
    )
    by_rare = sorted(
        postings,
        key=lambda token: (len(postings[token]), token),
    )

    common = by_common[:per_category]
    rare = [token for token in by_rare if token not in common][
        :per_category
    ]

    items: List[QuerySpec] = []
    for index, token in enumerate(common):
        items.append(
            QuerySpec(
                query_id=f"common_{index:02d}",
                category="common",
                text=token,
                tokens=(token,),
                expected_documents=tuple(sorted(postings[token])),
            )
        )

    for index, token in enumerate(rare):
        items.append(
            QuerySpec(
                query_id=f"rare_{index:02d}",
                category="rare",
                text=token,
                tokens=(token,),
                expected_documents=tuple(sorted(postings[token])),
            )
        )

    for index, (common_token, rare_token) in enumerate(zip(common, rare)):
        expected = postings[common_token].union(postings[rare_token])
        items.append(
            QuerySpec(
                query_id=f"multi_{index:02d}",
                category="multi",
                text=f"{common_token} {rare_token}",
                tokens=(common_token, rare_token),
                expected_documents=tuple(sorted(expected)),
            )
        )

    existing = set(postings)
    for index in range(per_category):
        token = _absent_token(existing, index)
        items.append(
            QuerySpec(
                query_id=f"no_result_{index:02d}",
                category="no_result",
                text=token,
                tokens=(token,),
                expected_documents=(),
            )
        )

    repeated_token = common[0]
    items.append(
        QuerySpec(
            query_id="repeated_00",
            category="repeated",
            text=repeated_token,
            tokens=(repeated_token,),
            expected_documents=tuple(sorted(postings[repeated_token])),
            repetitions=100,
        )
    )

    frozen_items = tuple(items)
    manifest = QueryManifest(
        version=QUERY_SET_VERSION,
        dataset_sha256=dataset.manifest.sha256,
        queries=len(frozen_items),
        sha256=_query_hash(frozen_items),
    )
    return GeneratedQueries(items=frozen_items, manifest=manifest)


def queries_from_dict(payload: Mapping[str, Any]) -> GeneratedQueries:
    """Rebuild a generated query set from its JSON representation.

    Load workers use this to consume the queries written by the build
    worker instead of regenerating the whole corpus.

    Args:
        payload: Mapping with ``manifest`` and ``items`` as produced by
            the build phase.

    Returns:
        Immutable query set equivalent to the original.

    Raises:
        ValueError: If the payload is missing fields, its version is
            unsupported, or the manifest hash does not match the items.
    """
    raw_manifest = payload.get("manifest")
    raw_items = payload.get("items")
    if not isinstance(raw_manifest, Mapping) or not isinstance(
        raw_items, list
    ):
        raise ValueError("Query payload must contain manifest and items")
    if raw_manifest.get("version") != QUERY_SET_VERSION:
        raise ValueError("Unsupported query payload version")

    items = []
    for raw in raw_items:
        if not isinstance(raw, Mapping):
            raise ValueError("Query items must be objects")
        items.append(
            QuerySpec(
                query_id=str(raw["query_id"]),
                category=str(raw["category"]),
                text=str(raw["text"]),
                tokens=tuple(str(token) for token in raw["tokens"]),
                expected_documents=tuple(
                    str(doc_id) for doc_id in raw["expected_documents"]
                ),
                repetitions=int(raw.get("repetitions", 1)),
            )
        )
    frozen_items = tuple(items)
    if _query_hash(frozen_items) != raw_manifest.get("sha256"):
        raise ValueError("Query manifest hash does not match the items")

    manifest = QueryManifest(
        version=str(raw_manifest["version"]),
        dataset_sha256=str(raw_manifest["dataset_sha256"]),
        queries=int(raw_manifest["queries"]),
        sha256=str(raw_manifest["sha256"]),
    )
    if manifest.queries != len(frozen_items):
        raise ValueError("Query manifest count does not match the items")
    return GeneratedQueries(items=frozen_items, manifest=manifest)
