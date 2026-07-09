"""
AlchemyLoadersMixin — Factory methods for SQLAlchemy data sources.

Contains the ``from_alchemy_table`` and ``from_alchemy_query`` class
methods that create a ready-to-search Lucis instance by reading rows
from any database supported by SQLAlchemy (MySQL, PostgreSQL, MariaDB,
etc.), including automatic temporal sharding and ``MetadataStorage``
handling. This is intentionally isolated from the other loaders since
it is the only one with a (lazy) dependency on ``sqlalchemy``.
"""
import os
from typing import TYPE_CHECKING, List, Optional, Union

from ...sync.source_spec import SourceSpec
from ..._internals import _get_alchemy_reader_class
from ...storage.metadata_storage import MetadataStorage

if TYPE_CHECKING:
    from ...main import Lucis


class AlchemyLoadersMixin:
    """Mixin that provides the ``from_alchemy_table`` and ``from_alchemy_query``
    factory methods."""

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
