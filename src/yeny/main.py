"""
Yeny — Main facade module.

This module defines the ``Yeny`` class, which is the **single entry
point** for all user-facing operations.  The implementation is split
across four mixins (in ``yeny.mixins``) and a synchronization layer
(in ``yeny.sync``) to keep each file focused and maintainable:

- ``LoaderMixin``: factory class methods (``from_dict``, ``from_table``, …)
- ``SearchMixin``: search orchestration and shard preloading.
- ``PersistenceMixin``: save, load, versioning, rollback, binary generation.
- ``AutomationMixin``: indexing, reindex, incremental updates, worker creation,
  health monitoring, and source connection.

Shared internal utilities (engine registry, lazy imports, SQL helpers)
live in ``yeny._internals`` to avoid circular imports between the
facade and the mixins.
"""
import os
import threading
from typing import Any, Callable, Dict, List, Optional, Union

from .config import YenyOptions
from .storage.base import BaseStorage
from .storage.json_storage import JSONStorage
from .storage.sqlite_storage import SQLiteStorage
from .storage.metadata_storage import MetadataStorage
from .storage.memory_storage import MemoryStorage
from .exceptions import YenyEngineError
from .core.shard import ShardManager
from .sync.source_spec import SourceSpec
from ._internals import (
    _ENGINE_REGISTRY,
    _get_alchemy_storage_class,
    _build_sql_text_expr,
)
from .mixins.loaders import LoaderMixin
from .mixins.search import SearchMixin
from .mixins.persistence import PersistenceMixin
from .mixins.automation import AutomationMixin


