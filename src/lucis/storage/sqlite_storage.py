# src/lucis/storage/sqlite_storage.py
import sqlite3
from datetime import datetime
from typing import Any, Dict, Optional
from .base import BaseStorage


class SQLiteStorage(BaseStorage):
    """
    Production storage backend using SQLite.

    Connects to an existing (or new) SQLite database and creates
    the necessary ``lucis_*`` tables to persist search indices.
    All Lucis tables are prefixed with ``lucis_`` so they never
    collide with the user's own tables.

    Two modes of operation:
        1. **Index**: read user data, build the index, persist it.
        2. **Load**: read previously-persisted index tables (skip recomputation).

    Args:
        db_path: Path to the SQLite database file.
        connection: An existing ``sqlite3.Connection`` (optional, for
            advanced users who want to share a connection with their app).

    Example – basic usage::

        storage = SQLiteStorage("my_data.db")
        storage.save(engine_state, "articles_idx")
        state = storage.load("articles_idx")

    Example – shared connection::

        conn = sqlite3.connect("app.db")
        storage = SQLiteStorage("app.db", connection=conn)
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
        self._initialize_schema()

    #  Schema bootstrap                                                    
    def _initialize_schema(self) -> None:
        """Create the ``lucis_*`` tables if they don't already exist."""
        cur = self.conn.cursor()

        cur.execute("""
            CREATE TABLE IF NOT EXISTS lucis_metadata (
                index_name      TEXT PRIMARY KEY,
                total_docs      INTEGER NOT NULL,
                id_type         TEXT NOT NULL,
                engine_name     TEXT NOT NULL,
                source_table    TEXT,
                source_column   TEXT,
                source_id_column TEXT,
                source_query    TEXT,
                source_where    TEXT,
                created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS lucis_inverted_index (
                index_name      TEXT    NOT NULL,
                word            TEXT    NOT NULL,
                doc_internal_id INTEGER NOT NULL,
                frequency       INTEGER NOT NULL,
                PRIMARY KEY (index_name, word, doc_internal_id),
                FOREIGN KEY (index_name) REFERENCES lucis_metadata(index_name)
            )
        """)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_lucis_word
            ON lucis_inverted_index(index_name, word)
        """)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_lucis_doc
            ON lucis_inverted_index(index_name, doc_internal_id)
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS lucis_doc_vectors (
                index_name      TEXT    NOT NULL,
                doc_internal_id INTEGER NOT NULL,
                word            TEXT    NOT NULL,
                tfidf_score     REAL    NOT NULL,
                PRIMARY KEY (index_name, doc_internal_id, word),
                FOREIGN KEY (index_name) REFERENCES lucis_metadata(index_name)
            )
        """)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_lucis_vector_doc
            ON lucis_doc_vectors(index_name, doc_internal_id)
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS lucis_id_mapping (
                index_name  TEXT    NOT NULL,
                internal_id INTEGER NOT NULL,
                original_id TEXT    NOT NULL,
                PRIMARY KEY (index_name, internal_id),
                FOREIGN KEY (index_name) REFERENCES lucis_metadata(index_name)
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS lucis_doc_lengths (
                index_name      TEXT    NOT NULL,
                doc_internal_id INTEGER NOT NULL,
                length          INTEGER NOT NULL,
                PRIMARY KEY (index_name, doc_internal_id),
                FOREIGN KEY (index_name) REFERENCES lucis_metadata(index_name)
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS lucis_aliases (
                alias_name      TEXT PRIMARY KEY,
                target_index    TEXT NOT NULL
            )
        """)

        self.conn.commit()

    #  BaseStorage interface          
                                       
    def save(self, data: Dict[str, Any], name: str) -> None:
        """
        Persist the engine state into the ``lucis_*`` tables.

        ``data`` is the bundle produced by ``CoreEngine.persist()`` and
        contains the keys: *index*, *doc_vectors*, *id_map*, *doc_lengths*,
        *total_docs*, *id_type*.
        """
        cur = self.conn.cursor()

        try:
            # 1. Metadata 
            cur.execute("""
                INSERT OR REPLACE INTO lucis_metadata
                    (index_name, total_docs, id_type, engine_name, updated_at)
                VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (name, data["total_docs"], data["id_type"], "CoreEngine"))

            # 2. Wipe previous data for this index 
            for table in (
                "lucis_inverted_index",
                "lucis_doc_vectors",
                "lucis_id_mapping",
                "lucis_doc_lengths",
            ):
                cur.execute(f"DELETE FROM {table} WHERE index_name = ?", (name,))

            # 3. Inverted index 
            inv_rows = [
                (name, word, int(doc_id), freq)
                for word, docs in data["index"].items()
                for doc_id, freq in docs.items()
            ]
            cur.executemany(
                "INSERT INTO lucis_inverted_index VALUES (?, ?, ?, ?)",
                inv_rows,
            )

            # 4. TF-IDF document vectors 
            vec_rows = [
                (name, int(doc_id), word, score)
                for doc_id, vector in data["doc_vectors"].items()
                for word, score in vector.items()
            ]
            cur.executemany(
                "INSERT INTO lucis_doc_vectors VALUES (?, ?, ?, ?)",
                vec_rows,
            )

            # 5. ID mapping (internal → original) 
            id_rows = [
                (name, int(internal_id), str(original_id))
                for internal_id, original_id in data["id_map"].items()
            ]
            cur.executemany(
                "INSERT INTO lucis_id_mapping VALUES (?, ?, ?)",
                id_rows,
            )

            # 6. Document lengths 
            len_rows = [
                (name, int(doc_id), length)
                for doc_id, length in data["doc_lengths"].items()
            ]
            cur.executemany(
                "INSERT INTO lucis_doc_lengths VALUES (?, ?, ?)",
                len_rows,
            )

            self.conn.commit()

        except Exception as exc:
            self.conn.rollback()
            raise RuntimeError(f"Failed to save index '{name}': {exc}") from exc

    def load(self, name: str) -> Dict[str, Any]:
        """
        Reconstruct an engine state dict from the ``lucis_*`` tables.

        The returned dict has the same shape that ``CoreEngine.load_engine``
        expects: *index*, *doc_vectors*, *id_map*, *doc_lengths*,
        *total_docs*, *id_type*.
        """
        cur = self.conn.cursor()

        # 1. Metadata 
        cur.execute(
            "SELECT total_docs, id_type FROM lucis_metadata WHERE index_name = ?",
            (name,),
        )
        meta = cur.fetchone()
        if meta is None:
            raise FileNotFoundError(f"Index '{name}' not found in database")
        total_docs, id_type = meta

        # 2. Inverted index 
        cur.execute(
            "SELECT word, doc_internal_id, frequency "
            "FROM lucis_inverted_index WHERE index_name = ?",
            (name,),
        )
        index: Dict[str, Dict[int, int]] = {}
        for word, doc_id, freq in cur.fetchall():
            index.setdefault(word, {})[doc_id] = freq

        # 3. Document vectors 
        cur.execute(
            "SELECT doc_internal_id, word, tfidf_score "
            "FROM lucis_doc_vectors WHERE index_name = ?",
            (name,),
        )
        doc_vectors: Dict[int, Dict[str, float]] = {}
        for doc_id, word, score in cur.fetchall():
            doc_vectors.setdefault(doc_id, {})[word] = score

        # 4. ID mapping 
        cur.execute(
            "SELECT internal_id, original_id "
            "FROM lucis_id_mapping WHERE index_name = ?",
            (name,),
        )
        id_map: Dict[int, Any] = {}
        for internal_id, original_id in cur.fetchall():
            # If the original ID looks like an integer, restore it as int
            # (id_type tells us the original format)
            if id_type == "sequential":
                id_map[internal_id] = int(original_id)
            else:
                id_map[internal_id] = original_id

        # 5. Document lengths 
        cur.execute(
            "SELECT doc_internal_id, length "
            "FROM lucis_doc_lengths WHERE index_name = ?",
            (name,),
        )
        doc_lengths: Dict[int, int] = {doc_id: length for doc_id, length in cur.fetchall()}

        return {
            "index": index,
            "doc_vectors": doc_vectors,
            "id_map": id_map,
            "doc_lengths": doc_lengths,
            "total_docs": total_docs,
            "id_type": id_type,
        }

    def exists(self, name: str) -> bool:
        """Return ``True`` if *name* can be resolved to a persisted index.

        Checks in order:
        1. Is *name* an alias that points to an existing physical index?
        2. Is *name* itself a physical index in ``lucis_metadata``?
        """
        resolved = self.resolve_alias(name)
        cur = self.conn.cursor()
        cur.execute(
            "SELECT 1 FROM lucis_metadata WHERE index_name = ? LIMIT 1",
            (resolved,),
        )
        return cur.fetchone() is not None

    #  Alias / versioning support                                         #

    def resolve_alias(self, name: str) -> str:
        """Resolve *name* to a physical index name.

        If *name* is a registered alias, return its target.
        Otherwise return *name* unchanged.
        """
        target = self.get_alias(name)
        return target if target is not None else name

    def set_alias(self, alias_name: str, target_index: str) -> None:
        """Create or update an alias → target mapping."""
        cur = self.conn.cursor()
        cur.execute(
            "INSERT OR REPLACE INTO lucis_aliases (alias_name, target_index) "
            "VALUES (?, ?)",
            (alias_name, target_index),
        )
        self.conn.commit()

    def get_alias(self, alias_name: str) -> Optional[str]:
        """Return the physical index name for *alias_name*, or ``None``."""
        cur = self.conn.cursor()
        cur.execute(
            "SELECT target_index FROM lucis_aliases WHERE alias_name = ?",
            (alias_name,),
        )
        row = cur.fetchone()
        return row[0] if row else None

    def list_aliases(self) -> Dict[str, str]:
        """Return all aliases as ``{alias_name: target_index}``."""
        cur = self.conn.cursor()
        cur.execute(
            "SELECT alias_name, target_index FROM lucis_aliases ORDER BY alias_name"
        )
        return {row[0]: row[1] for row in cur.fetchall()}

    def delete_alias(self, alias_name: str) -> None:
        """Remove an alias (does NOT delete the physical index)."""
        cur = self.conn.cursor()
        cur.execute(
            "DELETE FROM lucis_aliases WHERE alias_name = ?",
            (alias_name,),
        )
        self.conn.commit()

    def _generate_versioned_name(self, base_name: str) -> str:
        """Return ``base_name__vYYYYMMDD_HHMMSS``."""
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"{base_name}__v{ts}"

    def list_versions(self, base_name: str) -> list:
        """Return all physical versions of *base_name*, sorted oldest → newest."""
        cur = self.conn.cursor()
        cur.execute(
            "SELECT index_name FROM lucis_metadata "
            "WHERE index_name LIKE ? ORDER BY index_name",
            (f"{base_name}__v%",),
        )
        return [row[0] for row in cur.fetchall()]

    #  Source-info persistence (smart worker support)                       #

    def save_source_info(self, name: str, info: Dict[str, Any]) -> None:
        """Persist data-source metadata into ``lucis_metadata``."""
        cur = self.conn.cursor()
        cur.execute(
            "UPDATE lucis_metadata "
            "SET source_table = ?, source_column = ?, source_id_column = ?, "
            "source_query = ?, source_where = ? "
            "WHERE index_name = ?",
            (
                info.get("table_name"),
                info.get("text_column"),
                info.get("id_column"),
                info.get("query"),
                info.get("where_clause"),
                name,
            ),
        )
        self.conn.commit()

    def load_source_info(self, name: str) -> Optional[Dict[str, Any]]:
        """Load source metadata from ``lucis_metadata``."""
        cur = self.conn.cursor()
        cur.execute(
            "SELECT source_table, source_column, source_id_column, "
            "source_query, source_where "
            "FROM lucis_metadata WHERE index_name = ?",
            (name,),
        )
        row = cur.fetchone()
        if row is None:
            return None

        source_table, source_column, source_id_column, source_query, source_where = row

        # Query-based source
        if source_query is not None:
            return {
                "type": "query",
                "table_name": None,
                "text_column": None,
                "id_column": None,
                "where_clause": None,
                "query": source_query,
            }

        # Table-based source
        if source_table is not None:
            return {
                "type": "table",
                "table_name": source_table,
                "text_column": source_column,
                "id_column": source_id_column,
                "where_clause": source_where,
                "query": None,
            }

        return None

    def count_rows(self, table_name: str) -> Optional[int]:
        """Return ``SELECT COUNT(*) FROM <table_name>``."""
        cur = self.conn.cursor()
        cur.execute(f"SELECT COUNT(*) FROM {table_name}")
        return cur.fetchone()[0]

    #  Extras                                                              #

    def delete(self, name: str) -> None:
        """Remove all data for the given index from every ``lucis_*`` table."""
        cur = self.conn.cursor()
        for table in (
            "lucis_inverted_index",
            "lucis_doc_vectors",
            "lucis_id_mapping",
            "lucis_doc_lengths",
            "lucis_metadata",
        ):
            cur.execute(f"DELETE FROM {table} WHERE index_name = ?", (name,))
        self.conn.commit()

    def list_indices(self):
        """Return a list of all index names stored in the database."""
        cur = self.conn.cursor()
        cur.execute("SELECT index_name FROM lucis_metadata ORDER BY index_name")
        return [row[0] for row in cur.fetchall()]

    def close(self) -> None:
        """Close the connection **only** if we own it."""
        if self._owns_connection:
            self.conn.close()

    def __del__(self):
        try:
            self.close()
        except Exception:
            pass

    def __repr__(self) -> str:
        return f"SQLiteStorage(db_path='{self.db_path}')"
