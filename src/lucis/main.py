import os
import time
import threading
from typing import Any, Callable, Dict, List, Optional, Union
from .engines.core import CoreEngine
from .engines.lite import LiteEngine
from .engines.base import DocId
from .storage.base import BaseStorage
from .storage.json_storage import JSONStorage
from .storage.sqlite_storage import SQLiteStorage
from .exceptions import LucisEngineError
from .models.search import SearchResult, SearchResponse
from .utils.nlp import word_tokenizer, simple_tokenizer
from .core.worker import IndexWorker
from .core.health import health_check as _health_check, HealthMonitor, HealthReport
from .core.shard import (
    ShardManager,
    normalize_to_shard_key,
    shard_key_in_range,
    LUCIS_GLOBAL_SHARD,
)

# Lazy import flag — AlchemyStorage requires sqlalchemy (optional dep)
_AlchemyStorage = None

def _get_alchemy_storage_class():
    """Lazy-load ``AlchemyStorage`` to avoid a hard dependency on SQLAlchemy.

    Returns:
        The :class:`~lucis.storage.AlchemyStorage` class, imported on
        first call and cached globally afterwards.
    """
    global _AlchemyStorage
    if _AlchemyStorage is None:
        from .storage.alchemy_storage import AlchemyStorage
        _AlchemyStorage = AlchemyStorage
    return _AlchemyStorage

# Engine registry - maps friendly names to engine classes
# As new engines are added, register them here
_ENGINE_REGISTRY = {
    "core": CoreEngine,
    "lite": LiteEngine,
}


def _build_sql_text_expr(text_column):
    """Build a raw SQL expression for single or multi-column text.

    Used for SQLite raw SQL queries.  Concatenates multiple columns
    with spaces using ``||`` and wraps each in ``COALESCE(col, '')``
    to handle NULLs.

    Args:
        text_column: A single column name (str) or list of column names.

    Returns:
        A SQL expression string.
    """
    if isinstance(text_column, str):
        return text_column
    if len(text_column) == 1:
        return text_column[0]
    coalesced = [f"COALESCE({col}, '')" for col in text_column]
    return " || ' ' || ".join(coalesced)