class Yeny(LoaderMixin, SearchMixin, PersistenceMixin, AutomationMixin):
    """
    The friendly face of Yeny.
    
    Yeny is an orchestrator (Facade pattern) that simplifies building
    custom search engines. It connects engines, storage, and tokenizers
    behind a clean, minimal API.

    Three ways to create a Yeny instance:
    1. From scratch with data:
        yn = Yeny.from_dict({"doc1": "hello world"}, name="my_search")
        yn = Yeny.from_list(["hello world"], name="my_search")
    
    2. Load an existing index from disk:
        yn = Yeny(name="my_search")  # Auto-loads if exists
    
    3. Empty instance for later use:
        yn = Yeny(name="my_search", autoload=False)
        yn.index(data)

    The implementation is modular — each mixin group handles a
    distinct responsibility.  See ``yeny.mixins`` and ``yeny.sync``
    for the full breakdown.
    """

    def __init__(
        self,
        name: str = "default",
        engine: str = "core",
        preprocessor: Optional[Callable[[str], Union[str, List[str]]]] = None,
        *,
        autoload: bool = True,
        storage: Optional[BaseStorage] = None,
        options: Optional[YenyOptions] = None,
    ) -> None:
        """
        Base constructor: sets up identity, storage, and engine.
        Does NOT ingest data — use .index(), .from_dict(), or .from_list() for that.

        Args:
            name: Identifier for the index. Used for persistence (filename/table).
            engine: Which engine to use. Supported: ``"core"`` and ``"lite"``.
            preprocessor: Text preprocessor callable ``(str) → str | list[str]``. Defaults to WordTokenizer().
                Can return ``list[str]`` (tokens used directly) or ``str`` (Yeny will apply
                SimpleTokenizer as a final tokenization step). The same preprocessor is used
                for both indexing and searching to ensure a consistent vector space.
                Examples::

                    # Custom pipeline: clean + tokenize
                    Yeny(preprocessor=lambda t: WordTokenizer()(remove_stopwords(t)))

                    # Char n-gram search (e.g. for emails or encrypted data)
                    Yeny(preprocessor=CharNgramTokenizer(3))

                    # Text-only preprocessing — Yeny tokenizes the returned str automatically
                    Yeny(preprocessor=lambda t: t.lower().strip())
            autoload: If True and an index with this name exists on disk, load it automatically.
            storage: A pre-built storage object.  It takes precedence over the
                declarative storage fields in ``options``.
            options: Advanced infrastructure configuration.  ``None`` is
                equivalent to ``YenyOptions()`` and preserves the historical
                defaults.  Its ``binary_dir`` field is tri-state: ``"auto"``
                derives ``<storage_dir>/yny``, ``None`` disables binary
                persistence, and any other string is an explicit directory.

        Storage precedence:
            An explicit ``storage`` object always wins.  Otherwise
            ``options.storage_type`` selects JSON, SQLite, or SQLAlchemy
            persistence; SQLite requires ``options.db_path`` and SQLAlchemy
            requires ``options.connection_url``.
        """
        resolved_options = options or YenyOptions()
        storage_dir = resolved_options.storage_dir
        storage_type = resolved_options.storage_type
        db_path = resolved_options.db_path
        connection_url = resolved_options.connection_url
        max_loaded_shards = resolved_options.max_loaded_shards
        memory_limit_mb = resolved_options.memory_limit_mb
        binary_dir = resolved_options.binary_dir

        self.name = name
        self._is_indexed = False
        self._source_info: Optional[SourceSpec] = None
        self._shard_manager: Optional[ShardManager] = None
        self._max_loaded_shards: int = max_loaded_shards
        self._memory_limit_mb: Optional[int] = memory_limit_mb
        # Reader for source data (production DB). Set by from_table().
        self._reader: Optional[Any] = None
        # If user provides a preprocessor, use it globally.
        # If None, the engine will use its own default:
        #   CoreEngine → WordTokenizer()
        #   LiteEngine → CharNgramTokenizer(3) + lowercase
        self._user_preprocessor = preprocessor
        self.preprocessor: Optional[Callable[[str], Union[str, List[str]]]] = preprocessor

        # Check in-memory execution mode
        is_mem_type = storage_type is None or (
            isinstance(storage_type, str) and storage_type.lower() in ("memory", "none")
        )
        self._in_memory: bool = (
            (getattr(storage, "_in_memory", False) or is_mem_type)
            if storage is not None
            else is_mem_type
        )

        # Binary / mmap directory resolution (single source of truth)
        if self._in_memory or binary_dir is False or binary_dir is None:
            self._binary_dir: Optional[str] = None
        elif binary_dir is True or binary_dir == "auto":
            self._binary_dir = os.path.join(storage_dir, "yny")
        else:
            self._binary_dir = str(binary_dir)

        # Background rebuild state (Phase 3)
        self._rebuild_thread: Optional[threading.Thread] = None
        self._rebuild_error: Optional[Exception] = None

        # 1. Configure storage and persistence
        if storage is not None:
            self.storage = storage
        elif self._in_memory:
            self.storage = MemoryStorage()
        elif storage_type == "alchemy":
            if connection_url is None:
                raise ValueError(
                    "connection_url is required when storage_type='alchemy'. "
                    "Example: Yeny(options=YenyOptions("
                    "storage_type='alchemy', "
                    "connection_url='mysql+pymysql://user:pass@localhost/mydb'))"
                )
            AlchemyStorage = _get_alchemy_storage_class()
            self.storage = AlchemyStorage(url=connection_url)
        elif storage_type == "sqlite":
            if db_path is None:
                raise ValueError(
                    "db_path is required when storage_type='sqlite'. "
                    "Example: Yeny(options=YenyOptions("
                    "storage_type='sqlite', db_path='my_data.db'))"
                )
            self.storage = SQLiteStorage(db_path=db_path)
        elif storage_type == "json" or self._binary_dir is None:
            # Explicit JSON backend request or binary persistence disabled
            self.storage = JSONStorage(directory=storage_dir)
        else:
            # Default persistence: MetadataStorage (SQLite WAL yeny_meta.db) + .yny
            meta_db_path = os.path.join(self._binary_dir, "yeny_meta.db")
            self.storage = MetadataStorage(db_path=meta_db_path)

        # 1b. Transparent fallback for existing JSON indexes on autoload:
        if (
            autoload
            and not self._in_memory
            and storage is None
            and not (storage_type in ("sqlite", "alchemy"))
            and not self.storage.exists(name)
        ):
            json_candidate = os.path.join(storage_dir, f"{name}.json")
            if os.path.isfile(json_candidate):
                self.storage = JSONStorage(directory=storage_dir)

        # 2. Configure engine
        # The registry pattern lets us add engines without touching Yeny's code
        engine_class = _ENGINE_REGISTRY.get(engine)
        if engine_class is None:
            available = ", ".join(_ENGINE_REGISTRY.keys())
            raise YenyEngineError(
                engine_name=engine,
                detail=f"Unknown engine '{engine}'. Available: {available}"
            )
        # Pass the user's preprocessor (may be None — the engine will use its own default)
        self.engine = engine_class(storage=self.storage, preprocessor=self._user_preprocessor)
        # Sync: Yeny.preprocessor always reflects the engine's resolved preprocessor
        self.preprocessor = self.engine.preprocessor

        # 3. Smart persistence: if the index already exists on disk, load it
        # This enables the "pick up where you left off" workflow:
        #   yn = Yeny(name="my_index")  →  ready to search immediately
        # The name may be an alias — exists() resolves it transparently.
        if autoload and self.storage.exists(name):
            self.load()

    # Shard support

    @property
    def is_indexed(self) -> bool:
        """``True`` when the index has been built or loaded."""
        return self._is_indexed

    @property
    def is_in_memory(self) -> bool:
        """``True`` if this instance runs 100% in RAM without disk persistence."""
        return self._in_memory

    @property
    def is_sharded(self) -> bool:
        """``True`` if this index uses temporal sharding."""
        return self._shard_manager is not None

    @property
    def total_docs(self) -> int:
        """Total number of indexed documents (sharded or not)."""
        if self._shard_manager is not None:
            return self._shard_manager.total_docs
        return self.engine.total_docs if self._is_indexed else 0

    @property
    def loaded_memory_mb(self) -> float:
        """Approximate RAM used by currently-loaded shard engines (MB)."""
        if self._shard_manager is not None:
            return self._shard_manager.loaded_memory_mb
        return 0.0

    def _init_shard_manager(self) -> None:
        """Initialise a :class:`~yeny.core.shard.ShardManager` bound to
        the current engine class, storage backend, and preprocessor.
        """
        self._shard_manager = ShardManager(
            engine_class=type(self.engine),
            storage=self.storage,
            preprocessor=self._user_preprocessor,
            max_loaded_shards=self._max_loaded_shards,
            memory_limit_mb=self._memory_limit_mb,
            binary_dir=self._binary_dir,
        )

    # Post-index cleanup

    def _post_index_cleanup(self, logical_name: str) -> None:
        """Reload the index from storage to shed build-time RAM overhead.

        During indexing, engines accumulate intermediate structures
        (raw dicts, tokenized lists, etc.) that are significantly
        heavier than the compact/mmap representations loaded from
        storage.  This method destroys the build-time shard manager
        and reloads from storage — the same path taken by a cold
        start with an existing index — so steady-state RAM matches
        the lightweight pre-loaded profile.

        When dirty-tracking is available (incremental ``add_documents``),
        only the modified shards are reloaded — the rest keep their
        existing mmap handles intact.

        Also clears any ``functools.lru_cache`` on the preprocessor
        pipeline, which can accumulate millions of entries during
        bulk indexing.
        """
        # Preserve source_info before reload (load() restores it
        # from storage, but belt-and-suspenders).
        source_info = self._source_info

        # Decide between selective and full cleanup
        if self._shard_manager and self._shard_manager.has_dirty_shards:
            self._selective_cleanup(logical_name, source_info)
        else:
            self._full_cleanup(logical_name, source_info)

    def _selective_cleanup(self, logical_name: str, source_info) -> None:
        """Reload only dirty shards from .yny / storage.

        Used after incremental operations (``add_documents``,
        ``remove_documents``) where only a subset of shards changed.
        The rest keep their existing mmap handles intact.
        """
        import gc
        import logging
        _log = logging.getLogger(__name__)

        reloaded = self._shard_manager.reload_dirty_shards(
            logical_name, self.storage,
        )

        # Clear preprocessor caches
        self._clear_preprocessor_caches()

        gc.collect()
        _log.info(
            "Selective post-index cleanup: reloaded %d dirty shard(s) "
            "for '%s' (%.1f MB in RAM).",
            reloaded,
            logical_name,
            self._shard_manager.loaded_memory_mb,
        )

        if source_info:
            self._source_info = source_info

    def _full_cleanup(self, logical_name: str, source_info) -> None:
        """Tear down all shards and reload from storage.

        Used after an initial build or full reindex, where all
        shards must be discarded and reloaded from storage.
        """
        import gc
        import logging
        _log = logging.getLogger(__name__)

        # Tear down build-time shard manager completely.
        if self._shard_manager:
            self._shard_manager.teardown_all()
        self._shard_manager = None

        # Clear preprocessor caches (lru_cache on HMAC functions).
        self._clear_preprocessor_caches()

        # Force garbage collection before reload to release
        # build-time objects and (on CPython) return arenas.
        gc.collect()

        # Reload from storage — uses the lightweight load path
        # (mmap for .yny, compact freeze for DB-backed).
        self.load(logical_name)

        # Restore source info
        if source_info:
            self._source_info = source_info

        # Final GC pass to clean up any stragglers.
        gc.collect()

        _log.info(
            "Post-index cleanup complete: reloaded '%s' from storage "
            "(%.1f MB in RAM).",
            logical_name,
            self._shard_manager.loaded_memory_mb if self._shard_manager else 0,
        )

    def _clear_preprocessor_caches(self) -> None:
        """Clear lru_cache entries on the preprocessor and its module."""
        if self.preprocessor:
            for attr_name in dir(self.preprocessor):
                obj = getattr(self.preprocessor, attr_name, None)
                if hasattr(obj, "cache_clear"):
                    obj.cache_clear()
            mod = getattr(self.preprocessor, "__module__", None)
            if mod:
                import sys
                mod_obj = sys.modules.get(mod)
                if mod_obj:
                    for attr in dir(mod_obj):
                        fn = getattr(mod_obj, attr, None)
                        if callable(fn) and hasattr(fn, "cache_clear"):
                            fn.cache_clear()

    # Info and debugging

    def __repr__(self) -> str:
        """Return an informative string representation of the Yeny instance."""
        status = "indexed" if self._is_indexed else "empty"

        if self._shard_manager:
            docs = self._shard_manager.total_docs
            n_shards = len(self._shard_manager.shards)
            return (
                f"Yeny(name='{self.name}', engine='{self.engine.name}', "
                f"docs={docs}, shards={n_shards}, status='{status}')"
            )
        else:
            docs = self.engine.total_docs if self._is_indexed else 0
            id_t = self.engine.id_type if self._is_indexed else "N/A"
            return (
                f"Yeny(name='{self.name}', engine='{self.engine.name}', "
                f"docs={docs}, idx_type='{id_t}', status='{status}')"
            )
