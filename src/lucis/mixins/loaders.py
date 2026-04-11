"""
LoaderMixin — Factory methods for creating Lucis instances from data sources.

Contains all the ``from_*`` class methods that create a ready-to-search
Lucis instance from different data sources: dicts, lists, SQLite
tables/queries, and SQLAlchemy tables/queries.
"""
import os
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Union

from ..sync.source_spec import SourceSpec
from .._internals import _build_sql_text_expr, _get_alchemy_reader_class
from ..storage.metadata_storage import MetadataStorage

if TYPE_CHECKING:
    from ..main import Lucis


class LoaderMixin:
    """Mixin that provides ``from_*`` factory class methods.

    These methods create a new ``Lucis`` instance, ingest data from
    the specified source, persist the index, and return it ready to
    search.

    All methods are ``@classmethod`` — they receive ``cls`` (which is
    ``Lucis`` at runtime due to MRO) and delegate to ``index()``,
    ``save()``, and internal helpers defined on the full class.
    """

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
        instance._source_info = SourceSpec(
            type="table",
            table_name=table_name,
            text_column=text_column,
            id_column=id_column,
            date_column=None,
            where_clause=where_clause,
        )
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
        instance._source_info = SourceSpec(
            type="query",
            query=query,
        )
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
        AlchemyReader = _get_alchemy_reader_class()
        reader = AlchemyReader(url=url)

        # Resolve date column
        resolved_date_col = date_column
        if date_column == "auto":
            resolved_date_col = reader.detect_date_column(table_name, schema)

        # Resolve binary_dir to place MetadataStorage DB alongside .lcs files
        binary_dir_val = kwargs.get("binary_dir", "auto")
        storage_dir_val = kwargs.get("storage_dir", "lucis_data")
        if binary_dir_val == "auto":
            meta_dir = os.path.join(storage_dir_val, "lcs")
        elif binary_dir_val:
            meta_dir = binary_dir_val
        else:
            meta_dir = storage_dir_val
        os.makedirs(meta_dir, exist_ok=True)
        meta_db_path = os.path.join(meta_dir, "lucis_meta.db")
        storage = MetadataStorage(db_path=meta_db_path)

        kwargs.setdefault("storage_type", "alchemy")
        kwargs.setdefault("alchemy_url", url)
        # Pass the MetadataStorage so we don't create AlchemyStorage
        instance = cls(name=name, autoload=False, storage=storage, **kwargs)
        instance._reader = reader
        instance._source_info = SourceSpec(
            type="table",
            table_name=table_name,
            text_column=text_column,
            id_column=id_column,
            date_column=resolved_date_col,
            where_clause=where_clause,
            schema=schema,
        )

        if resolved_date_col:
            # Sharded mode: stream rows → build_shards_streaming (no fetchall)
            instance._init_shard_manager()

            # Pre-generate the physical name so the builder can persist
            # shards incrementally when memory management is active.
            persist_name = None
            if instance._shard_manager._is_managed:
                persist_name = instance.storage._generate_versioned_name(name)

            if hasattr(reader, "stream_table_with_dates"):
                row_iter = reader.stream_table_with_dates(
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
                # Fallback for non-streaming reader
                data, dates = reader.read_table_with_dates(
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
                    instance.storage.save_source_info(
                        persist_name, instance._source_info.to_dict()
                    )

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

                # Post-index RAM cleanup
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
            data = reader.read_table(
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
        AlchemyReader = _get_alchemy_reader_class()
        reader = AlchemyReader(url=url)

        data = reader.read_query(query)

        # Resolve binary_dir for MetadataStorage
        storage_dir_val = kwargs.get("storage_dir", "lucis_data")
        binary_dir_val = kwargs.get("binary_dir", "auto")
        if binary_dir_val == "auto":
            meta_dir = os.path.join(storage_dir_val, "lcs")
        elif binary_dir_val:
            meta_dir = binary_dir_val
        else:
            meta_dir = storage_dir_val
        os.makedirs(meta_dir, exist_ok=True)
        meta_db_path = os.path.join(meta_dir, "lucis_meta.db")
        storage = MetadataStorage(db_path=meta_db_path)

        kwargs.setdefault("storage_type", "alchemy")
        kwargs.setdefault("alchemy_url", url)
        instance = cls(name=name, autoload=False, storage=storage, **kwargs)
        instance._reader = reader
        instance._source_info = SourceSpec(
            type="query",
            query=query,
        )
        instance.index(data)
        return instance
