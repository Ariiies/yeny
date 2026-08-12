"""
Lightweight metadata-only storage backend (SQLite + WAL).

Stores **only** Lucis orchestration metadata (aliases, shard registry,
source info, document counts).  Index data (inverted index, doc lengths,
id mapping) lives exclusively in ``.lcs`` binary files — this backend
never writes them to SQL.

WAL mode is enabled automatically so that a background worker can write
metadata while search threads read concurrently without blocking.
"""
from __future__ import annotations

import sqlite3
from datetime import datetime
from typing import Any, Dict, Optional

from .base import BaseStorage


class MetadataStorage(BaseStorage):
    """SQLite storage that persists **only** lightweight metadata.

    Heavy index data (inverted index, doc lengths, id mapping) is NOT
    stored here — it lives in ``.lcs`` files managed by the
    :class:`~lucis.core.shard.ShardManager`.

    Tables created:
        - ``lucis_metadata``       — per-index document counts and source info
        - ``lucis_aliases``        — alias → physical name mapping
        - ``lucis_shard_registry`` — shard key lists

    Args:
        db_path: Path to the SQLite database file.
        connection: An existing ``sqlite3.Connection`` (optional).
    """

    def __init__(
        self,
        db_path: str,
        connection: Optional[sqlite3.Connection] = None,
    ):
        if connection is not None:
            self.conn = connection
            self._owns_connection = False
        else:
            self.conn = sqlite3.connect(db_path, check_same_thread=False)
            self._owns_connection = True

        self.db_path = db_path

        # Enable WAL for concurrent reader/writer access
        self.conn.execute("PRAGMA journal_mode=WAL")

        self._initialize_schema()

    # Schema initialization and migration

    def _initialize_schema(self) -> None:
        cur = self.conn.cursor()

        cur.execute("""
            CREATE TABLE IF NOT EXISTS lucis_metadata (
                index_name          TEXT PRIMARY KEY,
                total_docs          INTEGER NOT NULL,
                id_type             TEXT NOT NULL,
                engine_name         TEXT NOT NULL,
                source_table        TEXT,
                source_column       TEXT,
                source_id_column    TEXT,
                source_date_column  TEXT,
                source_query        TEXT,
                source_where        TEXT,
                created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS lucis_aliases (
                alias_name      TEXT PRIMARY KEY,
                target_index    TEXT NOT NULL
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS lucis_shard_registry (
                index_name  TEXT NOT NULL,
                shard_key   TEXT NOT NULL,
                PRIMARY KEY (index_name, shard_key)
            )
        """)

        self.conn.commit()

    # BaseStorage interface

    def save(self, data: Dict[str, Any], name: str) -> None:
        """Persist **only metadata** — index data is ignored.

        The *data* dict may contain ``index``, ``doc_lengths``, etc.
        but they are silently skipped.  Only ``total_docs``, ``id_type``,
        and ``engine_name`` are stored.
        """
        cur = self.conn.cursor()
        cur.execute("""
            INSERT OR REPLACE INTO lucis_metadata
                (index_name, total_docs, id_type, engine_name, updated_at)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
        """, (
            name,
            data.get("total_docs", 0),
            data.get("id_type", "none"),
            data.get("engine_name", "LiteEngine"),
        ))
        self.conn.commit()

    def load(self, name: str) -> Dict[str, Any]:
        """Load metadata only.

        Returns a minimal state dict.  The caller must load actual index
        data from ``.lcs`` files separately via ``engine.load_mmap()``.
        """
        cur = self.conn.cursor()
        cur.execute(
            "SELECT total_docs, id_type FROM lucis_metadata WHERE index_name = ?",
            (name,),
        )
        row = cur.fetchone()
        if row is None:
            raise FileNotFoundError(f"Index '{name}' not found in metadata database")

        total_docs, id_type = row
        return {
            "total_docs": total_docs,
            "id_type": id_type,
            # Empty placeholders — real data comes from .lcs
            "index": {},
            "doc_vectors": {},
            "id_map": {},
            "doc_lengths": {},
        }

    def exists(self, name: str) -> bool:
        resolved = self.resolve_alias(name)
        cur = self.conn.cursor()
        cur.execute(
            "SELECT 1 FROM lucis_metadata WHERE index_name = ? LIMIT 1",
            (resolved,),
        )
        return cur.fetchone() is not None

    # Alias support

    def resolve_alias(self, name: str) -> str:
        target = self.get_alias(name)
        return target if target is not None else name

    def set_alias(self, alias_name: str, target_index: str) -> None:
        cur = self.conn.cursor()
        cur.execute(
            "INSERT OR REPLACE INTO lucis_aliases (alias_name, target_index) "
            "VALUES (?, ?)",
            (alias_name, target_index),
        )
        self.conn.commit()

    def get_alias(self, alias_name: str) -> Optional[str]:
        cur = self.conn.cursor()
        cur.execute(
            "SELECT target_index FROM lucis_aliases WHERE alias_name = ?",
            (alias_name,),
        )
        row = cur.fetchone()
        return row[0] if row else None

    def list_aliases(self) -> Dict[str, str]:
        cur = self.conn.cursor()
        cur.execute(
            "SELECT alias_name, target_index FROM lucis_aliases ORDER BY alias_name"
        )
        return {row[0]: row[1] for row in cur.fetchall()}

    def delete_alias(self, alias_name: str) -> None:
        cur = self.conn.cursor()
        cur.execute(
            "DELETE FROM lucis_aliases WHERE alias_name = ?",
            (alias_name,),
        )
        self.conn.commit()

    # Versioning

    def _generate_versioned_name(self, base_name: str) -> str:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"{base_name}__v{ts}"

    def list_versions(self, base_name: str) -> list:
        cur = self.conn.cursor()
        cur.execute(
            "SELECT index_name FROM lucis_metadata "
            "WHERE index_name LIKE ? AND index_name NOT LIKE '%__shard__%' "
            "ORDER BY index_name",
            (f"{base_name}__v%",),
        )
        return [row[0] for row in cur.fetchall()]

    # Source info

    def save_source_info(self, name: str, info: Dict[str, Any]) -> None:
        import json as _json
        text_col = info.get("text_columns")
        source_column = _json.dumps(text_col) if isinstance(text_col, list) else text_col
        cur = self.conn.cursor()
        cur.execute(
            "UPDATE lucis_metadata "
            "SET source_table = ?, source_column = ?, source_id_column = ?, "
            "source_date_column = ?, source_query = ?, source_where = ? "
            "WHERE index_name = ?",
            (
                info.get("table"),
                source_column,
                info.get("id_column"),
                info.get("date_column"),
                info.get("query"),
                info.get("where_clause"),
                name,
            ),
        )
        self.conn.commit()

    def load_source_info(self, name: str) -> Optional[Dict[str, Any]]:
        cur = self.conn.cursor()
        cur.execute(
            "SELECT source_table, source_column, source_id_column, "
            "source_date_column, source_query, source_where "
            "FROM lucis_metadata WHERE index_name = ?",
            (name,),
        )
        row = cur.fetchone()
        if row is None:
            return None

        (source_table, source_column, source_id_column,
         source_date_column, source_query, source_where) = row

        import json as _json
        try:
            parsed_col = _json.loads(source_column) if source_column else source_column
            text_column = parsed_col if isinstance(parsed_col, list) else source_column
        except (TypeError, ValueError):
            text_column = source_column

        if source_query is not None:
            return {
                "type": "query",
                "table": None,
                "text_columns": None,
                "id_column": None,
                "date_column": None,
                "where_clause": None,
                "query": source_query,
            }

        if source_table is not None:
            return {
                "type": "table",
                "table": source_table,
                "text_columns": text_column,
                "id_column": source_id_column,
                "date_column": source_date_column,
                "where_clause": source_where,
                "query": None,
            }

        return None

    # Shard registry

    def save_shard_registry(self, index_name: str, shard_keys: list) -> None:
        cur = self.conn.cursor()
        cur.execute(
            "DELETE FROM lucis_shard_registry WHERE index_name = ?",
            (index_name,),
        )
        if shard_keys:
            cur.executemany(
                "INSERT INTO lucis_shard_registry (index_name, shard_key) "
                "VALUES (?, ?)",
                [(index_name, key) for key in shard_keys],
            )
        self.conn.commit()

    def load_shard_registry(self, index_name: str) -> list:
        cur = self.conn.cursor()
        cur.execute(
            "SELECT shard_key FROM lucis_shard_registry "
            "WHERE index_name = ? ORDER BY shard_key",
            (index_name,),
        )
        return [row[0] for row in cur.fetchall()]

    # Doc count (metadata-only query) 

    def get_total_docs(self, name: str) -> int:
        cur = self.conn.cursor()
        cur.execute(
            "SELECT total_docs FROM lucis_metadata WHERE index_name = ? LIMIT 1",
            (name,),
        )
        row = cur.fetchone()
        return int(row[0]) if row else 0

    # Extras

    def delete(self, name: str) -> None:
        shard_keys = self.load_shard_registry(name)
        cur = self.conn.cursor()

        for key in shard_keys:
            shard_name = f"{name}__shard__{key}"
            cur.execute(
                "DELETE FROM lucis_metadata WHERE index_name = ?",
                (shard_name,),
            )

        if shard_keys:
            cur.execute(
                "DELETE FROM lucis_shard_registry WHERE index_name = ?",
                (name,),
            )

        cur.execute(
            "DELETE FROM lucis_metadata WHERE index_name = ?",
            (name,),
        )
        self.conn.commit()

    def list_indices(self):
        cur = self.conn.cursor()
        cur.execute("SELECT index_name FROM lucis_metadata ORDER BY index_name")
        return [row[0] for row in cur.fetchall()]

    # Lifecycle managemenT

    def close(self) -> None:
        if self._owns_connection:
            self.conn.close()

    def __del__(self):
        try:
            self.close()
        except Exception:
            pass

    def __repr__(self) -> str:
        return f"MetadataStorage(db_path='{self.db_path}')"
