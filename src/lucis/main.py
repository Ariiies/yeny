import time
from typing import Any, Dict, List, Optional, Union
from .engines.core import CoreEngine
from .engines.base import DocId
from .storage.base import BaseStorage
from .storage.json_storage import JSONStorage
from .storage.sqlite_storage import SQLiteStorage
from .exceptions import LucisEngineError
from .models.search import SearchResult, SearchResponse

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
            autoload: If True and an index with this name exists on disk, load it automatically.
        """
        self.name = name
        self._is_indexed = False

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
        self.engine = engine_class(storage=self.storage)

        # 3. Smart persistence: if the index already exists on disk, load it
        # This enables the "pick up where you left off" workflow:
        #   lu = Lucis(name="my_index")  →  ready to search immediately
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
        # (The engine's decorator will see it's already tokenized and pass through)
        if isinstance(query, str):
            from .utils.nlp import word_tokenizer
            tokens = word_tokenizer(query)
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
        
        Uses self.name by default, or a custom name if provided.
        This allows "save as" functionality: lu.save("backup_v2")

        Args:
            name: Optional custom name. Falls back to self.name.
        """
        save_name = name or self.name
        self.engine.persist(save_name)

    def load(self, name: Optional[str] = None) -> None:
        """
        Loads a previously saved index from storage.

        Args:
            name: Optional custom name. Falls back to self.name.
        """
        load_name = name or self.name
        self.engine.load_engine(load_name)
        self._is_indexed = True
    
    # info and debugging
    def __repr__(self) -> str:
        status = "indexed" if self._is_indexed else "empty"
        docs = self.engine.total_docs if self._is_indexed else 0
        id_t = self.engine.id_type if self._is_indexed else "N/A"
        return f"Lucis(name='{self.name}', engine='{self.engine.name}', docs={docs}, idx_type='{id_t}', status='{status}')"