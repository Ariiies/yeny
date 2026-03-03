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

import logging
import re
import sys
import time
from collections import defaultdict, OrderedDict
from datetime import datetime, date
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

from ..engines.base import BaseEngine, DocId

log = logging.getLogger(__name__)


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
    """Convert a date/datetime/string to a shard key ``YYYY_MM``.

    Accepts ``datetime``, ``date``, ISO-format strings, or ``None``.
    Returns :data:`LUCIS_GLOBAL_SHARD` for ``None`` or unparseable values.

    Args:
        value: The date value to convert.  Accepted types: ``datetime``,
            ``date``, ISO-format ``str`` (e.g. ``"2026-02-23"``), or
            ``None``.

    Returns:
        A shard key string such as ``"2026_02"``, or
        :data:`LUCIS_GLOBAL_SHARD` (``"9999_99"``) when *value* is
        ``None`` or cannot be parsed.

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
    """Normalize a ``since``/``until`` filter value to a shard key.

    Accepts shard keys (``"2026_01"``), ISO dates (``"2026-01-15"``),
    year-month strings (``"2026-01"``), ``datetime`` objects, or ``None``.

    Args:
        value: Filter value to normalise.  Accepted types: existing shard
            key ``str``, ISO date/datetime ``str``, ``datetime``,
            ``date``, or ``None``.

    Returns:
        Normalised shard key (e.g. ``"2026_01"``), or ``None`` when
        *value* is ``None`` or cannot be parsed.

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
    """Return ``True`` if *key* falls within [*since*, *until*] (inclusive).

    The global shard (``"9999_99"``) is **always** included regardless
    of the range — it contains undated documents that may be relevant.

    Args:
        key: Shard key to test (e.g. ``"2026_02"``).
        since: Lower-bound shard key (inclusive).  ``None`` means
            no lower bound.
        until: Upper-bound shard key (inclusive).  ``None`` means
            no upper bound.

    Returns:
        ``True`` if *key* is within the specified range or is the
        global shard.
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
        max_loaded_shards: int = 0,
        memory_limit_mb: Optional[int] = None,
        temp_ttl_seconds: int = 30,
    ):
        self._engine_class = engine_class
        self._storage = storage
        self._preprocessor = preprocessor
        # shard_key → engine instance (only loaded shards live here)
        self.shards: Dict[str, BaseEngine] = {}

        # --- Lazy / memory-managed loading state ---
        # Fixed shard-count limit (0 = unlimited).
        self._max_loaded: int = max_loaded_shards
        # Dynamic memory budget in bytes (None = unlimited).
        self._memory_limit: Optional[int] = (
            memory_limit_mb * 1_048_576 if memory_limit_mb else None
        )
        # All known shard keys from the registry (loaded AND unloaded).
        self._all_keys: List[str] = []
        # Pre-fetched doc counts per shard (metadata-only, no full load).
        self._doc_counts: Dict[str, int] = {}
        # Physical index base name needed to lazy-load a shard from storage.
        self._lazy_base_name: Optional[str] = None
        # LRU tracker: keys in insertion order (oldest → newest).
        self._lru: "OrderedDict[str, None]" = OrderedDict()
        # Per-shard measured memory in bytes.
        self._shard_mem: Dict[str, int] = {}
        # Cumulative memory of all currently-loaded shards.
        self._loaded_mem: int = 0
        # --- Temporal shard TTL ---
        # Shards loaded for a since/until query get a TTL expiry.
        self._temp_expiry: Dict[str, float] = {}  # shard_key → time.monotonic()
        self._ttl_seconds: int = temp_ttl_seconds
        # Tracks shards already persisted during build_shards_streaming
        # (so persist_all skips them).
        self._persisted_keys: set = set()

    # ── Memory management helpers ──

    @property
    def _is_managed(self) -> bool:
        """``True`` when memory management is active (count or MB limit)."""
        return bool(self._max_loaded or self._memory_limit)

    @staticmethod
    def _estimate_engine_memory(engine: BaseEngine) -> int:
        """Return an approximate byte count for a loaded engine's data.

        Measures the three heavy structures: ``index`` (dict of
        CompactPostings / dict), ``doc_lengths`` (CompactDocLengths /
        dict), and ``id_map``.
        """
        total = 0
        _sizeof = sys.getsizeof

        # -- index: Dict[str, CompactPostings | dict] --
        idx = getattr(engine, "index", None)
        if idx:
            total += _sizeof(idx)
            for tok, postings in idx.items():
                total += _sizeof(tok)
                # CompactPostings uses array.array internally
                ids = getattr(postings, "_doc_ids", None)
                freqs = getattr(postings, "_freqs", None)
                if ids is not None:
                    total += _sizeof(ids) + _sizeof(freqs)
                elif isinstance(postings, dict):
                    total += _sizeof(postings) + 56 * len(postings)
                else:
                    total += _sizeof(postings)

        # -- doc_lengths: CompactDocLengths | dict --
        dl = getattr(engine, "doc_lengths", None)
        if dl is not None:
            data = getattr(dl, "_data", None)  # CompactDocLengths
            if data is not None:
                total += _sizeof(data)
            elif isinstance(dl, dict):
                total += _sizeof(dl) + 56 * len(dl)
            else:
                total += _sizeof(dl)

        # -- id_map --
        im = getattr(engine, "id_map", None)
        if im:
            total += _sizeof(im)
            for k, v in im.items():
                total += _sizeof(k) + _sizeof(v)

        return total

    def _touch(self, shard_key: str) -> None:
        """Mark *shard_key* as most recently used."""
        self._lru.pop(shard_key, None)
        self._lru[shard_key] = None

    def _evict_one(self) -> Optional[str]:
        """Evict the oldest shard from the LRU.  Returns evicted key or ``None``."""
        if not self._lru:
            return None
        oldest_key, _ = next(iter(self._lru.items()))
        self._lru.pop(oldest_key)
        evicted = self.shards.pop(oldest_key, None)
        if evicted is not None:
            mem = self._shard_mem.pop(oldest_key, 0)
            self._loaded_mem -= mem
            self._temp_expiry.pop(oldest_key, None)
            # Free the engine's in-memory arrays.
            evicted.index = {}
            evicted.doc_lengths = None
            evicted.id_map = {}
        return oldest_key

    def _evict_until_fits(self, incoming_bytes: int = 0) -> None:
        """Evict LRU shards until the budget accommodates *incoming_bytes*."""
        # Count-based cap
        if self._max_loaded:
            while len(self.shards) > self._max_loaded and self._lru:
                self._evict_one()
        # Memory-based cap
        if self._memory_limit:
            target = self._memory_limit - incoming_bytes
            while self._loaded_mem > target and self._lru:
                self._evict_one()

    def _register_engine(self, shard_key: str, engine: BaseEngine) -> None:
        """Store a loaded engine, measure its memory, and evict if needed."""
        mem = self._estimate_engine_memory(engine)
        # Warn if a single shard already exceeds the budget
        if self._memory_limit and mem > self._memory_limit and not self.shards:
            log.warning(
                "Shard '%s' uses %d MB — exceeds memory_limit_mb=%d. "
                "Loading anyway.",
                shard_key, mem // 1_048_576,
                self._memory_limit // 1_048_576,
            )
        self._evict_until_fits(mem)
        self.shards[shard_key] = engine
        self._shard_mem[shard_key] = mem
        self._loaded_mem += mem
        self._touch(shard_key)

    def _cleanup_expired(self) -> None:
        """Evict temporary shards whose TTL has passed."""
        if not self._temp_expiry:
            return
        now = time.monotonic()
        expired = [k for k, exp in self._temp_expiry.items() if now >= exp]
        for key in expired:
            self._temp_expiry.pop(key, None)
            self._lru.pop(key, None)
            evicted = self.shards.pop(key, None)
            if evicted is not None:
                mem = self._shard_mem.pop(key, 0)
                self._loaded_mem -= mem
                evicted.index = {}
                evicted.doc_lengths = None
                evicted.id_map = {}

    def _lazy_load(self, shard_key: str) -> None:
        """Load *shard_key* from storage if it is not currently in memory.

        No-op when lazy loading is disabled or the shard is already loaded.
        """
        if not self._lazy_base_name or shard_key in self.shards:
            return
        shard_name = f"{self._lazy_base_name}__shard__{shard_key}"
        engine = self._create_engine()
        engine.load_engine(shard_name)
        self._register_engine(shard_key, engine)

    # Properties

    @property
    def total_docs(self) -> int:
        """Total documents across all shards (uses cached metadata counts)."""
        if self._doc_counts:
            return sum(self._doc_counts.values())
        return sum(e.total_docs for e in self.shards.values())

    @property
    def shard_keys(self) -> List[str]:
        """Sorted list of all known shard keys (loaded and unloaded)."""
        if self._all_keys:
            return sorted(self._all_keys)
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
        """ID type used by the shards (e.g. ``"custom"`` or ``"sequential"``)."""
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
        if shard_key not in self._all_keys:
            self._all_keys.append(shard_key)
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

    def build_shards_streaming(
        self,
        row_iter,
        batch_size: int = 5_000,
        persist_base_name: Optional[str] = None,
        stream_ordered: bool = False,
    ) -> None:
        """Route and index documents from a streaming row iterator.

        Unlike :meth:`build_shards`, this method **never** materializes the
        full dataset in RAM.  Documents are consumed in *batch_size* chunks
        and routed to their shard.  Each shard buffer is flushed to its engine
        once it accumulates *batch_size* documents (or when the stream ends).

        When *persist_base_name* is given, each shard is persisted to storage
        **after** all data has been streamed and flushed.  If memory management
        is active, old shards are then evicted from RAM via
        :meth:`trim_to_budget`.

        When ``stream_ordered=True`` **and** memory management is active,
        shards that are guaranteed to be complete (because a newer date key
        has already arrived) are persisted and evicted immediately, keeping
        peak RAM low throughout the build.  **Only enable this if you are
        certain your data arrives sorted chronologically by the date column;
        enabling it on unsorted data will silently truncate shards.**

        This is the recommended path for datasets with > 100 K rows.

        Args:
            row_iter: Any iterable that yields ``(doc_id_str, text, date_val)``
                triples.  The simplest source is
                :meth:`~lucis.storage.AlchemyStorage.stream_table_with_dates`.
            batch_size: Maximum buffer size **per shard** before flushing.
                Tune this value to balance throughput vs. peak RAM.
                Default is 5 000 rows.
            persist_base_name: Versioned physical index name.  When provided,
                shards are persisted to storage after (or during, when
                ``stream_ordered=True``) the stream completes.
            stream_ordered: When ``True``, assumes rows arrive sorted
                chronologically.  Allows in-flight eviction of finished shards
                to keep peak RAM proportional to the working set, not the
                total dataset.  **Default is ``False`` — safe for any ordering.**
        """
        self.shards.clear()
        self._shard_mem.clear()
        self._loaded_mem = 0
        self._lru.clear()
        self._persisted_keys.clear()

        # Per-shard raw buffers: shard_key → {doc_id: text}
        buffers: Dict[str, Dict[str, str]] = defaultdict(dict)
        # Track which shards have had their first build_index call
        initialized: set = set()
        # Highest non-global shard key seen so far (for ordered eviction)
        highest_key: Optional[str] = None

        # Ordered eviction is only useful when we can persist during build
        can_evict_ordered = (
            stream_ordered
            and persist_base_name is not None
            and self._is_managed
        )

        def _flush(shard_key: str) -> None:
            buf = buffers.pop(shard_key, {})
            if not buf:
                return
            engine = self.get_or_create_shard(shard_key)
            if shard_key in initialized:
                engine.add_documents(buf)
            else:
                engine.build_index(buf)
                initialized.add(shard_key)

        def _persist_and_evict_closed(current_key: str) -> None:
            """Persist + evict all shards older than *current_key*.

            A shard is "closed" when its key is strictly less than the
            current key (meaning no more data can arrive for it given
            chronological ordering) and its buffer has already been flushed.
            The global shard is never evicted here — NULLs can appear
            anywhere in the stream.
            """
            closeable = [
                k for k in sorted(self.shards.keys())
                if k != LUCIS_GLOBAL_SHARD
                and k < current_key
                and k not in buffers   # buffer empty → already flushed
            ]
            if not closeable:
                return

            for key in closeable:
                engine = self.shards[key]
                shard_name = f"{persist_base_name}__shard__{key}"
                engine.persist(shard_name)
                self._persisted_keys.add(key)
                self._doc_counts[key] = engine.total_docs

                mem = self._shard_mem.pop(key, None)
                if mem is None:
                    mem = self._estimate_engine_memory(engine)
                self._loaded_mem -= mem
                self._lru.pop(key, None)

                engine.index = {}
                engine.doc_lengths = None
                engine.id_map = {}
                del self.shards[key]

                log.info(
                    "[stream_ordered] Persisted & evicted shard '%s' "
                    "(freed ~%d MB, RAM now ~%.0f MB).",
                    key, mem // 1_048_576, self._loaded_mem / 1_048_576,
                )

        for doc_id, text, date_val in row_iter:
            shard_key = date_to_shard_key(date_val)
            buffers[shard_key][doc_id] = text
            if len(buffers[shard_key]) >= batch_size:
                _flush(shard_key)

            # Ordered eviction: when we see a key newer than anything before,
            # all older shards with empty buffers are definitively closed.
            if (
                can_evict_ordered
                and shard_key != LUCIS_GLOBAL_SHARD
            ):
                if highest_key is None or shard_key > highest_key:
                    highest_key = shard_key
                    _persist_and_evict_closed(shard_key)

        # Flush all remaining buffers
        for shard_key in list(buffers.keys()):
            _flush(shard_key)

        # --- Post-build: persist remaining shards to storage ---
        if persist_base_name:
            still_in_ram = {
                k: e for k, e in self.shards.items()
                if k not in self._persisted_keys
            }
            for shard_key, engine in still_in_ram.items():
                shard_name = f"{persist_base_name}__shard__{shard_key}"
                engine.persist(shard_name)
                self._persisted_keys.add(shard_key)
                self._doc_counts[shard_key] = engine.total_docs

            total_docs = sum(
                self._doc_counts.get(k, getattr(e, "total_docs", 0))
                for k, e in list(self.shards.items())
            ) + sum(
                self._doc_counts.get(k, 0)
                for k in self._persisted_keys
                if k not in self.shards
            )
            log.info(
                "Build complete: %d shards total (%d in RAM, %d already evicted), "
                "~%d total docs. Trimming RAM to budget...",
                len(self._persisted_keys), len(self.shards),
                len(self._persisted_keys) - len(self.shards),
                total_docs,
            )

    def add_documents(
        self,
        new_docs: Dict[str, str],
        dates: Dict[str, Any],
    ) -> None:
        """Incrementally add documents to the appropriate shards.

        Each document is routed to its shard by date.  If the shard
        already exists and the engine supports incremental indexing,
        ``add_documents()`` is called on it.  Otherwise the shard is
        initialised with ``build_index()``.

        Args:
            new_docs: ``{doc_id: text}`` mapping of new documents.
            dates: ``{doc_id: date_value}`` used for shard routing
                (same keys as *new_docs*).
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

        When memory management is active (``memory_limit_mb`` or
        ``max_loaded_shards``), the method works as follows:

        * **No date range** (``since`` / ``until`` both ``None``): only
          searches shards currently loaded in RAM — fast, zero I/O.
        * **With date range**: missing shards inside the range are loaded
          on-the-fly and given a TTL (default 30 s) so they auto-evict
          on the next search call, keeping RAM bounded.

        Args:
            query_tokens: Pre-processed query (str or token list).
            top_k: Maximum results.
            since: Start shard key or ISO date (inclusive).
            until: End shard key or ISO date (inclusive).

        Returns:
            ``[(doc_id, score, shard_key), ...]`` sorted by score
            descending, limited to *top_k*.
        """
        # Housekeeping: evict expired temporary shards (fast, O(n) on tiny dict).
        self._cleanup_expired()

        since_key = normalize_to_shard_key(since)
        until_key = normalize_to_shard_key(until)

        all_results: List[Tuple[DocId, float, str]] = []
        has_date_filter = since is not None or until is not None

        # When a date filter is given, determine the full set of keys to search
        # (including unloaded ones) so we can temporarily load them.
        # Without a date filter, only search what is already in RAM (fast path).
        if has_date_filter and self._lazy_base_name:
            search_keys = [
                k for k in self.shard_keys
                if shard_key_in_range(k, since_key, until_key)
            ]
            # Load missing shards temporarily
            for key in search_keys:
                if key not in self.shards:
                    self._lazy_load(key)
                    # Mark as temporary — will expire after TTL
                    self._temp_expiry[key] = (
                        time.monotonic() + self._ttl_seconds
                    )
        else:
            search_keys = sorted(self.shards.keys())
            if since_key or until_key:
                search_keys = [
                    k for k in search_keys
                    if shard_key_in_range(k, since_key, until_key)
                ]

        for key in sorted(search_keys):
            if key not in self.shards:
                continue
            if self._is_managed:
                self._touch(key)
            shard_results = self.shards[key].search(query_tokens, top_k=top_k)
            for doc_id, score in shard_results:
                all_results.append((doc_id, score, key))

        all_results.sort(key=lambda x: x[1], reverse=True)
        return all_results[:top_k]

    # Persistence

    def persist_all(self, base_name: str) -> List[str]:
        """Persist every shard to storage.

        Each shard is saved as ``{base_name}__shard__{key}``.
        Shards already persisted during ``build_shards_streaming``
        (tracked in ``_persisted_keys``) are skipped.

        Args:
            base_name: The versioned physical name.

        Returns:
            List of **all** shard keys (persisted now + persisted earlier).
        """
        already = getattr(self, "_persisted_keys", set())
        shard_keys = list(already)   # include shards persisted during build

        for shard_key, engine in self.shards.items():
            if shard_key in already:
                continue  # already saved during build
            shard_name = f"{base_name}__shard__{shard_key}"
            engine.persist(shard_name)
            shard_keys.append(shard_key)

        self._storage.save_shard_registry(base_name, shard_keys)
        return shard_keys

    def load_all(
        self,
        base_name: str,
        shard_keys: Optional[List[str]] = None,
        lazy: bool = False,
    ) -> None:
        """Load shards from storage.

        Args:
            base_name: The versioned physical name.
            shard_keys: Explicit shard keys.  If ``None``, reads from
                the shard registry.
            lazy: When ``True``, only the newest shards that fit inside
                the configured memory budget (or ``max_loaded_shards``
                count) are loaded eagerly.  The rest stay registered
                in ``_all_keys`` and can be loaded on-demand via
                :meth:`search` (with ``since``/``until``) or
                :meth:`preload_shards`.
        """
        if shard_keys is None:
            shard_keys = self._storage.load_shard_registry(base_name)

        self.shards.clear()
        self._all_keys = list(shard_keys)
        self._shard_mem.clear()
        self._loaded_mem = 0
        self._lru.clear()
        self._temp_expiry.clear()

        if lazy:
            self._lazy_base_name = base_name
            # Pre-fetch doc counts from metadata (lightweight).
            if hasattr(self._storage, "get_total_docs"):
                for key in shard_keys:
                    shard_name = f"{base_name}__shard__{key}"
                    self._doc_counts[key] = self._storage.get_total_docs(shard_name)

            # Load newest-first until the budget is exhausted.
            recent_keys = sorted(shard_keys, reverse=True)
            for shard_key in recent_keys:
                # Check budget BEFORE loading
                if self._max_loaded and len(self.shards) >= self._max_loaded:
                    break
                if self._memory_limit and self._loaded_mem >= self._memory_limit * 0.9:
                    break

                shard_name = f"{base_name}__shard__{shard_key}"
                engine = self._create_engine()
                engine.load_engine(shard_name)
                self._register_engine(shard_key, engine)

            loaded_count = len(self.shards)
            total_count = len(shard_keys)
            if loaded_count < total_count:
                log.info(
                    "Loaded %d / %d shards (%.0f MB).  "
                    "Remaining %d shards available via search(since/until) "
                    "or preload_shards().",
                    loaded_count,
                    total_count,
                    self._loaded_mem / 1_048_576,
                    total_count - loaded_count,
                )
            return

        # Eager load (original behaviour — all shards, no budget).
        self._lazy_base_name = None
        for shard_key in shard_keys:
            shard_name = f"{base_name}__shard__{shard_key}"
            engine = self._create_engine()
            engine.load_engine(shard_name)
            self.shards[shard_key] = engine
            # Track memory even in eager mode (for stats).
            mem = self._estimate_engine_memory(engine)
            self._shard_mem[shard_key] = mem
            self._loaded_mem += mem

    def preload_shards(
        self,
        since: Optional[str] = None,
        until: Optional[str] = None,
        n_recent: Optional[int] = None,
    ) -> List[str]:
        """Explicitly load shards into memory without blocking searches.

        Use this after ``load_all(lazy=True)`` to warm specific shards before
        querying historical data.  Respects the LRU eviction limit and
        memory budget so RAM stays bounded.

        Args:
            since: Load shards at or after this key / ISO date.
            until: Load shards at or before this key / ISO date.
            n_recent: If given, load only the *n_recent* most recent shards
                that fall in the range (most recent first).

        Returns:
            List of shard keys that were newly loaded (already-loaded shards
            are skipped).
        """
        if not self._lazy_base_name:
            return []  # lazy mode not active; nothing to do

        since_key = normalize_to_shard_key(since)
        until_key = normalize_to_shard_key(until)
        candidates = [
            k for k in self._all_keys
            if shard_key_in_range(k, since_key, until_key)
        ]
        candidates = sorted(candidates, reverse=True)  # most recent first
        if n_recent is not None:
            candidates = candidates[:n_recent]

        loaded: List[str] = []
        for shard_key in candidates:
            if shard_key in self.shards:
                self._touch(shard_key)
                continue
            self._lazy_load(shard_key)
            loaded.append(shard_key)
        return loaded

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

    @property
    def loaded_memory_mb(self) -> float:
        """Approximate RAM used by all currently-loaded shard engines (MB)."""
        return self._loaded_mem / 1_048_576

    def trim_to_budget(self) -> int:
        """Evict old shards until the memory / count budget is satisfied.

        Useful after ``build_shards_streaming`` + ``persist_all`` to release
        RAM from shards that have already been saved to storage.

        Returns:
            Number of shards evicted.
        """
        if not self._is_managed:
            return 0
        # Ensure _all_keys and _lazy_base_name are set so evicted shards
        # can be reloaded later if needed.
        if not self._all_keys:
            self._all_keys = list(self.shards.keys())
        # Populate LRU for shards that aren't tracked yet (post-build).
        for key in sorted(self.shards.keys()):
            if key not in self._lru:
                self._touch(key)
        # Measure shards that aren't tracked yet.
        for key, engine in list(self.shards.items()):
            if key not in self._shard_mem:
                mem = self._estimate_engine_memory(engine)
                self._shard_mem[key] = mem
                self._loaded_mem += mem

        before = len(self.shards)
        self._evict_until_fits(0)
        return before - len(self.shards)

    def shard_stats(self) -> Dict[str, int]:
        """Return document counts per shard.

        Returns:
            ``{shard_key: doc_count}`` dict sorted by shard key.
        """
        return {k: e.total_docs for k, e in sorted(self.shards.items())}

    def __repr__(self) -> str:
        """Return an informative string representation of the manager."""
        keys = ", ".join(sorted(self.shards.keys()))
        extra = ""
        if self._is_managed:
            extra = f", loaded_mem={self.loaded_memory_mb:.0f}MB"
            if len(self._all_keys) > len(self.shards):
                extra += f", unloaded={len(self._all_keys) - len(self.shards)}"
        return (
            f"ShardManager(shards={len(self.shards)}, "
            f"total_docs={self.total_docs}, keys=[{keys}]{extra})"
        )
