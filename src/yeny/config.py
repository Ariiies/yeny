"""Typed configuration objects for advanced Yeny infrastructure.

The high-level intent of an index remains expressed directly on ``Yeny`` and
its factories.  These immutable dataclasses group only infrastructure and
source-tuning options that would otherwise make every public signature long.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Union


@dataclass(frozen=True)
class YenyOptions:
    """Advanced infrastructure shared by ``Yeny`` and its factories.

    Attributes:
        storage_dir: Directory used by JSON storage and as the base for the
            automatic binary directory.
        storage_type: Declarative storage backend: ``"json"``, ``"sqlite"``
            or ``"alchemy"``.  An explicitly injected ``storage`` object on
            :class:`yeny.Yeny` takes precedence over these fields.
        db_path: SQLite persistence path.  Required when ``storage_type`` is
            ``"sqlite"`` and no storage object is injected.
        connection_url: Database connection URL.  Required when
            ``storage_type`` is ``"alchemy"`` and no storage object is
            injected.
        max_loaded_shards: Maximum number of temporal shards kept in memory.
            ``0`` keeps the existing eager, unlimited behavior.
        memory_limit_mb: Approximate memory budget for loaded shards, or
            ``None`` for no budget.
        binary_dir: Tri-state binary persistence setting.  ``"auto"`` derives
            ``<storage_dir>/yny``; ``None`` disables ``.yny`` persistence; any
            other string is used as an explicit directory.  SQLAlchemy
            factories use metadata-only storage, so keep binaries enabled when
            their indexes must be reloadable.
    """

    storage_dir: str = "yeny_data"
    storage_type: str = "json"
    db_path: Optional[str] = None
    connection_url: Optional[str] = None
    max_loaded_shards: int = 0
    memory_limit_mb: Optional[int] = None
    binary_dir: Optional[str] = "auto"


@dataclass(frozen=True)
class TableSource:
    """Describe the database table that ``Yeny.from_table`` will index.

    ``text_columns`` accepts either one column or multiple columns.  Multiple
    values are concatenated into one searchable document by the database
    reader.
    """

    table: str
    connection_url: str
    text_columns: Union[str, List[str]]
    id_column: Optional[str] = None
    date_column: Optional[str] = "auto"


@dataclass(frozen=True)
class TableConfig:
    """Advanced source tuning for ``Yeny.from_table``.

    Attributes:
        where_clause: SQL ``WHERE`` expression without the ``WHERE`` keyword.
        schema: Optional database schema containing the source table.
        shard_batch_size: Rows buffered per shard during streaming ingestion.
        stream_ordered: Whether rows are guaranteed to arrive in chronological
            order.  This enables in-flight persistence and eviction when a
            memory limit is active.  Setting it incorrectly can truncate a
            shard, so the safe default is ``False``.
    """

    where_clause: Optional[str] = None
    schema: Optional[str] = None
    shard_batch_size: int = 20_000
    stream_ordered: bool = False


__all__ = ["YenyOptions", "TableSource", "TableConfig"]
