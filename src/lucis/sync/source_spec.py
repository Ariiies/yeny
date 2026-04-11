"""
SourceSpec — structured description of a Lucis data source.

Replaces the raw ``dict`` previously stored as ``_source_info`` with
a typed dataclass, making field access explicit and IDE-friendly.
"""
from dataclasses import dataclass
from typing import List, Optional, Union


@dataclass
class SourceSpec:
    """Describes the origin of indexed data for auto-sync operations.

    Every factory method (``from_sqlite_table``, ``from_alchemy_table``,
    etc.) creates a SourceSpec that is persisted alongside the index.
    The ``sync`` layer reads it to auto-generate ``data_fn``, ``delta_fn``,
    and ``change_detector`` callables for the ``IndexWorker``.

    Attributes:
        type: Source kind — ``"table"`` or ``"query"``.
        table_name: Name of the source table (``"table"`` type only).
        text_column: Column(s) containing document text.
        id_column: Column used as document ID (optional).
        date_column: Column used for temporal sharding (optional).
        where_clause: Optional SQL ``WHERE`` filter (without keyword).
        query: Raw SQL query (``"query"`` type only).
        schema: Database schema (e.g. ``"public"`` for PostgreSQL).
    """
    type: str
    table_name: Optional[str] = None
    text_column: Optional[Union[str, List[str]]] = None
    id_column: Optional[str] = None
    date_column: Optional[str] = None
    where_clause: Optional[str] = None
    query: Optional[str] = None
    schema: Optional[str] = None

    def to_dict(self) -> dict:
        """Serialize to a plain dict for storage persistence.

        The output is backward-compatible with the raw dicts used
        by ``save_source_info`` / ``load_source_info`` before the
        SourceSpec refactoring.
        """
        return {
            "type": self.type,
            "table_name": self.table_name,
            "text_column": self.text_column,
            "id_column": self.id_column,
            "date_column": self.date_column,
            "where_clause": self.where_clause,
            "query": self.query,
            "schema": self.schema,
        }

    @classmethod
    def from_dict(cls, d: Optional[dict]) -> Optional["SourceSpec"]:
        """Deserialize from a plain dict loaded from storage.

        Returns ``None`` if *d* is ``None`` (no source info stored).
        """
        if d is None:
            return None
        return cls(
            type=d["type"],
            table_name=d.get("table_name"),
            text_column=d.get("text_column"),
            id_column=d.get("id_column"),
            date_column=d.get("date_column"),
            where_clause=d.get("where_clause"),
            query=d.get("query"),
            schema=d.get("schema"),
        )
