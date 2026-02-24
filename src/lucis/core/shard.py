"""
Temporal Shard Manager for Lucis.

Partitions documents into monthly shards (``YYYY_MM``) based on a date
column.  Each shard is an independent engine instance with its own
inverted index, so only the shards relevant to a query need to be
loaded into RAM.

Architecture overview::

    ┌─────────────┐
    │   Lucis     │
    │  (Facade)   │
    └──────┬──────┘
           │
    ┌──────▼──────┐
    │ShardManager │
    └──────┬──────┘
           │
    ┌──────┼──────────┬──────────┐
    ▼      ▼          ▼          ▼
  2026_01  2026_02  2026_03  9999_99
  Engine   Engine   Engine   Engine
  (shard)  (shard)  (shard)  (global)

Constants:
    LUCIS_GLOBAL_SHARD: Fallback shard key (``"9999_99"``) for documents
        without a date or from tables without a date column.
    LUCIS_DEFAULT_DATE_COLUMNS: Column names that Lucis auto-detects
        as temporal key when ``date_column="auto"``.
"""
from __future__ import annotations

import re
from collections import defaultdict
from datetime import datetime, date
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

from ..engines.base import BaseEngine, DocId


# Constants 

LUCIS_GLOBAL_SHARD: str = "9999_99"
"""Fallback shard for documents without a date value."""

LUCIS_DEFAULT_DATE_COLUMNS: Tuple[str, ...] = (
    "created_at",
    "updated_at",
    "timestamp",
)
"""Column names auto-detected as temporal key (checked in order)."""

_SHARD_KEY_RE = re.compile(r"^\d{4}_\d{2}$")


# Utility functions

def date_to_shard_key(value: Any) -> str:
    """Convert a date/datetime/string to shard key ``YYYY_MM``.

    Accepts ``datetime``, ``date``, ISO-format strings, or ``None``.
    Returns :data:`LUCIS_GLOBAL_SHARD` for ``None`` or unparseable values.

    Examples::

        date_to_shard_key(datetime(2026, 2, 23))   # "2026_02"
        date_to_shard_key("2026-02-23")             # "2026_02"
        date_to_shard_key(None)                     # "9999_99"
    """
    if value is None:
        return LUCIS_GLOBAL_SHARD
    if isinstance(value, datetime):
        return f"{value.year:04d}_{value.month:02d}"
    if isinstance(value, date):
        return f"{value.year:04d}_{value.month:02d}"
    if isinstance(value, str):
        try:
            dt = datetime.fromisoformat(value)
            return f"{dt.year:04d}_{dt.month:02d}"
        except (ValueError, TypeError):
            return LUCIS_GLOBAL_SHARD
    return LUCIS_GLOBAL_SHARD


def normalize_to_shard_key(value: Any) -> Optional[str]:
    """Normalize a ``since``/``until`` value to a shard key.

    Accepts shard keys (``"2026_01"``), ISO dates (``"2026-01-15"``),
    year-month strings (``"2026-01"``), ``datetime`` objects, or ``None``.

    Examples::

        normalize_to_shard_key("2026_01")       # "2026_01"
        normalize_to_shard_key("2026-01")       # "2026_01"
        normalize_to_shard_key("2026-01-15")    # "2026_01"
        normalize_to_shard_key(None)            # None
    """
    if value is None:
        return None
    if isinstance(value, str):
        if _SHARD_KEY_RE.match(value):
            return value
        # Handle "2026-01" format (year-month without day)
        if re.match(r"^\d{4}-\d{2}$", value):
            return value.replace("-", "_")
        try:
            dt = datetime.fromisoformat(value)
            return f"{dt.year:04d}_{dt.month:02d}"
        except (ValueError, TypeError):
            return None
    if isinstance(value, (datetime, date)):
        return f"{value.year:04d}_{value.month:02d}"
    return None


