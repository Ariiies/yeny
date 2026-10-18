"""Factory methods for database-backed Yeny indexes.

The public API describes tables, queries, and connection URLs. SQLAlchemy is
kept behind the lazily imported read-only adapter that implements those
operations.
"""

import logging
import os
from dataclasses import replace
from typing import TYPE_CHECKING, Any, Callable, Optional

from ..._internals import _get_database_reader_class
from ...config import YenyOptions, TableConfig, TableSource
from ...storage.metadata_storage import MetadataStorage
from ...sync.source_spec import SourceSpec

if TYPE_CHECKING:
    from ...main import Yeny


class DatabaseLoadersMixin:
    """Provide the ``from_table`` and ``from_query`` factories."""

    @staticmethod
    def _create_database_reader(connection_url: str) -> Any:
        """Create the lazily imported read-only database adapter."""
        DatabaseReader = _get_database_reader_class()
        return DatabaseReader(connection_url=connection_url)

    @staticmethod
    def _resolve_date_column(
        reader: Any,
        source: TableSource,
        config: TableConfig,
    ) -> Optional[str]:
        """Resolve automatic temporal-column selection."""
        if source.date_column == "auto":
            return reader.detect_date_column(source.table, config.schema)
        return source.date_column

    @staticmethod
    def _resolve_binary_metadata_dir(
        storage_dir: str,
        binary_dir: Optional[str],
    ) -> str:
        """Resolve and create the directory that owns ``yeny_meta.db``."""
        if binary_dir == "auto":
            meta_dir = os.path.join(storage_dir, "yny")
        elif binary_dir:
            meta_dir = binary_dir
        else:
            meta_dir = storage_dir
        os.makedirs(meta_dir, exist_ok=True)
        return meta_dir

    @staticmethod
    def _create_source_metadata_storage(meta_dir: str) -> MetadataStorage:
        """Create metadata-only storage beside the binary artifacts."""
        return MetadataStorage(db_path=os.path.join(meta_dir, "yeny_meta.db"))

    @staticmethod
    def _table_source_spec(
        source: TableSource,
        config: TableConfig,
        date_column: Optional[str],
    ) -> SourceSpec:
        return SourceSpec(
            type="table",
            table=source.table,
            text_columns=source.text_columns,
            id_column=source.id_column,
            date_column=date_column,
            where_clause=config.where_clause,
            schema=config.schema,
        )

    @classmethod
    def _build_sharded_source(
        cls,
        instance: "Yeny",
        reader: Any,
        source: TableSource,
        config: TableConfig,
        date_column: str,
        persist_name: Optional[str],
    ) -> None:
        """Stream a table into temporal shards and mark the index ready."""
        if hasattr(reader, "stream_table_with_dates"):
            row_iter = reader.stream_table_with_dates(
                source.table,
                source.text_columns,
                source.id_column,
                date_column,
                config.where_clause,
                config.schema,
            )
            instance._shard_manager.build_shards_streaming(
                row_iter,
                batch_size=config.shard_batch_size,
                persist_base_name=persist_name,
                stream_ordered=config.stream_ordered,
            )
        else:
            data, dates = reader.read_table_with_dates(
                source.table,
                source.text_columns,
                source.id_column,
                date_column,
                config.where_clause,
                config.schema,
            )
            instance._shard_manager.build_shards(data, dates)
        instance._is_indexed = True

    @staticmethod
    def _finalize_sharded_build(
        instance: "Yeny",
        logical_name: str,
        persist_name: Optional[str],
    ) -> None:
        """Persist a sharded build and restore its steady-state footprint."""
        if not persist_name:
            instance.save()
            return

        instance._shard_manager.persist_all(persist_name)
        parent_state = {
            "index": {},
            "total_docs": instance._shard_manager.total_docs,
            "doc_lengths": {},
            "id_map": {},
            "id_type": instance._shard_manager.id_type,
            "engine_name": instance.engine.name,
        }
        instance.storage.save(parent_state, persist_name)
        instance.storage.set_alias(logical_name, persist_name)
        if instance._source_info is not None:
            instance.storage.save_source_info(
                persist_name, instance._source_info.to_dict()
            )

        instance._shard_manager._lazy_base_name = persist_name
        evicted = instance._shard_manager.trim_to_budget()
        if evicted:
            logging.getLogger(__name__).info(
                "Post-index trim: evicted %d shards to fit memory budget "
                "(%.0f MB in RAM).",
                evicted,
                instance._shard_manager.loaded_memory_mb,
            )
        instance._post_index_cleanup(logical_name)

    @staticmethod
    def _build_non_sharded_source(
        instance: "Yeny",
        reader: Any,
        source: TableSource,
        config: TableConfig,
    ) -> None:
        """Read and index a table without temporal partitioning."""
        data = reader.read_table(
            table=source.table,
            text_columns=source.text_columns,
            id_column=source.id_column,
            where_clause=config.where_clause,
            schema=config.schema,
        )
        instance.index(data)

    @classmethod
    def from_table(
        cls,
        source: TableSource,
        name: str = "default",
        *,
        engine: str = "core",
        preprocessor: Optional[Callable] = None,
        config: Optional[TableConfig] = None,
        options: Optional[YenyOptions] = None,
    ) -> "Yeny":
        """Build a ready-to-search index from a database table.

        ``source`` says what to read, ``config`` controls advanced ingestion,
        and ``options`` controls Yeny infrastructure. A temporal column is
        auto-detected by default; set ``source.date_column=None`` to disable
        temporal sharding.
        """
        table_config = config or TableConfig()
        source_options = replace(
            options or YenyOptions(),
            storage_type="alchemy",
            connection_url=source.connection_url,
        )
        reader = cls._create_database_reader(source.connection_url)
        date_column = cls._resolve_date_column(reader, source, table_config)
        meta_dir = cls._resolve_binary_metadata_dir(
            source_options.storage_dir,
            source_options.binary_dir,
        )
        storage = cls._create_source_metadata_storage(meta_dir)

        instance = cls(
            name=name,
            engine=engine,
            preprocessor=preprocessor,
            autoload=False,
            storage=storage,
            options=source_options,
        )
        instance._reader = reader
        instance._source_info = cls._table_source_spec(
            source, table_config, date_column
        )

        if date_column:
            instance._init_shard_manager()
            persist_name = None
            if instance._shard_manager._is_managed:
                persist_name = instance.storage._generate_versioned_name(name)
            cls._build_sharded_source(
                instance,
                reader,
                source,
                table_config,
                date_column,
                persist_name,
            )
            cls._finalize_sharded_build(instance, name, persist_name)
        else:
            cls._build_non_sharded_source(
                instance, reader, source, table_config
            )

        return instance

    @classmethod
    def from_query(
        cls,
        query: str,
        connection_url: str,
        name: str = "default",
        *,
        engine: str = "core",
        preprocessor: Optional[Callable] = None,
        options: Optional[YenyOptions] = None,
    ) -> "Yeny":
        """Build a ready-to-search index from an arbitrary SQL query.

        One returned column is interpreted as text. With two or more columns,
        the first is the document ID and the second is searchable text.
        """
        source_options = replace(
            options or YenyOptions(),
            storage_type="alchemy",
            connection_url=connection_url,
        )
        reader = cls._create_database_reader(connection_url)
        data = reader.read_query(query)

        meta_dir = cls._resolve_binary_metadata_dir(
            source_options.storage_dir,
            source_options.binary_dir,
        )
        storage = cls._create_source_metadata_storage(meta_dir)
        instance = cls(
            name=name,
            engine=engine,
            preprocessor=preprocessor,
            autoload=False,
            storage=storage,
            options=source_options,
        )
        instance._reader = reader
        instance._source_info = SourceSpec(type="query", query=query)
        instance.index(data)
        return instance