class Lucis:
    """
    The friendly face of Lucis.
    
    Lucis is an orchestrator (Facade pattern) that simplifies building
    custom search engines. It connects engines, storage, and tokenizers
    behind a clean, minimal API.

    Three ways to create a Lucis instance:
    1. From scratch with data:
        lu = Lucis.from_dict({"doc1": "hello world"}, name="my_search")
        lu = Lucis.from_list(["hello world"], name="my_search")
    
    2. Load an existing index from disk:
        lu = Lucis(name="my_search")  # Auto-loads if exists
    
    3. Empty instance for later use:
        lu = Lucis(name="my_search", autoload=False)
        lu.index(data)
    """

    def __init__(
        self, 
        name: str = "default",
        storage_dir: str = "lucis_data",
        storage_type: str = "json",
        db_path: Optional[str] = None,
        alchemy_url: Optional[str] = None,
        storage: Optional[BaseStorage] = None,
        engine: str = "core",
        preprocessor: Optional[Callable[[str], Union[str, List[str]]]] = None,
        autoload: bool = True,
        max_loaded_shards: int = 0,
        memory_limit_mb: Optional[int] = None,
        binary_dir: Optional[str] = "auto",
    ):
        """
        Base constructor: sets up identity, storage, and engine.
        Does NOT ingest data — use .index(), .from_dict(), or .from_list() for that.

        Args:
            name: Identifier for the index. Used for persistence (filename/table).
            storage_dir: Directory where the JSON index files are stored (only for storage_type="json").
            storage_type: Backend to use for persistence — "json", "sqlite", or "alchemy".
            db_path: Path to the SQLite database (required when storage_type="sqlite" and no *storage* is given).
            alchemy_url: SQLAlchemy connection URL (required when storage_type="alchemy" and no *storage* is given).
            Example: "mysql+pymysql://user:pass@localhost/mydb"
            storage: A pre-built BaseStorage instance (overrides storage_type/db_path/storage_dir).
            engine: Which engine to use. Currently supported: "core".
            preprocessor: Text preprocessor function ``(str) → str | list[str]``. Defaults to word_tokenizer.
                Can return ``list[str]`` (tokens used directly) or ``str`` (Lucis will apply
                simple_tokenizer as a final tokenization step). The same preprocessor is used
                for both indexing and searching to ensure a consistent vector space.
                Examples::

                    # Custom pipeline: clean + tokenize
                    Lucis(preprocessor=lambda t: word_tokenizer(remove_stopwords(t)))

                    # Char n-gram search (e.g. for emails or encrypted data)
                    Lucis(preprocessor=char_ngram_tokenizer(3))

                    # Text-only preprocessing — Lucis tokenizes the returned str automatically
                    Lucis(preprocessor=lambda t: t.lower().strip())
            autoload: If True and an index with this name exists on disk, load it automatically.
            max_loaded_shards: Maximum number of shards to keep in RAM simultaneously.
                ``0`` (default) loads all shards eagerly (original behaviour).
                Set e.g. ``6`` to keep only the 6 most recently accessed shards loaded,
                evicting older ones on demand.  Requires a sharded index.
            memory_limit_mb: Maximum RAM budget (in megabytes) for loaded shards.
                ``None`` (default) = no limit.  When set, the system loads the
                newest shards first until the budget is ~90 % full, then stops.
                Historical queries via ``search(since=..., until=...)`` temporarily
                load extra shards that auto-expire after 30 seconds.
            binary_dir: Directory for ``.lcs`` (Lucis Compact Shard) binary
                files.  When set, shards are persisted as mmap-friendly
                binaries alongside the regular storage, enabling near-zero
                RAM loading via memory-mapped I/O.
                ``"auto"`` (default) derives the directory automatically
                from the storage configuration.  ``None`` disables binary
                persistence entirely.
        """
        self.name = name
        self._is_indexed = False
        self._source_info: Optional[Dict[str, Optional[str]]] = None
        self._shard_manager: Optional[ShardManager] = None
        self._max_loaded_shards: int = max_loaded_shards
        self._memory_limit_mb: Optional[int] = memory_limit_mb
        # If user provides a preprocessor, use it globally.
        # If None, the engine will use its own default:
        #   CoreEngine → word_tokenizer
        #   LiteEngine → char_ngram_tokenizer(3) + lowercase
        self._user_preprocessor = preprocessor
        self.preprocessor: Optional[Callable[[str], Union[str, List[str]]]] = preprocessor

        # Binary / mmap directory resolution
        if binary_dir == "auto":
            self._binary_dir: Optional[str] = os.path.join(storage_dir, "lcs")
        else:
            self._binary_dir = binary_dir

        # Background rebuild state (Phase 3)
        self._rebuild_thread: Optional[threading.Thread] = None
        self._rebuild_error: Optional[Exception] = None

        # 1. Configure storage
        if storage is not None:
            # Advanced users can inject their own storage instance
            self.storage = storage
        elif storage_type == "alchemy":
            if alchemy_url is None:
                raise ValueError(
                    "alchemy_url is required when storage_type='alchemy'. "
                    "Example: Lucis(storage_type='alchemy', "
                    "alchemy_url='mysql+pymysql://user:pass@localhost/mydb')"
                )
            AlchemyStorage = _get_alchemy_storage_class()
            self.storage = AlchemyStorage(url=alchemy_url)
        elif storage_type == "sqlite":
            if db_path is None:
                raise ValueError(
                    "db_path is required when storage_type='sqlite'. "
                    "Example: Lucis(storage_type='sqlite', db_path='my_data.db')"
                )
            self.storage = SQLiteStorage(db_path=db_path)
        else:
            # Default: lightweight JSON files
            self.storage = JSONStorage(directory=storage_dir)

        # 2. Configure engine
        # The registry pattern lets us add engines without touching Lucis's code
        engine_class = _ENGINE_REGISTRY.get(engine)
        if engine_class is None:
            available = ", ".join(_ENGINE_REGISTRY.keys())
            raise LucisEngineError(
                engine_name=engine,
                detail=f"Unknown engine '{engine}'. Available: {available}"
            )
        # Pass the user's preprocessor (may be None — the engine will use its own default)
        self.engine = engine_class(storage=self.storage, preprocessor=self._user_preprocessor)
        # Sync: Lucis.preprocessor always reflects the engine's resolved preprocessor
        self.preprocessor = self.engine.preprocessor

        # 3. Smart persistence: if the index already exists on disk, load it
        # This enables the "pick up where you left off" workflow:
        #   lu = Lucis(name="my_index")  →  ready to search immediately
        # The name may be an alias — exists() resolves it transparently.
        if autoload and self.storage.exists(name):
            self.load()

    # Shard support

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
        """Initialise a :class:`~lucis.core.shard.ShardManager` bound to
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

    def _post_index_cleanup(self, logical_name: str) -> None:
        """Reload the index from storage to shed build-time RAM overhead.

        During indexing, engines accumulate intermediate structures
        (raw dicts, tokenized lists, etc.) that are significantly
        heavier than the compact/mmap representations loaded from
        storage.  This method destroys the build-time shard manager
        and reloads from storage — the same path taken by a cold
        start with an existing index — so steady-state RAM matches
        the lightweight pre-loaded profile.

        Also clears any ``functools.lru_cache`` on the preprocessor
        pipeline, which can accumulate millions of entries during
        bulk indexing.
        """
        import gc
        import logging
        _log = logging.getLogger(__name__)

        # 1. Preserve source_info before reload (load() restores it
        #    from storage, but belt-and-suspenders).
        source_info = self._source_info

        # 2. Tear down build-time shard manager completely.
        if self._shard_manager:
            for key in list(self._shard_manager.shards.keys()):
                engine = self._shard_manager.shards[key]
                close_fn = getattr(engine, "close_mmap", None)
                if close_fn:
                    close_fn()
                else:
                    engine.index = {}
                    engine.doc_lengths = None
                    engine.id_map = {}
            self._shard_manager.shards.clear()
            self._shard_manager._shard_mem.clear()
            self._shard_manager._lru.clear()
            self._shard_manager._loaded_mem = 0
        self._shard_manager = None

        # 3. Clear preprocessor caches (lru_cache on HMAC functions).
        if self.preprocessor:
            # Walk the preprocessor's closure/globals for lru_cache'd callables
            for attr_name in dir(self.preprocessor):
                obj = getattr(self.preprocessor, attr_name, None)
                if hasattr(obj, "cache_clear"):
                    obj.cache_clear()
            # Also check the module the preprocessor lives in
            mod = getattr(self.preprocessor, "__module__", None)
            if mod:
                import sys
                mod_obj = sys.modules.get(mod)
                if mod_obj:
                    for attr in dir(mod_obj):
                        fn = getattr(mod_obj, attr, None)
                        if callable(fn) and hasattr(fn, "cache_clear"):
                            fn.cache_clear()

        # 4. Force garbage collection before reload to release
        #    build-time objects and (on CPython) return arenas.
        gc.collect()

        # 5. Reload from storage — uses the lightweight load path
        #    (mmap for .lcs, compact freeze for DB-backed).
        self.load(logical_name)

        # 6. Restore source info
        if source_info:
            self._source_info = source_info

        # 7. Final GC pass to clean up any stragglers.
        gc.collect()

        _log.info(
            "Post-index cleanup complete: reloaded '%s' from storage "
            "(%.1f MB in RAM).",
            logical_name,
            self._shard_manager.loaded_memory_mb if self._shard_manager else 0,
        )

    # factory methods
    @classmethod
    def from_dict(
        cls, 
        data: Dict[Any, str], 
        name: str = "default", 
        **kwargs
    ) -> "Lucis":
        """
        Creates a Lucis instance from a dictionary {id: text}.
        
        Preserves original keys as document IDs in search results.
        This is the recommended format when you have meaningful IDs
        (e.g., database PKs, document codes, email addresses).

        Args:
            data: Dictionary mapping document IDs to their text content.
            name: Identifier for persistence.
            **kwargs: Additional arguments passed to __init__ (storage_dir, engine, etc.)

        Returns:
            A ready-to-search Lucis instance.

        Example:
            lu = Lucis.from_dict({
                "doc_001": "Python es un lenguaje versátil",
                "doc_002": "El amor por la programación crece cada día"
            })
            results = lu.search("programación python")
        """
        # autoload=False to avoid loading stale data before indexing fresh data
        instance = cls(name=name, autoload=False, **kwargs)
        instance.index(data)
        return instance

    @classmethod
    def from_list(
        cls, 
        data: List[str], 
        name: str = "default", 
        **kwargs
    ) -> "Lucis":
        """
        Creates a Lucis instance from a list of text documents.
        
        Document IDs will be auto-generated as sequential integers (0, 1, 2...).
        This is the simplest way to get started when IDs don't matter.

        Args:
            data: List of text documents.
            name: Identifier for persistence.
            **kwargs: Additional arguments passed to __init__ (storage_dir, engine, etc.)

        Returns:
            A ready-to-search Lucis instance.

        Example:
            lu = Lucis.from_list([
                "Python es un lenguaje versátil",
                "El amor por la programación crece cada día"
            ])
            results = lu.search("programación")
        """
        instance = cls(name=name, autoload=False, **kwargs)
        instance.index(data)
        return instance

    @classmethod
    def from_sqlite_table(
        cls,
        table_name: str,
        db_path: str,
        text_column: Union[str, List[str]],
        id_column: Optional[str] = None,
        where_clause: Optional[str] = None,
        name: str = "default",
        **kwargs,
    ) -> "Lucis":
        """
        Create a Lucis instance by reading rows from an existing SQLite table.

        The index is automatically persisted back to the **same** database
        (``storage_type`` defaults to ``"sqlite"``).

        Args:
            table_name: Name of the source table.
            db_path: Path to the SQLite database file.
            text_column: Column name (or list of column names) containing
                the document text.  When a list is given (cross-field
                search), the columns are concatenated with spaces at the
                SQL level.
            id_column: Column to use as document ID (optional).
            where_clause: Optional SQL ``WHERE`` filter (without the ``WHERE`` keyword).
            name: Identifier for the persisted index.
            **kwargs: Extra arguments forwarded to ``Lucis.__init__``.

        Returns:
            A ready-to-search Lucis instance.

        Example::

            luc = Lucis.from_sqlite_table(
                table_name="articles",
                db_path="blog.db",
                text_column="content",
                id_column="article_id",
            )
            results = luc.search("python tutorial")
        """
        import sqlite3 as _sqlite3

        text_expr = _build_sql_text_expr(text_column)
        cols = f"{id_column}, {text_expr}" if id_column else text_expr
        query = f"SELECT {cols} FROM {table_name}"
        if where_clause:
            query += f" WHERE {where_clause}"

        conn = _sqlite3.connect(db_path)
        cursor = conn.execute(query)

        if id_column:
            data: Union[Dict[str, str], List[str]] = {
                str(row[0]): row[1] for row in cursor
            }
        else:
            data = [row[0] for row in cursor]

        conn.close()

        # Default to sqlite storage backed by the same db
        kwargs.setdefault("storage_type", "sqlite")
        kwargs.setdefault("db_path", db_path)
        instance = cls(name=name, autoload=False, **kwargs)
        instance._source_info = {
            "type": "table",
            "table_name": table_name,
            "text_column": text_column,
            "id_column": id_column,
            "date_column": None,
            "where_clause": where_clause,
            "query": None,
        }
        instance.index(data)
        return instance

    @classmethod
    def from_sqlite_query(
        cls,
        query: str,
        db_path: str,
        name: str = "default",
        **kwargs,
    ) -> "Lucis":
        """
        Create a Lucis instance from an arbitrary SQL ``SELECT`` query.

        * If the query returns **one** column → treated as a list of texts.
        * If it returns **two or more** columns → first column is the ID,
          second column is the text.

        Args:
            query: A ``SELECT`` statement to execute.
            db_path: Path to the SQLite database file.
            name: Identifier for the persisted index.
            **kwargs: Extra arguments forwarded to ``Lucis.__init__``.

        Returns:
            A ready-to-search Lucis instance.

        Example::

            luc = Lucis.from_sqlite_query(
                query=(
                    "SELECT p.id, p.title || ' ' || p.body "
                    "FROM posts p "
                    "WHERE p.published = 1"
                ),
                db_path="forum.db",
                name="published_posts",
            )
        """
        import sqlite3 as _sqlite3

        conn = _sqlite3.connect(db_path)
        cursor = conn.execute(query)

        first_row = cursor.fetchone()
        if first_row is None:
            conn.close()
            raise ValueError("The query returned no results.")

        # Re-execute to include the first row (simplest portable approach)
        cursor = conn.execute(query)

        if len(first_row) == 1:
            data: Union[Dict[str, str], List[str]] = [row[0] for row in cursor]
        else:
            data = {str(row[0]): row[1] for row in cursor}

        conn.close()

        kwargs.setdefault("storage_type", "sqlite")
        kwargs.setdefault("db_path", db_path)
        instance = cls(name=name, autoload=False, **kwargs)
        instance._source_info = {
            "type": "query",
            "table_name": None,
            "text_column": None,
            "id_column": None,
            "date_column": None,
            "where_clause": None,
            "query": query,
        }
        instance.index(data)
        return instance

    @classmethod
    def from_alchemy_table(
        cls,
        table_name: str,
        url: str,
        text_column: Union[str, List[str]],
        id_column: Optional[str] = None,
        date_column: Optional[str] = "auto",
        where_clause: Optional[str] = None,
        schema: Optional[str] = None,
        name: str = "default",
        shard_batch_size: int = 20_000,
        stream_ordered: bool = False,
        **kwargs,
    ) -> "Lucis":
        """
        Create a Lucis instance by reading rows from a table via SQLAlchemy.

        Works with any database supported by SQLAlchemy (MySQL, PostgreSQL,
        MariaDB, etc.).  The index is automatically persisted back to the
        **same** database.

        **Temporal Sharding** (automatic):
        If the table contains a ``created_at``, ``updated_at``, or
        ``timestamp`` column (or a custom ``date_column``), the index
        is automatically partitioned into monthly shards (YYYY_MM).
        Documents with ``NULL`` dates go to the global shard
        (``LUCIS_GLOBAL_SHARD = "9999_99"``).

        To disable sharding, pass ``date_column=None``.

        Args:
            table_name: Name of the source table.
            url: SQLAlchemy connection URL.
                Example: ``"mysql+pymysql://user:pass@localhost/mydb"``
            text_column: Column name (or list of column names) containing
                the document text.  When a list is given (**cross-field
                search**), the columns are concatenated with spaces at the
                SQL level into a single searchable document.
            id_column: Column to use as document ID (optional).
            date_column: Column used for temporal sharding.
                ``"auto"`` (default) auto-detects ``created_at``,
                ``updated_at``, or ``timestamp``.
                Pass a column name like ``"published_at"`` to override.
                ``None`` disables sharding.
            where_clause: Optional SQL ``WHERE`` filter (without the ``WHERE`` keyword).
            schema: Database schema (e.g. ``"public"`` for PostgreSQL).
            name: Identifier for the persisted index.
            shard_batch_size: Rows buffered per shard before flushing during streaming.
            stream_ordered: When ``True``, assumes rows arrive sorted
                chronologically by the date column.  Requires
                ``memory_limit_mb`` or ``max_loaded_shards`` to have any
                effect — when a memory budget is active, completed shards
                are persisted and evicted during the build, keeping peak
                RAM proportional to the working set instead of the full
                dataset.  **Only enable if you are certain the data is
                ordered; unsorted data with this flag will silently
                truncate shards.**  Default: ``False``.
            **kwargs: Extra arguments forwarded to ``Lucis.__init__``.

        Returns:
            A ready-to-search Lucis instance.

        Example::

            luc = Lucis.from_alchemy_table(
                table_name="articles",
                url="mysql+pymysql://root:secret@localhost/blog",
                text_column="content",
                id_column="article_id",
            )
            results = luc.search("python tutorial")

        Example — time-scoped search::

            luc = Lucis.from_alchemy_table(
                table_name="emails",
                url="mysql+pymysql://root:secret@localhost/mail",
                text_column="body",
                id_column="email_id",
                date_column="received_at",
                engine="lite",
            )
            # Search only last month's emails:
            results = luc.search("invoice", since="2026-01")

        Example — cross-field search::

            luc = Lucis.from_alchemy_table(
                table_name="articles",
                url="mysql+pymysql://root:secret@localhost/blog",
                text_column=["title", "content", "tags"],
                id_column="article_id",
            )
            results = luc.search("python tutorial")
        """
        AlchemyStorage = _get_alchemy_storage_class()
        storage = AlchemyStorage(url=url)

        # Resolve date column
        resolved_date_col = date_column
        if date_column == "auto":
            resolved_date_col = storage.detect_date_column(table_name, schema)

        kwargs.setdefault("storage_type", "alchemy")
        kwargs.setdefault("alchemy_url", url)
        # Pass the already-built storage so we don't create a second engine
        instance = cls(name=name, autoload=False, storage=storage, **kwargs)
        instance._source_info = {
            "type": "table",
            "table_name": table_name,
            "text_column": text_column,
            "id_column": id_column,
            "date_column": resolved_date_col,
            "where_clause": where_clause,
            "query": None,
        }

        if resolved_date_col:
            # Sharded mode: stream rows → build_shards_streaming (no fetchall)
            instance._init_shard_manager()

            # Pre-generate the physical name so the builder can persist
            # shards incrementally when memory management is active.
            persist_name = None
            if instance._shard_manager._is_managed:
                persist_name = instance.storage._generate_versioned_name(name)

            if hasattr(storage, "stream_table_with_dates"):
                row_iter = storage.stream_table_with_dates(
                    table_name, text_column, id_column,
                    resolved_date_col, where_clause, schema,
                )
                instance._shard_manager.build_shards_streaming(
                    row_iter,
                    batch_size=shard_batch_size,
                    persist_base_name=persist_name,
                    stream_ordered=stream_ordered,
                )
            else:
                # Fallback for non-Alchemy storage
                data, dates = storage.read_table_with_dates(
                    table_name, text_column, id_column,
                    resolved_date_col, where_clause, schema,
                )
                instance._shard_manager.build_shards(data, dates)
            instance._is_indexed = True

            if persist_name:
                # Persist remaining shards + save registry using the
                # same physical name generated earlier.
                instance._shard_manager.persist_all(persist_name)

                # Create parent metadata entry
                parent_state = {
                    "index": {},
                    "total_docs": instance._shard_manager.total_docs,
                    "doc_lengths": {},
                    "id_map": {},
                    "id_type": instance._shard_manager.id_type,
                    "engine_name": instance.engine.name,
                }
                instance.storage.save(parent_state, persist_name)
                instance.storage.set_alias(name, persist_name)
                if instance._source_info is not None:
                    instance.storage.save_source_info(persist_name, instance._source_info)

                # Final trim: evict anything still over budget
                instance._shard_manager._lazy_base_name = persist_name
                evicted = instance._shard_manager.trim_to_budget()
                if evicted:
                    import logging
                    logging.getLogger(__name__).info(
                        "Post-index trim: evicted %d shards to fit memory budget "
                        "(%.0f MB in RAM).",
                        evicted,
                        instance._shard_manager.loaded_memory_mb,
                    )

                # ── Post-index RAM cleanup ──
                # After building + persisting, the in-memory engines retain
                # build-time structures (raw dicts, tokenized lists, etc.)
                # that are much heavier than a clean load from storage.
                # Reload from the persisted state to match the lightweight
                # footprint of a cold start with an existing index.
                instance._post_index_cleanup(name)
            else:
                # No memory management — use normal save()
                instance.save()
        else:
            # Non-sharded mode: current behavior
            data = storage.read_table(
                table_name=table_name,
                text_column=text_column,
                id_column=id_column,
                where_clause=where_clause,
                schema=schema,
            )
            instance.index(data)

        return instance

    @classmethod
    def from_alchemy_query(
        cls,
        query: str,
        url: str,
        name: str = "default",
        **kwargs,
    ) -> "Lucis":
        """
        Create a Lucis instance from an arbitrary SQL query via SQLAlchemy.

        * If the query returns **one** column → treated as a list of texts.
        * If it returns **two or more** columns → first column is the ID,
          second column is the text.

        Args:
            query: A ``SELECT`` statement to execute.
            url: SQLAlchemy connection URL.
            name: Identifier for the persisted index.
            **kwargs: Extra arguments forwarded to ``Lucis.__init__``.

        Returns:
            A ready-to-search Lucis instance.

        Example::

            luc = Lucis.from_alchemy_query(
                query="SELECT id, title FROM posts WHERE published = 1",
                url="mysql+pymysql://root:secret@localhost/blog",
                name="published_posts",
            )
        """
        AlchemyStorage = _get_alchemy_storage_class()
        storage = AlchemyStorage(url=url)

        data = storage.read_query(query)

        kwargs.setdefault("storage_type", "alchemy")
        kwargs.setdefault("alchemy_url", url)
        instance = cls(name=name, autoload=False, storage=storage, **kwargs)
        instance._source_info = {
            "type": "query",
            "table_name": None,
            "text_column": None,
            "id_column": None,
            "date_column": None,
            "where_clause": None,
            "query": query,
        }
        instance.index(data)
        return instance

    # core methods
    def index(self, data: Union[List[str], Dict[Any, str]], persist: bool = True) -> None:
        """
        The "all-terrain" ingestion method.
        
        Detects whether data is a Dict or List and delegates to the engine.
        This is the single entry point for all data ingestion — the engine's
        _normalize_corpus handles the rest.

        Args:
            data: Either a Dict[id, text] or List[text] to index.
            persist: Whether to save the index to storage after building.
        """
        self.engine.build_index(data)
        self._is_indexed = True
        if persist:
            self.save()

    def search(
        self,
        query: Union[str, List[str]],
        top_k: int = 10,
        since: Optional[str] = None,
        until: Optional[str] = None,
    ) -> SearchResponse:
        """
        Searches the indexed corpus for documents matching the query.

        The engine returns raw tuples; Lucis wraps them in a SearchResponse
        with full context: query, tokens, timing, and structured results.

        When the index is sharded (temporal partitioning), ``since`` and
        ``until`` restrict the search to shards within the specified range.
        Without these parameters, **all** shards are searched.

        Args:
            query: A search string ("love python") or pre-tokenized list (["love", "python"]).
            top_k: Maximum number of results to return.
            since: Start of the temporal range (inclusive).  Accepts:
                - Shard keys: ``"2026_01"``
                - ISO dates: ``"2026-01-15"``
                - Year-month: ``"2026-01"``
                Ignored for non-sharded indices.
            until: End of the temporal range (inclusive).  Same formats.

        Returns:
            SearchResponse with ranked results and search metadata.

        Example:
            response = lu.search("programación python", top_k=5)
            print(response.total_results)        # 5
            print(response.results[0].doc_id)     # "doc_001"
            print(response.results[0].score)      # 0.3903
            print(response.search_time_ms)        # 2.31
            print(response.to_dict())             # JSON-ready dict

        Example — time-scoped::

            response = lu.search("invoice", since="2026-01", until="2026-02")
        """
        if not self._is_indexed:
            raise LucisEngineError(
                engine_name=self.engine.name,
                detail="No index built yet. Use .index(data), .from_dict(), or .from_list() first."
            )

        # Preserve the original query before tokenization
        original_query = query

        # Preprocess + tokenize to capture the tokens for the response
        if isinstance(query, str):
            processed = self.preprocessor(query)
            # Fallback: if preprocessor returned str instead of list[str], apply simple_tokenizer
            tokens = simple_tokenizer(processed) if isinstance(processed, str) else processed
        else:
            tokens = list(query)

        # Time the search (the core computation)
        start = time.perf_counter()

        if self._shard_manager:
            # ── Sharded search: query relevant shards and merge ──
            raw_results = self._shard_manager.search(
                tokens, top_k=top_k, since=since, until=until,
            )
            elapsed_ms = (time.perf_counter() - start) * 1000

            # raw_results: [(doc_id, score, shard_key), ...]
            results = [
                SearchResult(
                    doc_id=doc_id, score=round(score, 6),
                    rank=rank, shard_key=shard_key,
                )
                for rank, (doc_id, score, shard_key) in enumerate(raw_results, start=1)
            ]

            # Count shards actually queried
            since_key = normalize_to_shard_key(since)
            until_key = normalize_to_shard_key(until)
            shards_searched = sum(
                1 for k in self._shard_manager.shards
                if shard_key_in_range(k, since_key, until_key)
            )

            return SearchResponse(
                query=original_query,
                tokens=tokens,
                engine=self.engine.name,
                total_results=len(results),
                search_time_ms=round(elapsed_ms, 2),
                results=results,
                shards_searched=shards_searched,
                total_shards=len(self._shard_manager.shards),
            )
        else:
            # ── Single-engine search (non-sharded) ──
            raw_results = self.engine.search(tokens, top_k=top_k)
            elapsed_ms = (time.perf_counter() - start) * 1000

            results = [
                SearchResult(doc_id=doc_id, score=round(score, 6), rank=rank)
                for rank, (doc_id, score) in enumerate(raw_results, start=1)
            ]

            return SearchResponse(
                query=original_query,
                tokens=tokens,
                engine=self.engine.name,
                total_results=len(results),
                search_time_ms=round(elapsed_ms, 2),
                results=results,
            )

    # persistence methods
    def save(self, name: Optional[str] = None) -> None:
        """
        Persists the current index to storage.
        
        On database-backed storages (SQLite, Alchemy) this creates a
        versioned physical index (e.g. ``my_idx__v20260210_143022``)
        and points the logical alias to it.  On JSON storage the
        behaviour is unchanged (no versioning).

        When sharded, each shard is persisted independently and a
        shard registry is saved alongside the parent metadata.

        Args:
            name: Optional custom name. Falls back to self.name.
        """
        save_name = name or self.name
        physical_name = self.storage._generate_versioned_name(save_name)

        if self._shard_manager:
            # ── Sharded save ──
            # 1. Persist each shard engine
            self._shard_manager.persist_all(physical_name)

            # 2. Create parent metadata entry (empty index data, just metadata)
            parent_state = {
                "index": {},
                "total_docs": self._shard_manager.total_docs,
                "doc_lengths": {},
                "id_map": {},
                "id_type": self._shard_manager.id_type,
                "engine_name": self.engine.name,
            }
            self.storage.save(parent_state, physical_name)
        else:
            # Single-engine save
            self.engine.persist(physical_name)

        # Point the logical alias to the new physical index
        self.storage.set_alias(save_name, physical_name)

        # Persist source info so the worker can auto-generate data_fn
        if self._source_info is not None:
            self.storage.save_source_info(physical_name, self._source_info)

    def load(self, name: Optional[str] = None) -> None:
        """
        Loads a previously saved index from storage.

        If *name* is an alias, it is resolved to the physical index
        name transparently.  Automatically detects whether the index
        is sharded and loads all shards if so.

        Args:
            name: Optional custom name. Falls back to self.name.
        """
        load_name = name or self.name
        physical_name = self.storage.resolve_alias(load_name)

        # Check if this is a sharded index
        shard_keys = self.storage.load_shard_registry(physical_name)

        if shard_keys:
            # Sharded load 
            self._init_shard_manager()
            lazy = self._max_loaded_shards > 0 or self._memory_limit_mb is not None
            self._shard_manager.load_all(physical_name, shard_keys, lazy=lazy)
            self._is_indexed = True
        else:
            # Single-engine load 
            self.engine.load_engine(physical_name)
            self._is_indexed = True

        # Restore source info (if available) so create_worker() works
        source = self.storage.load_source_info(physical_name)
        if source is not None:
            self._source_info = source

    def preload_shards(
        self,
        since: Optional[str] = None,
        until: Optional[str] = None,
        n_recent: Optional[int] = None,
    ) -> List[str]:
        """Explicitly warm shards into memory without blocking searches.

        Only useful when ``max_loaded_shards > 0`` was passed to the
        constructor (lazy mode).  Call this before running a query against
        historical data so the shards are ready in RAM.

        Args:
            since: Load shards at or after this key / ISO date (e.g. ``"2025_01"``).
            until: Load shards at or before this key / ISO date.
            n_recent: Load only the *n_recent* most recent qualifying shards.
                If ``None``, loads all matching shards (subject to the
                LRU eviction limit).

        Returns:
            List of shard keys that were newly loaded into memory.

        Example::

            luc = Lucis(name="email_idx", ..., max_loaded_shards=6)
            # After load(), only 6 most recent shards are in RAM.
            # To also query 2024 data:
            luc.preload_shards(since="2024_01", until="2024_12")
        """
        if self._shard_manager is None:
            return []
        return self._shard_manager.preload_shards(since=since, until=until, n_recent=n_recent)

    # Shadow Rebuild 

    def reindex(
        self,
        data: Union[List[str], Dict[Any, str]],
        dates: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Rebuild the index with fresh data, creating a new version.

        The previous version remains in storage so you can ``rollback()``
        if needed.  The alias is swapped atomically to the new version.

        When the index is sharded and *dates* is provided, documents are
        re-routed to their correct temporal shards.

        Args:
            data: New corpus — ``Dict[id, text]`` or ``List[text]``.
            dates: Optional ``{doc_id: date_value}`` for shard routing.
                Required for sharded indices; ignored otherwise.

        Example::

            new_data = storage.read_table("articles", text_column="content", id_column="id")
            luc.reindex(new_data)
            # → alias now points to the new version
        """
        if self._shard_manager and dates is not None:
            self._shard_manager.shards.clear()
            self._shard_manager.build_shards(data, dates)
        else:
            self.engine.build_index(data)
        self._is_indexed = True
        self.save()
        # Reload from storage to shed build-time RAM overhead
        if self._shard_manager:
            self._post_index_cleanup(self.name)

    def reindex_streaming(
        self,
        row_iter,
        batch_size: int = 5_000,
    ) -> None:
        """Rebuild the sharded index from a **streaming** row iterator.

        This is the memory-efficient counterpart to :meth:`reindex`.
        Instead of materialising the entire corpus in RAM (via
        ``fetchall``), rows are consumed in *batch_size* chunks and
        routed directly to their temporal shards.

        Peak RAM during rebuild ≈ steady-state index RAM + one batch
        (a few MB), instead of steady-state + full raw corpus (~1 GB
        extra for a 2 M-row email dataset).

        Args:
            row_iter: Any iterable that yields ``(doc_id_str, text, date_val)``
                triples.  Typical source:
                ``storage.stream_table_with_dates(...)``.
            batch_size: Per-shard buffer size.  Default 5 000 rows.

        Raises:
            LucisEngineError: If the index is not sharded (no
                ``_shard_manager``).  Use :meth:`reindex` for
                non-sharded indices.

        Example::

            row_iter = storage.stream_table_with_dates(
                "emails", "body", id_column="id", date_column="sent_at"
            )
            luc.reindex_streaming(row_iter)
        """
        if self._shard_manager is None:
            raise LucisEngineError(
                engine_name=self.engine.name,
                detail=(
                    "reindex_streaming() requires a sharded index. "
                    "Use reindex() for non-sharded indices."
                ),
            )
        self._shard_manager.build_shards_streaming(row_iter, batch_size=batch_size)
        self._is_indexed = True
        self.save()
        # Reload from storage to shed build-time RAM overhead
        self._post_index_cleanup(self.name)

    def add_documents(
        self,
        new_docs: Union[List[str], Dict[Any, str]],
        dates: Optional[Dict[str, Any]] = None,
        persist: bool = True,
    ) -> None:
        """
        Incrementally add new documents to the current index.

        When the index is sharded, new documents are routed to the
        correct shard based on *dates*.

        Args:
            new_docs: New documents — ``Dict[id, text]`` or ``List[text]``.
            dates: Optional ``{doc_id: date_value}`` for shard routing.
            persist: Whether to save the updated index to storage.

        Raises:
            LucisEngineError: If the engine does not support incremental
                indexing (e.g., ``CoreEngine``) and index is not sharded.

        Example::

            luc.add_documents({"new_doc": "some text"})
            luc.add_documents(["another document"])
        """
        if self._shard_manager and dates is not None:
            self._shard_manager.add_documents(new_docs, dates)
        elif hasattr(self.engine, "add_documents"):
            self.engine.add_documents(new_docs)
        else:
            raise LucisEngineError(
                engine_name=self.engine.name,
                detail=(
                    f"'{self.engine.name}' does not support incremental indexing. "
                    "Use reindex() for a full rebuild, or switch to engine='lite'."
                ),
            )

        self._is_indexed = True
        if persist:
            self.save()

    def rollback(self) -> None:
        """
        Roll back the alias to the previous index version.

        Looks at all physical versions for ``self.name``, finds the one
        right before the current target, swaps the alias, and reloads
        the engine.

        Raises:
            LucisEngineError: If there is no alias or no previous version.

        Example::

            luc.rollback()
            # → alias points to the version before the current one
        """
        current_target = self.storage.get_alias(self.name)
        if current_target is None:
            raise LucisEngineError(
                engine_name=self.engine.name,
                detail=f"No alias found for '{self.name}'. Cannot rollback."
            )

        versions = self.storage.list_versions(self.name)
        if len(versions) < 2:
            raise LucisEngineError(
                engine_name=self.engine.name,
                detail=f"No previous version to rollback to for '{self.name}'."
            )

        try:
            current_idx = versions.index(current_target)
        except ValueError:
            raise LucisEngineError(
                engine_name=self.engine.name,
                detail=(
                    f"Current target '{current_target}' not found in "
                    f"versions list. The physical index may have been deleted."
                )
            )

        if current_idx == 0:
            raise LucisEngineError(
                engine_name=self.engine.name,
                detail="Already at the oldest version. Cannot rollback further."
            )

        previous = versions[current_idx - 1]
        self.storage.set_alias(self.name, previous)
        self.load()

    def list_versions(self) -> List[str]:
        """
        List all physical versions of this index.

        Returns a list of physical index names sorted oldest → newest.

        Returns:
            List of versioned physical names.

        Example::

            luc.list_versions()
            # ['articles__v20260210_143022', 'articles__v20260210_150545']
        """
        return self.storage.list_versions(self.name)

    def purge_old_versions(self, keep: int = 2) -> int:
        """
        Delete old index versions, keeping the *keep* most recent ones.

        The version currently pointed to by the alias is **always** kept,
        even if it falls outside the *keep* window.

        Args:
            keep: Number of most-recent versions to retain (default 2).

        Returns:
            Number of versions deleted.

        Example::

            deleted = luc.purge_old_versions(keep=2)
            print(f"Cleaned up {deleted} old versions")
        """
        versions = self.storage.list_versions(self.name)
        if len(versions) <= keep:
            return 0

        # Current alias target must be protected
        current_target = self.storage.get_alias(self.name)

        # Keep the N most recent + the current target
        to_keep = set(versions[-keep:])
        if current_target:
            to_keep.add(current_target)

        to_delete = [v for v in versions if v not in to_keep]
        for v in to_delete:
            self.storage.delete(v)

        return len(to_delete)

    # Phase 3: Background Rebuild

    def reindex_async(
        self,
        data: Union[List[str], Dict[Any, str]],
        on_complete: Optional[Callable[[str], None]] = None,
        on_error: Optional[Callable[[Exception], None]] = None,
        auto_swap: bool = True,
    ) -> None:
        """
        Rebuild the index in a background thread.

        While the rebuild is running, ``search()`` continues to use the
        current (active) engine with **zero downtime**.  When the new
        index is ready it is persisted, the alias is swapped, and
        (optionally) the live engine is replaced atomically.

        Args:
            data: New corpus — ``Dict[id, text]`` or ``List[text]``.
            on_complete: Callback ``fn(physical_name)`` invoked when the
                rebuild finishes successfully.
            on_error: Callback ``fn(exception)`` invoked if the rebuild fails.
            auto_swap: If ``True`` (default), the live engine is
                swapped to the new version automatically.  If ``False``,
                the alias is updated but you must call ``load()`` yourself
                to pick up the new version.

        Raises:
            LucisEngineError: If a rebuild is already in progress.

        Example::

            luc.reindex_async(new_data)

            while luc.is_rebuilding():
                results = luc.search("query")   # ← uses active index
                time.sleep(0.5)

            luc.wait_for_reindex()               # ← ensures completion
            results = luc.search("query")        # ← uses new index
        """
        if self.is_rebuilding():
            raise LucisEngineError(
                engine_name=self.engine.name,
                detail="A background rebuild is already in progress. "
                       "Call wait_for_reindex() before starting another.",
            )

        self._rebuild_error = None

        # Capture references for the worker closure
        engine_class = type(self.engine)
        storage = self.storage
        index_name = self.name
        preprocessor = self.preprocessor

        def _worker() -> None:
            try:
                # 1. Build in an isolated engine (no impact on live searches)
                shadow_engine = engine_class(storage=storage, preprocessor=preprocessor)
                shadow_engine.build_index(data)

                # 2. Persist with a new versioned name + swap alias
                physical_name = storage._generate_versioned_name(index_name)
                shadow_engine.persist(physical_name)
                storage.set_alias(index_name, physical_name)

                # 3. Hot-swap the live engine (GIL makes reference swap atomic)
                if auto_swap:
                    self.engine = shadow_engine
                    self._is_indexed = True

                if on_complete:
                    on_complete(physical_name)

            except Exception as exc:
                self._rebuild_error = exc
                if on_error:
                    on_error(exc)

        self._rebuild_thread = threading.Thread(
            target=_worker,
            name=f"lucis-reindex-{index_name}",
            daemon=True,
        )
        self._rebuild_thread.start()

    def is_rebuilding(self) -> bool:
        """Return ``True`` if a background rebuild is currently in progress.

        Returns:
            ``True`` while the rebuild thread started by
            :meth:`reindex_async` is alive.

        Example::

            if luc.is_rebuilding():
                print("Rebuild in progress…")
        """
        return (
            self._rebuild_thread is not None
            and self._rebuild_thread.is_alive()
        )

    def wait_for_reindex(self, timeout: Optional[float] = None) -> None:
        """
        Block until the background rebuild finishes.

        If the rebuild raised an exception, it is re-raised here so the
        caller can handle it.

        Args:
            timeout: Maximum seconds to wait.  ``None`` means wait
                indefinitely.

        Raises:
            LucisEngineError: If no rebuild has been started.
            Exception: Re-raises the original error from the worker thread.

        Example::

            luc.reindex_async(new_data)
            luc.wait_for_reindex(timeout=30)
            print("Rebuild done!")
        """
        if self._rebuild_thread is None:
            raise LucisEngineError(
                engine_name=self.engine.name,
                detail="No background rebuild to wait for.",
            )

        self._rebuild_thread.join(timeout=timeout)

        if self._rebuild_error is not None:
            raise self._rebuild_error

    # Phase 4: Worker / Automation 

    def _auto_data_fn(self) -> Callable:
        """Auto-generate a ``data_fn`` callable from stored ``_source_info``.

        For sharded indices (``date_column`` present), the returned
        callable produces ``(data, dates)`` tuples.  For non-sharded
        indices, it returns ``Dict`` or ``List`` as before.

        Returns:
            A no-argument callable that fetches the full corpus from
            the configured data source.

        Raises:
            LucisEngineError: If ``_source_info`` is missing or has an
                unknown ``type`` field.
        """
        info = self._source_info
        storage = self.storage
        date_col = info.get("date_column")

        if info["type"] == "table":
            table_name = info["table_name"]
            text_col = info["text_column"]
            id_col = info["id_column"]
            where = info.get("where_clause")

            # Sharded: return (data, dates)
            if date_col and hasattr(storage, "read_table_with_dates"):
                def fetch_with_dates():
                    return storage.read_table_with_dates(
                        table_name, text_col, id_col, date_col, where,
                    )
                return fetch_with_dates

            # Non-sharded: Alchemy
            if hasattr(storage, "read_table"):
                def fetch():
                    return storage.read_table(
                        table_name, text_col, id_col, where
                    )
                return fetch

            # Non-sharded: SQLite
            text_expr = _build_sql_text_expr(text_col)
            cols = f"{id_col}, {text_expr}" if id_col else text_expr
            sql = f"SELECT {cols} FROM {table_name}"
            if where:
                sql += f" WHERE {where}"
            db_path = getattr(storage, "db_path", None)
            def fetch_sqlite():
                import sqlite3
                conn = sqlite3.connect(db_path)
                cursor = conn.execute(sql)
                if id_col:
                    data = {str(row[0]): row[1] for row in cursor}
                else:
                    data = [row[0] for row in cursor]
                conn.close()
                return data
            return fetch_sqlite

        elif info["type"] == "query":
            query_str = info["query"]

            if hasattr(storage, "read_query"):
                def fetch_q():
                    return storage.read_query(query_str)
                return fetch_q
            else:
                db_path = getattr(storage, "db_path", None)
                def fetch_q_sqlite():
                    import sqlite3
                    conn = sqlite3.connect(db_path)
                    cursor = conn.execute(query_str)
                    first = cursor.fetchone()
                    if first is None:
                        conn.close()
                        return []
                    cursor = conn.execute(query_str)
                    if len(first) == 1:
                        data = [row[0] for row in cursor]
                    else:
                        data = {str(row[0]): row[1] for row in cursor}
                    conn.close()
                    return data
                return fetch_q_sqlite

        raise LucisEngineError(
            engine_name=self.engine.name,
            detail=f"Cannot auto-generate data_fn: unknown source type '{info.get('type')}'",
        )

    def _auto_streaming_fn(self) -> Optional[Callable]:
        """Return a no-arg callable that produces a streaming row iterator.

        Available when: source is a ``"table"``, the storage is
        :class:`~lucis.storage.AlchemyStorage` (has
        ``stream_table_with_dates``), **and** a ``date_column`` is
        configured (sharded mode).

        Returns ``None`` when any of these conditions is not met —
        callers should fall back to :meth:`_auto_data_fn`.

        The returned callable has the signature::

            def streaming_fn() -> Iterator[(doc_id, text, date_val)]

        Each call to ``streaming_fn()`` opens a fresh server-side cursor
        on the database.
        """
        info = self._source_info
        if info is None or info.get("type") != "table":
            return None
        if not info.get("date_column"):
            return None  # Streaming rebuild only meaningful for sharded mode
        storage = self.storage
        if not hasattr(storage, "stream_table_with_dates"):
            return None  # Non-Alchemy storage — no streaming support

        table_name = info["table_name"]
        text_col = info["text_column"]
        id_col = info["id_column"]
        date_col = info["date_column"]
        where = info.get("where_clause")
        schema = info.get("schema")

        def streaming_fn():
            return storage.stream_table_with_dates(
                table_name, text_col, id_col, date_col, where, schema,
            )
        return streaming_fn

    def _auto_delta_fn(
        self,
    ) -> Optional[Callable[[], Union[List[str], Dict[Any, str]]]]:
        """Auto-generate a delta_fn that returns only NEW documents since last call.

        Strategy selection:

        1. **Table + id_column** (optimal): Uses ``WHERE id > last_max_id``
           to fetch only new rows at the SQL level.
        2. **Query or table without id_column** (universal): Fetches all
           data via ``data_fn`` and diffs against already-indexed IDs
           to extract only the new documents.

        Returns ``None`` only when ``_source_info`` is missing entirely
        (no auto-generation possible).
        """
        info = self._source_info
        if info is None:
            return None

        storage = self.storage

        # Optimized path: table + id_column → SQL-level delta
        if info["type"] == "table" and info.get("id_column"):
            return self._auto_delta_fn_by_id(info, storage)

        # Universal path: fetch all → diff against known IDs
        return self._auto_delta_fn_universal()

    def _auto_delta_fn_by_id(
        self,
        info: Dict[str, Optional[str]],
        storage: Any,
    ) -> Callable[[], Dict[str, str]]:
        """Optimized delta: ``WHERE id > last_max_id`` at the SQL level.

        When a ``date_column`` is present, the returned callable
        produces ``(data, dates)`` tuples for shard routing.
        """
        id_col = info["id_column"]
        table_name = info["table_name"]
        text_col = info["text_column"]
        date_col = info.get("date_column")
        where = info.get("where_clause")

        last_max = [0]

        if hasattr(storage, "_engine"):
            # AlchemyStorage
            from sqlalchemy import text as _sa_text

            with storage._engine.connect() as conn:
                result = conn.execute(
                    _sa_text(f"SELECT MAX({id_col}) FROM {table_name}")
                ).scalar()
                if result is not None:
                    last_max[0] = result

            # Build text expression for multi-column support
            text_expr = storage._sql_concat_columns(text_col)

            if date_col:
                def delta_alchemy_sharded():
                    from sqlalchemy import text as _sa_t
                    sql = (
                        f"SELECT {id_col}, {text_expr}, {date_col} "
                        f"FROM {table_name} WHERE {id_col} > :last_id"
                    )
                    if where:
                        sql += f" AND ({where})"
                    sql += f" ORDER BY {id_col}"
                    with storage._engine.connect() as conn:
                        rows = conn.execute(
                            _sa_t(sql), {"last_id": last_max[0]}
                        ).fetchall()
                    if not rows:
                        return {}, {}
                    data = {str(row[0]): row[1] for row in rows}
                    dates = {str(row[0]): row[2] for row in rows}
                    last_max[0] = max(row[0] for row in rows)
                    return data, dates
                return delta_alchemy_sharded
            else:
                def delta_alchemy():
                    from sqlalchemy import text as _sa_t
                    sql = f"SELECT {id_col}, {text_expr} FROM {table_name} WHERE {id_col} > :last_id"
                    if where:
                        sql += f" AND ({where})"
                    sql += f" ORDER BY {id_col}"
                    with storage._engine.connect() as conn:
                        rows = conn.execute(
                            _sa_t(sql), {"last_id": last_max[0]}
                        ).fetchall()
                    if not rows:
                        return {}
                    data = {str(row[0]): row[1] for row in rows}
                    last_max[0] = max(row[0] for row in rows)
                    return data
                return delta_alchemy

        else:
            # SQLiteStorage
            import sqlite3 as _sqlite3

            db_path = getattr(storage, "db_path", None)
            conn = _sqlite3.connect(db_path)
            result = conn.execute(
                f"SELECT MAX({id_col}) FROM {table_name}"
            ).fetchone()[0]
            conn.close()
            if result is not None:
                last_max[0] = result

            # Build text expression for multi-column support
            text_expr = _build_sql_text_expr(text_col)

            if date_col:
                def delta_sqlite_sharded():
                    import sqlite3
                    sql = (
                        f"SELECT {id_col}, {text_expr}, {date_col} "
                        f"FROM {table_name} WHERE {id_col} > ?"
                    )
                    if where:
                        sql += f" AND ({where})"
                    sql += f" ORDER BY {id_col}"
                    conn = sqlite3.connect(db_path)
                    rows = conn.execute(sql, (last_max[0],)).fetchall()
                    conn.close()
                    if not rows:
                        return {}, {}
                    data = {str(row[0]): row[1] for row in rows}
                    dates = {str(row[0]): row[2] for row in rows}
                    last_max[0] = max(row[0] for row in rows)
                    return data, dates
                return delta_sqlite_sharded
            else:
                def delta_sqlite():
                    import sqlite3
                    sql = f"SELECT {id_col}, {text_expr} FROM {table_name} WHERE {id_col} > ?"
                    if where:
                        sql += f" AND ({where})"
                    sql += f" ORDER BY {id_col}"
                    conn = sqlite3.connect(db_path)
                    rows = conn.execute(sql, (last_max[0],)).fetchall()
                    conn.close()
                    if not rows:
                        return {}
                    data = {str(row[0]): row[1] for row in rows}
                    last_max[0] = max(row[0] for row in rows)
                    return data
                return delta_sqlite

    def _auto_delta_fn_universal(
        self,
    ) -> Callable:
        """Universal delta: fetch all data → diff against indexed IDs.

        Less efficient than the SQL-level approach (still reads the full
        table/query), but works with **any** source type and correctly
        produces only the new documents for ``add_documents()``.

        When the data_fn returns ``(data, dates)`` tuples (sharded mode),
        the delta also returns ``(new_data, new_dates)``.
        """
        data_fn = self._auto_data_fn()
        shard_manager = self._shard_manager
        engine = self.engine

        def delta_universal():
            result = data_fn()

            # Detect sharded mode: data_fn returns (data, dates)
            if isinstance(result, tuple) and len(result) == 2:
                all_data, all_dates = result
                known_ids = set(str(v) for v in shard_manager.id_map.values())
                new_data = {
                    k: v for k, v in all_data.items()
                    if str(k) not in known_ids
                }
                new_dates = {k: v for k, v in all_dates.items() if k in new_data}
                return new_data, new_dates

            # Non-sharded mode
            all_data = result
            if isinstance(all_data, dict):
                known_ids = set(str(v) for v in engine.id_map.values())
                new_data = {
                    k: v for k, v in all_data.items()
                    if str(k) not in known_ids
                }
                return new_data
            else:
                current_count = engine.total_docs
                if len(all_data) <= current_count:
                    return []
                return all_data[current_count:]

        return delta_universal

    def _auto_change_detector(self) -> Optional[Callable[[], bool]]:
        """Auto-generate a count-based change detector from source metadata.

        Works for both ``"table"`` sources (uses ``count_rows``) and
        ``"query"`` sources (wraps the original query in
        ``SELECT COUNT(*) FROM (…)``).
        """
        info = self._source_info
        if info is None:
            return None

        storage = self.storage
        if self._shard_manager is not None:
            last_count = [self._shard_manager.total_docs]
        else:
            last_count = [self.engine.total_docs if self._is_indexed else 0]

        if info["type"] == "table":
            table_name = info["table_name"]

            def detect_table():
                current = storage.count_rows(table_name)
                if current != last_count[0]:
                    last_count[0] = current
                    return True
                return False

            return detect_table

        elif info["type"] == "query":
            query_str = info["query"]

            if hasattr(storage, "_engine"):
                # AlchemyStorage — use sa_text
                from sqlalchemy import text as _sa_text

                def detect_query_alchemy():
                    with storage._engine.connect() as conn:
                        current = conn.execute(
                            _sa_text(
                                f"SELECT COUNT(*) FROM ({query_str}) AS _lucis_subq"
                            )
                        ).scalar()
                    if current != last_count[0]:
                        last_count[0] = current
                        return True
                    return False

                return detect_query_alchemy

            else:
                # SQLiteStorage — direct cursor
                db_path = getattr(storage, "db_path", None)

                def detect_query_sqlite():
                    import sqlite3
                    conn = sqlite3.connect(db_path)
                    current = conn.execute(
                        f"SELECT COUNT(*) FROM ({query_str})"
                    ).fetchone()[0]
                    conn.close()
                    if current != last_count[0]:
                        last_count[0] = current
                        return True
                    return False

                return detect_query_sqlite

        return None

    def create_worker(
        self,
        data_fn: Optional[Callable[[], Union[List[str], Dict[Any, str]]]] = None,
        interval: float = 60,
        change_detector: Optional[Callable[[], bool]] = None,
        incremental: Optional[bool] = None,
        delta_fn: Optional[Callable[[], Union[List[str], Dict[Any, str]]]] = None,
        auto_purge: bool = True,
        keep_versions: int = 2,
        on_rebuild: Optional[Callable[[str], None]] = None,
        on_error: Optional[Callable[[Exception], None]] = None,
        on_cycle: Optional[Callable[[int, bool], None]] = None,
        streaming: bool = True,
    ) -> "IndexWorker":
        """
        Create an ``IndexWorker`` bound to this Lucis instance.

        The worker runs a daemon loop that periodically fetches fresh
        data, rebuilds the index, swaps the alias, and (optionally)
        purges old versions — all with **zero downtime** for searches.

        If the index was created from a database table/query (via
        ``from_alchemy_table``, ``from_sqlite_table``, etc.), both
        ``data_fn`` and ``change_detector`` are **auto-generated**
        when not provided — the worker just works out of the box.

        **Incremental mode** (LiteEngine only):
        When ``incremental=True`` (or auto-detected), the worker uses
        ``delta_fn`` instead of ``data_fn`` to fetch only new rows and
        calls ``add_documents()`` instead of ``reindex()``.  This is
        significantly faster for append-heavy workloads.

        If ``incremental`` is not specified:
        - Auto-enabled when engine is ``LiteEngine`` and source is
          a table with an ``id_column``.
        - Falls back to full rebuild mode otherwise.

        Args:
            data_fn: Callable that returns fresh data each cycle.
                If ``None``, auto-generated from source metadata.
            interval: Seconds between cycles (default 60).
            change_detector: Optional ``() → bool``.  When provided,
                the rebuild only runs if this returns ``True``.
                If ``None`` and source is a table, auto-generated
                using ``COUNT(*)`` comparison.
            incremental: Enable incremental mode.  ``None`` = auto-detect.
            delta_fn: Callable returning only *new* documents since last
                call.  Auto-generated for table sources with id_column.
            auto_purge: Automatically clean old versions (default True).
            keep_versions: Versions to retain when purging (default 2).
            on_rebuild: Callback ``fn(physical_name)`` on success.
            on_error: Callback ``fn(exception)`` on failure.
            on_cycle: Callback ``fn(cycle_number, skipped)`` every cycle.
            streaming: Enable streaming full-rebuild mode (default ``True``).
                When ``True`` and the source is a sharded Alchemy table, the
                worker calls :meth:`reindex_streaming` instead of loading the
                entire corpus into RAM via ``data_fn``.  This keeps peak RAM
                at ≈ steady-state index RAM rather than doubling it during each
                rebuild cycle.  Set to ``False`` to force the classic
                ``fetchall`` path.

        Returns:
            An ``IndexWorker`` instance (not yet started).
            Call ``.start()`` to begin the loop.

        Example — zero config (auto data_fn + auto incremental)::

            luc = Lucis.from_alchemy_table("articles", url=URL,
                                           text_column="content",
                                           id_column="article_id",
                                           name="articles_idx",
                                           engine="lite")
            worker = luc.create_worker(interval=60)
            worker.start()

        Example — explicit incremental with custom delta_fn::

            worker = luc.create_worker(
                incremental=True,
                delta_fn=my_delta_fetcher,
                interval=30,
            )
            worker.start()

        Example — full rebuild (default for CoreEngine)::

            worker = luc.create_worker(data_fn=my_fetch, interval=30)
            worker.start()
        """
        # Auto-detect incremental mode
        # LiteEngine → always incremental (uses add_documents)
        # CoreEngine  → always full rebuild (uses reindex)
        if incremental is None:
            incremental = hasattr(self.engine, "add_documents")

        # Auto-generate delta_fn for incremental mode 
        if incremental and delta_fn is None:
            delta_fn = self._auto_delta_fn()
            if delta_fn is None:
                # No source info at all — cannot auto-generate
                import logging
                logging.getLogger("lucis.worker").warning(
                    "Cannot auto-generate delta_fn for incremental mode; "
                    "falling back to full rebuild."
                )
                incremental = False

        # Auto-generate data_fn (always needed as fallback)
        if data_fn is None:
            if self._source_info is None:
                if not incremental:
                    raise LucisEngineError(
                        engine_name=self.engine.name,
                        detail=(
                            "Cannot auto-generate data_fn: no source info available. "
                            "Either create the index with from_alchemy_table / "
                            "from_sqlite_table, or provide data_fn explicitly."
                        ),
                    )
                # Incremental-only: data_fn not strictly needed,
                # but we still create a no-op for the worker signature.
                data_fn = lambda: {}
            else:
                data_fn = self._auto_data_fn()

        # Auto-generate change_detector if not provided
        if change_detector is None and self._source_info is not None:
            change_detector = self._auto_change_detector()

        # Auto-generate streaming_fn for sharded+alchemy full-rebuild mode.
        # When available, the worker streams rows from the DB without fetchall,
        # keeping peak RAM ≈ steady-state index RAM instead of doubling it.
        streaming_fn: Optional[Callable] = None
        if streaming and not incremental:
            streaming_fn = self._auto_streaming_fn()

        from .core.worker import IndexWorker
        return IndexWorker(
            lucis=self,
            data_fn=data_fn,
            interval=interval,
            change_detector=change_detector,
            incremental=incremental,
            delta_fn=delta_fn,
            auto_purge=auto_purge,
            keep_versions=keep_versions,
            on_rebuild=on_rebuild,
            on_error=on_error,
            on_cycle=on_cycle,
            streaming_fn=streaming_fn,
        )

    # Health monitoring

    def health_check(
        self,
        worker: Optional["IndexWorker"] = None,
        benchmark_query: Optional[str] = None,
    ) -> "HealthReport":
        """
        Generate a full health report: RAM usage, shard sizes, worker
        status, and optional search benchmark.

        Args:
            worker: An ``IndexWorker`` to include in the report (optional).
            benchmark_query: If provided, runs a timed search and includes
                the latency in the report.

        Returns:
            A :class:`HealthReport` with all diagnostics.

        Example::

            report = luc.health_check(worker=worker, benchmark_query="test")
            print(report)          # pretty table
            print(report.to_dict())  # JSON-ready dict
        """
        return _health_check(self, worker=worker, benchmark_query=benchmark_query)

    def health_monitor(
        self,
        worker: Optional["IndexWorker"] = None,
        interval: float = 30,
        benchmark_query: Optional[str] = None,
        on_report: Optional[Any] = None,
        ram_warning_mb: float = 512,
    ) -> "HealthMonitor":
        """
        Create a continuous health monitor that collects periodic snapshots.

        The monitor runs in a daemon thread and stores a history of
        :class:`HealthReport` objects for trend analysis.

        Args:
            worker: An ``IndexWorker`` to include in reports.
            interval: Seconds between snapshots (default 30).
            benchmark_query: If provided, benchmarks search each cycle.
            on_report: Optional callback ``fn(HealthReport)`` per cycle.
            ram_warning_mb: Log a warning if index RAM exceeds this
                threshold (default 512 MB).

        Returns:
            A :class:`HealthMonitor` instance (not yet started).
            Call ``.start()`` to begin monitoring.

        Example::

            monitor = luc.health_monitor(worker=worker, interval=30)
            monitor.start()
            # ... app runs ...
            monitor.stop()
            monitor.print_summary()
        """
        return HealthMonitor(
            lucis=self,
            worker=worker,
            interval=interval,
            benchmark_query=benchmark_query,
            on_report=on_report,
            ram_warning_mb=ram_warning_mb,
        )

    # ------------------------------------------------------------------ #
    #  Lifecycle                                                          #
    # ------------------------------------------------------------------ #

    def close(self) -> None:
        """Release all mmap handles held by loaded shard engines.

        Call this before deleting ``.lcs`` files on Windows, or when
        the ``Lucis`` instance is no longer needed and you want to
        free OS-level file handles immediately.
        """
        if self._shard_manager is not None:
            self._shard_manager.close()
        else:
            close_fn = getattr(self.engine, "close_mmap", None)
            if close_fn is not None:
                close_fn()

    def generate_lcs(self) -> int:
        """Write ``.lcs`` binary cache files for all currently-loaded shards.

        This is the one-time step needed to enable mmap-based loading.
        Call it once after a normal index load, then on subsequent runs
        Lucis will automatically use the ``.lcs`` files (near-zero heap RAM).

        The index in MySQL/SQLite is **not** modified — ``.lcs`` files
        are only a read cache stored in ``binary_dir`` (default:
        ``{storage_dir}/lcs/``).

        Returns:
            Number of ``.lcs`` files written.

        Raises:
            RuntimeError: If the instance is not sharded, not indexed,
                or ``binary_dir`` is ``None``.

        Example::

            luc = Lucis(name="email_idx", ..., binary_dir="auto")
            n = luc.generate_lcs()
            print(f"Generated {n} .lcs files")
            luc.close()
            # Next load will use mmap automatically
        """
        if self._shard_manager is None:
            raise RuntimeError(
                "generate_lcs() is only supported for sharded indexes. "
                "Non-sharded indexes don't benefit from .lcs files."
            )
        if not self._is_indexed:
            raise RuntimeError(
                "generate_lcs() requires a loaded index. "
                "Load or build the index before calling generate_lcs()."
            )
        if self._shard_manager._binary_dir is None:
            raise RuntimeError(
                "generate_lcs() requires binary_dir to be set. "
                "Pass binary_dir='auto' when creating Lucis."
            )
        base_name = self._shard_manager._lazy_base_name or self.name
        return self._shard_manager.write_lcs_files(base_name)

    # info and debugging
    def __repr__(self) -> str:
        """Return an informative string representation of the Lucis instance."""
        status = "indexed" if self._is_indexed else "empty"

        if self._shard_manager:
            docs = self._shard_manager.total_docs
            n_shards = len(self._shard_manager.shards)
            return (
                f"Lucis(name='{self.name}', engine='{self.engine.name}', "
                f"docs={docs}, shards={n_shards}, status='{status}')"
            )
        else:
            docs = self.engine.total_docs if self._is_indexed else 0
            id_t = self.engine.id_type if self._is_indexed else "N/A"
            return (
                f"Lucis(name='{self.name}', engine='{self.engine.name}', "
                f"docs={docs}, idx_type='{id_t}', status='{status}')"
            )