def shard_key_in_range(
    key: str,
    since: Optional[str] = None,
    until: Optional[str] = None,
) -> bool:
    """Check if *key* falls within [*since*, *until*] (inclusive).

    The global shard (``9999_99``) is **always** included regardless
    of the range — it contains undated documents that may be relevant.
    """
    if key == LUCIS_GLOBAL_SHARD:
        return True
    if since and key < since:
        return False
    if until and key > until:
        return False
    return True


# ShardManager

class ShardManager:
    """
    Orchestrates temporal shards for a Lucis index.

    Each shard is an independent :class:`BaseEngine` instance containing
    documents from a single month.  The manager handles:

    - Document routing by date value.
    - Multi-shard search with optional time-scoped filtering.
    - Per-shard persistence and loading.
    - Incremental document addition to the correct shard.

    Args:
        engine_class: Engine class to instantiate per shard
            (e.g. ``LiteEngine``, ``CoreEngine``).
        storage: Storage backend for persistence.
        preprocessor: Text preprocessor passed to each shard engine.
    """

    def __init__(
        self,
        engine_class: type,
        storage: Any,
        preprocessor: Optional[Callable] = None,
    ):
        self._engine_class = engine_class
        self._storage = storage
        self._preprocessor = preprocessor
        # shard_key → engine instance
        self.shards: Dict[str, BaseEngine] = {}

    # Properties

    @property
    def total_docs(self) -> int:
        """Total documents across all loaded shards."""
        return sum(e.total_docs for e in self.shards.values())

    @property
    def shard_keys(self) -> List[str]:
        """Sorted list of active shard keys."""
        return sorted(self.shards.keys())

    @property
    def id_map(self) -> Dict:
        """Unified ``id_map`` across all shards."""
        unified: Dict = {}
        for engine in self.shards.values():
            unified.update(engine.id_map)
        return unified

    @property
    def id_type(self) -> str:
        for engine in self.shards.values():
            if engine.id_type != "none":
                return engine.id_type
        return "none"

    @property
    def preprocessor(self) -> Callable:
        """Preprocessor from any shard (all share the same config)."""
        for engine in self.shards.values():
            return engine.preprocessor
        # No shards yet — create a temp engine to resolve the chain
        dummy = self._create_engine()
        return dummy.preprocessor

    # Shard lifecycle

    def _create_engine(self) -> BaseEngine:
        """Create a fresh engine instance with the shared config."""
        return self._engine_class(
            storage=self._storage,
            preprocessor=self._preprocessor,
        )

    def get_or_create_shard(self, shard_key: str) -> BaseEngine:
        """Get an existing shard engine or create a new empty one."""
        if shard_key not in self.shards:
            self.shards[shard_key] = self._create_engine()
        return self.shards[shard_key]

    # Indexing

    def build_shards(
        self,
        data: Dict[str, str],
        dates: Dict[str, Any],
    ) -> None:
        """Route documents to shards by date and build each shard's index.

        Args:
            data: ``{doc_id: text}`` mapping.
            dates: ``{doc_id: date_value}`` (same keys as *data*).
                ``None`` values → :data:`LUCIS_GLOBAL_SHARD`.
        """
        groups: Dict[str, Dict[str, str]] = defaultdict(dict)
        for doc_id, text in data.items():
            key = date_to_shard_key(dates.get(doc_id))
            groups[key][doc_id] = text

        self.shards.clear()
        for shard_key, docs in groups.items():
            engine = self.get_or_create_shard(shard_key)
            engine.build_index(docs)

    def add_documents(
        self,
        new_docs: Dict[str, str],
        dates: Dict[str, Any],
    ) -> None:
        """Incrementally add documents to appropriate shards.

        Each document is routed to its shard by date.  If the shard
        already exists and the engine supports incremental indexing,
        ``add_documents()`` is called.  Otherwise ``build_index()``
        is used (for new shards or engines without incremental support).
        """
        groups: Dict[str, Dict[str, str]] = defaultdict(dict)
        for doc_id, text in new_docs.items():
            key = date_to_shard_key(dates.get(doc_id))
            groups[key][doc_id] = text

        for shard_key, docs in groups.items():
            engine = self.get_or_create_shard(shard_key)
            if engine.total_docs > 0 and hasattr(engine, "add_documents"):
                engine.add_documents(docs)
            else:
                engine.build_index(docs)

    # Search

    def search(
        self,
        query_tokens: Union[str, List[str]],
        top_k: int = 10,
        since: Optional[str] = None,
        until: Optional[str] = None,
    ) -> List[Tuple[DocId, float, str]]:
        """Search across relevant shards and merge results.

        Args:
            query_tokens: Pre-processed query (str or token list).
            top_k: Maximum results.
            since: Start shard key or ISO date (inclusive).
            until: End shard key or ISO date (inclusive).

        Returns:
            ``[(doc_id, score, shard_key), ...]`` sorted by score
            descending, limited to *top_k*.
        """
        since_key = normalize_to_shard_key(since)
        until_key = normalize_to_shard_key(until)

        all_results: List[Tuple[DocId, float, str]] = []

        for key in sorted(self.shards.keys()):
            if not shard_key_in_range(key, since_key, until_key):
                continue
            shard_results = self.shards[key].search(query_tokens, top_k=top_k)
            for doc_id, score in shard_results:
                all_results.append((doc_id, score, key))

        all_results.sort(key=lambda x: x[1], reverse=True)
        return all_results[:top_k]

    # Persistence

    def persist_all(self, base_name: str) -> List[str]:
        """Persist every shard to storage.

        Each shard is saved as ``{base_name}__shard__{key}``.

        Args:
            base_name: The versioned physical name.

        Returns:
            List of shard keys persisted.
        """
        shard_keys = []
        for shard_key, engine in self.shards.items():
            shard_name = f"{base_name}__shard__{shard_key}"
            engine.persist(shard_name)
            shard_keys.append(shard_key)

        self._storage.save_shard_registry(base_name, shard_keys)
        return shard_keys

    def load_all(
        self,
        base_name: str,
        shard_keys: Optional[List[str]] = None,
    ) -> None:
        """Load shards from storage.

        Args:
            base_name: The versioned physical name.
            shard_keys: Explicit shard keys.  If ``None``, reads from
                the shard registry.
        """
        if shard_keys is None:
            shard_keys = self._storage.load_shard_registry(base_name)

        self.shards.clear()
        for shard_key in shard_keys:
            shard_name = f"{base_name}__shard__{shard_key}"
            engine = self._create_engine()
            engine.load_engine(shard_name)
            self.shards[shard_key] = engine

    def load_selective(
        self,
        base_name: str,
        since: Optional[str] = None,
        until: Optional[str] = None,
    ) -> None:
        """Load only shards within a time range (RAM optimization).

        Shards outside the range are never loaded into memory.
        The global shard is always loaded.

        Args:
            base_name: The versioned physical name.
            since: Start shard key or ISO date (inclusive).
            until: End shard key or ISO date (inclusive).
        """
        all_keys = self._storage.load_shard_registry(base_name)
        since_key = normalize_to_shard_key(since)
        until_key = normalize_to_shard_key(until)
        relevant_keys = [
            k for k in all_keys
            if shard_key_in_range(k, since_key, until_key)
        ]
        self.load_all(base_name, relevant_keys)

    # Info

    def shard_stats(self) -> Dict[str, int]:
        """Return ``{shard_key: doc_count}`` for all loaded shards."""
        return {k: e.total_docs for k, e in sorted(self.shards.items())}

    def __repr__(self) -> str:
        keys = ", ".join(sorted(self.shards.keys()))
        return (
            f"ShardManager(shards={len(self.shards)}, "
            f"total_docs={self.total_docs}, keys=[{keys}])"
        )
