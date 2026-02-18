import time
import threading
from typing import Any, Callable, Dict, List, Optional, Union
from .engines.core import CoreEngine
from .engines.base import DocId
from .storage.base import BaseStorage
from .storage.json_storage import JSONStorage
from .storage.sqlite_storage import SQLiteStorage
from .exceptions import LucisEngineError
from .models.search import SearchResult, SearchResponse
from .utils.nlp import word_tokenizer
from .worker import IndexWorker

# Lazy import flag — AlchemyStorage requires sqlalchemy (optional dep)
_AlchemyStorage = None

def _get_alchemy_storage_class():
    """Lazy-load AlchemyStorage to avoid hard dependency on sqlalchemy."""
    global _AlchemyStorage
    if _AlchemyStorage is None:
        from .storage.alchemy_storage import AlchemyStorage
        _AlchemyStorage = AlchemyStorage
    return _AlchemyStorage

# Engine registry - maps friendly names to engine classes
# As new engines are added, register them here
_ENGINE_REGISTRY = {
    "core": CoreEngine,
    # Future: "plus": PlusEngine, "numpy": NumpyEngine, etc.
}


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
        tokenizer: Optional[Callable[[str], List[str]]] = None,
        autoload: bool = True,
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
            tokenizer: Custom tokenizer function ``(str) → list[str]``. Defaults to word_tokenizer.
                Any function matching that signature works. The same tokenizer is used for
                both indexing and searching to ensure consistent vector spaces.
                Example: ``char_ngram_tokenizer(3)`` for character n-gram based search.
            autoload: If True and an index with this name exists on disk, load it automatically.
        """
        self.name = name
        self._is_indexed = False
        self._source_info: Optional[Dict[str, Optional[str]]] = None
        self.tokenizer: Callable[[str], List[str]] = tokenizer or word_tokenizer

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
        self.engine = engine_class(storage=self.storage, tokenizer=self.tokenizer)

        # 3. Smart persistence: if the index already exists on disk, load it
        # This enables the "pick up where you left off" workflow:
        #   lu = Lucis(name="my_index")  →  ready to search immediately
        # The name may be an alias — exists() resolves it transparently.
        if autoload and self.storage.exists(name):
            self.load()

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
        text_column: str,
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
            text_column: Column that contains the document text.
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

        cols = f"{id_column}, {text_column}" if id_column else text_column
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
        text_column: str,
        id_column: Optional[str] = None,
        where_clause: Optional[str] = None,
        schema: Optional[str] = None,
        name: str = "default",
        **kwargs,
    ) -> "Lucis":
        """
        Create a Lucis instance by reading rows from a table via SQLAlchemy.

        Works with any database supported by SQLAlchemy (MySQL, PostgreSQL,
        MariaDB, etc.).  The index is automatically persisted back to the
        **same** database.

        Args:
            table_name: Name of the source table.
            url: SQLAlchemy connection URL.
                Example: ``"mysql+pymysql://user:pass@localhost/mydb"``
            text_column: Column that contains the document text.
            id_column: Column to use as document ID (optional).
            where_clause: Optional SQL ``WHERE`` filter (without the ``WHERE`` keyword).
            schema: Database schema (e.g. ``"public"`` for PostgreSQL).
            name: Identifier for the persisted index.
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
        """
        AlchemyStorage = _get_alchemy_storage_class()
        storage = AlchemyStorage(url=url)

        data = storage.read_table(
            table_name=table_name,
            text_column=text_column,
            id_column=id_column,
            where_clause=where_clause,
            schema=schema,
        )

        kwargs.setdefault("storage_type", "alchemy")
        kwargs.setdefault("alchemy_url", url)
        # Pass the already-built storage so we don't create a second engine
        instance = cls(name=name, autoload=False, storage=storage, **kwargs)
        instance._source_info = {
            "type": "table",
            "table_name": table_name,
            "text_column": text_column,
            "id_column": id_column,
            "where_clause": where_clause,
            "query": None,
        }
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

    def search(self, query: Union[str, List[str]], top_k: int = 10) -> SearchResponse:
        """
        Searches the indexed corpus for documents matching the query.

        The engine returns raw tuples; Lucis wraps them in a SearchResponse
        with full context: query, tokens, timing, and structured results.

        Args:
            query: A search string ("love python") or pre-tokenized list (["love", "python"]).
            top_k: Maximum number of results to return.

        Returns:
            SearchResponse with ranked results and search metadata.

        Example:
            response = lu.search("programación python", top_k=5)
            print(response.total_results)        # 5
            print(response.results[0].doc_id)     # "doc_001"
            print(response.results[0].score)      # 0.3903
            print(response.search_time_ms)        # 2.31
            print(response.to_dict())             # JSON-ready dict
        """
        if not self._is_indexed:
            raise LucisEngineError(
                engine_name=self.engine.name,
                detail="No index built yet. Use .index(data), .from_dict(), or .from_list() first."
            )

        # Preserve the original query before tokenization
        original_query = query

        # Tokenize here to capture the tokens for the response
        if isinstance(query, str):
            tokens = self.tokenizer(query)
        else:
            tokens = list(query)

        # Time the engine search (the core computation)
        start = time.perf_counter()
        raw_results = self.engine.search(tokens, top_k=top_k)
        elapsed_ms = (time.perf_counter() - start) * 1000

        # Wrap raw tuples into structured SearchResult objects
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

        Args:
            name: Optional custom name. Falls back to self.name.
        """
        save_name = name or self.name
        # Generate a versioned physical name (no-op on JSONStorage)
        physical_name = self.storage._generate_versioned_name(save_name)
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
        name transparently.

        Args:
            name: Optional custom name. Falls back to self.name.
        """
        load_name = name or self.name
        # Resolve alias → physical name (passthrough if no alias exists)
        physical_name = self.storage.resolve_alias(load_name)
        self.engine.load_engine(physical_name)
        self._is_indexed = True
        # Restore source info (if available) so create_worker() works
        source = self.storage.load_source_info(physical_name)
        if source is not None:
            self._source_info = source

    # Shadow Rebuild 

    def reindex(self, data: Union[List[str], Dict[Any, str]]) -> None:
        """
        Rebuild the index with fresh data, creating a new version.

        The previous version remains in storage so you can ``rollback()``
        if needed.  The alias is swapped atomically to the new version.

        Args:
            data: New corpus — ``Dict[id, text]`` or ``List[text]``.

        Example::

            new_data = storage.read_table("articles", text_column="content", id_column="id")
            luc.reindex(new_data)
            # → alias now points to the new version
        """
        self.engine.build_index(data)
        self._is_indexed = True
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
        tokenizer = self.tokenizer

        def _worker() -> None:
            try:
                # 1. Build in an isolated engine (no impact on live searches)
                shadow_engine = engine_class(storage=storage, tokenizer=tokenizer)
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
        """
        Return ``True`` if a background rebuild is in progress.

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

    def _auto_data_fn(self) -> Callable[[], Union[List[str], Dict[Any, str]]]:
        """Auto-generate a data_fn based on stored _source_info."""
        info = self._source_info
        storage = self.storage

        if info["type"] == "table":
            table_name = info["table_name"]
            text_col = info["text_column"]
            id_col = info["id_column"]
            where = info.get("where_clause")

            if hasattr(storage, "read_table"):
                def fetch():
                    return storage.read_table(
                        table_name, text_col, id_col, where
                    )
                return fetch
            else:
                # SQLiteStorage — build SQL manually
                cols = f"{id_col}, {text_col}" if id_col else text_col
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

    def _auto_change_detector(self) -> Optional[Callable[[], bool]]:
        """Auto-generate a count-based change detector if source is a table."""
        info = self._source_info
        if info is None or info["type"] != "table":
            return None

        table_name = info["table_name"]
        storage = self.storage
        last_count = [self.engine.total_docs if self._is_indexed else 0]

        def detect():
            current = storage.count_rows(table_name)
            if current != last_count[0]:
                last_count[0] = current
                return True
            return False

        return detect

    def create_worker(
        self,
        data_fn: Optional[Callable[[], Union[List[str], Dict[Any, str]]]] = None,
        interval: float = 60,
        change_detector: Optional[Callable[[], bool]] = None,
        auto_purge: bool = True,
        keep_versions: int = 3,
        on_rebuild: Optional[Callable[[str], None]] = None,
        on_error: Optional[Callable[[Exception], None]] = None,
        on_cycle: Optional[Callable[[int, bool], None]] = None,
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

        Args:
            data_fn: Callable that returns fresh data each cycle.
                If ``None``, auto-generated from source metadata.
            interval: Seconds between cycles (default 60).
            change_detector: Optional ``() → bool``.  When provided,
                the rebuild only runs if this returns ``True``.
                If ``None`` and source is a table, auto-generated
                using ``COUNT(*)`` comparison.
            auto_purge: Automatically clean old versions (default True).
            keep_versions: Versions to retain when purging (default 3).
            on_rebuild: Callback ``fn(physical_name)`` on success.
            on_error: Callback ``fn(exception)`` on failure.
            on_cycle: Callback ``fn(cycle_number, skipped)`` every cycle.

        Returns:
            An ``IndexWorker`` instance (not yet started).
            Call ``.start()`` to begin the loop.

        Example — zero config (auto data_fn)::

            luc = Lucis.from_alchemy_table("articles", url=URL,
                                           text_column="content",
                                           id_column="article_id",
                                           name="articles_idx")
            worker = luc.create_worker(interval=60)
            worker.start()

        Example — custom data_fn::

            worker = luc.create_worker(data_fn=my_fetch, interval=30)
            worker.start()
        """
        # Auto-generate data_fn if not provided
        if data_fn is None:
            if self._source_info is None:
                raise LucisEngineError(
                    engine_name=self.engine.name,
                    detail=(
                        "Cannot auto-generate data_fn: no source info available. "
                        "Either create the index with from_alchemy_table / "
                        "from_sqlite_table, or provide data_fn explicitly."
                    ),
                )
            data_fn = self._auto_data_fn()

        # Auto-generate change_detector if not provided
        if change_detector is None and self._source_info is not None:
            change_detector = self._auto_change_detector()

        from .worker import IndexWorker
        return IndexWorker(
            lucis=self,
            data_fn=data_fn,
            interval=interval,
            change_detector=change_detector,
            auto_purge=auto_purge,
            keep_versions=keep_versions,
            on_rebuild=on_rebuild,
            on_error=on_error,
            on_cycle=on_cycle,
        )

    # info and debugging
    def __repr__(self) -> str:
        status = "indexed" if self._is_indexed else "empty"
        docs = self.engine.total_docs if self._is_indexed else 0
        id_t = self.engine.id_type if self._is_indexed else "N/A"
        return f"Lucis(name='{self.name}', engine='{self.engine.name}', docs={docs}, idx_type='{id_t}', status='{status}')"