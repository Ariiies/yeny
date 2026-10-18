# src/yeny/storage/sqlite_storage.py
import sqlite3

from ..utils.serialization import dumps as _dumps, loads as _loads
from datetime import datetime
from typing import Any, Dict, Optional
from .base import BaseStorage


class SQLiteStorage(BaseStorage):
    """
    Production storage backend using SQLite.

    Connects to an existing (or new) SQLite database and creates
    the necessary ``yeny_*`` tables to persist search indices.
    All Yeny tables are prefixed with ``yeny_`` so they never
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
        """Create the ``yeny_*`` tables if they don't already exist."""
        cur = self.conn.cursor()

        cur.execute("""
            CREATE TABLE IF NOT EXISTS yeny_metadata (
                index_name      TEXT PRIMARY KEY,
                total_docs      INTEGER NOT NULL,
                id_type         TEXT NOT NULL,
                engine_name     TEXT NOT NULL,
                source_table    TEXT,
                source_column   TEXT,
                source_id_column TEXT,
                source_date_column TEXT,
                source_query    TEXT,
                source_where    TEXT,
                created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS yeny_inverted_index (
                index_name      TEXT    NOT NULL,
                word            TEXT    NOT NULL,
                postings        TEXT    NOT NULL,
                PRIMARY KEY (index_name, word),
                FOREIGN KEY (index_name) REFERENCES yeny_metadata(index_name)
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS yeny_doc_vectors (
                index_name      TEXT    NOT NULL,
                doc_internal_id INTEGER NOT NULL,
                vector          TEXT    NOT NULL,
                PRIMARY KEY (index_name, doc_internal_id),
                FOREIGN KEY (index_name) REFERENCES yeny_metadata(index_name)
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS yeny_id_mapping (
                index_name  TEXT    NOT NULL,
                internal_id INTEGER NOT NULL,
                original_id TEXT    NOT NULL,
                PRIMARY KEY (index_name, internal_id),
                FOREIGN KEY (index_name) REFERENCES yeny_metadata(index_name)
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS yeny_doc_lengths (
                index_name      TEXT    NOT NULL,
                doc_internal_id INTEGER NOT NULL,
                length          INTEGER NOT NULL,
                PRIMARY KEY (index_name, doc_internal_id),
                FOREIGN KEY (index_name) REFERENCES yeny_metadata(index_name)
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS yeny_aliases (
                alias_name      TEXT PRIMARY KEY,
                target_index    TEXT NOT NULL
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS yeny_shard_registry (
                index_name  TEXT NOT NULL,
                shard_key   TEXT NOT NULL,
                PRIMARY KEY (index_name, shard_key)
            )
        """)

        self.conn.commit()

    #  BaseStorage interface          
                                       
    def save(self, data: Dict[str, Any], name: str) -> None:
        """
        Persist the engine state into the ``yeny_*`` tables.

        ``data`` is the bundle produced by ``BaseEngine.persist()`` and
        contains the keys: *index*, *doc_vectors*, *id_map*, *doc_lengths*,
        *total_docs*, *id_type*.

        Args:
            data: Engine-state dict to persist.
            name: Physical index name (storage key).

        Raises:
            RuntimeError: If the write fails (transaction is rolled back
                automatically).
        """
        cur = self.conn.cursor()

        try:
            # 1. Metadata 
            cur.execute("""
                INSERT OR REPLACE INTO yeny_metadata
                    (index_name, total_docs, id_type, engine_name, updated_at)
                VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (name, data["total_docs"], data["id_type"], data.get("engine_name", "CoreEngine")))

            # 2. Wipe previous data for this index 
            for table in (
                "yeny_inverted_index",
                "yeny_doc_vectors",
                "yeny_id_mapping",
                "yeny_doc_lengths",
            ):
                cur.execute(f"DELETE FROM {table} WHERE index_name = ?", (name,))

            # 3. Inverted index (one row per word, postings as JSON)
            inv_rows = [
                (
                    name,
                    word,
                    _dumps(
                        {int(doc_id): freq for doc_id, freq in docs.items()}
                    ),
                )
                for word, docs in data["index"].items()
            ]
            cur.executemany(
                "INSERT INTO yeny_inverted_index VALUES (?, ?, ?)",
                inv_rows,
            )

            # 4. TF-IDF document vectors (one row per doc, vector as JSON)
            #    Optional: LiteEngine does not produce doc_vectors
            doc_vectors = data.get("doc_vectors", {})
            if doc_vectors:
                vec_rows = [
                    (name, int(doc_id), _dumps(vector))
                    for doc_id, vector in doc_vectors.items()
                ]
                cur.executemany(
                    "INSERT INTO yeny_doc_vectors VALUES (?, ?, ?)",
                    vec_rows,
                )

            # 5. ID mapping (internal → original) 
            id_rows = [
                (name, int(internal_id), str(original_id))
                for internal_id, original_id in data["id_map"].items()
            ]
            cur.executemany(
                "INSERT INTO yeny_id_mapping VALUES (?, ?, ?)",
                id_rows,
            )

            # 6. Document lengths 
            len_rows = [
                (name, int(doc_id), length)
                for doc_id, length in data["doc_lengths"].items()
            ]
            cur.executemany(
                "INSERT INTO yeny_doc_lengths VALUES (?, ?, ?)",
                len_rows,
            )

            self.conn.commit()

        except Exception as exc:
            self.conn.rollback()
            raise RuntimeError(f"Failed to save index '{name}': {exc}") from exc

    def load(self, name: str) -> Dict[str, Any]:
        """
        Reconstruct an engine state dict from the ``yeny_*`` tables.

        The returned dict has the same shape that ``BaseEngine.load_engine``
        expects: *index*, *doc_vectors*, *id_map*, *doc_lengths*,
        *total_docs*, *id_type*.

        Args:
            name: Physical index name (same key used in :meth:`save`).

        Returns:
            Engine-state dict ready to be passed to ``BaseEngine.load_engine``.

        Raises:
            FileNotFoundError: If *name* is not found in ``yeny_metadata``.
        """
        cur = self.conn.cursor()

        # 1. Metadata 
        cur.execute(
            "SELECT total_docs, id_type FROM yeny_metadata WHERE index_name = ?",
            (name,),
        )
        meta = cur.fetchone()
        if meta is None:
            raise FileNotFoundError(f"Index '{name}' not found in database")
        total_docs, id_type = meta

        # 2. Inverted index (one row per word, JSON postings)
        cur.execute(
            "SELECT word, postings "
            "FROM yeny_inverted_index WHERE index_name = ?",
            (name,),
        )
        index: Dict[str, Dict[int, int]] = {}
        for word, postings_json in cur.fetchall():
            index[word] = {
                int(k): v for k, v in _loads(postings_json).items()
            }

        # 3. Document vectors (one row per doc, JSON vector)
        cur.execute(
            "SELECT doc_internal_id, vector "
            "FROM yeny_doc_vectors WHERE index_name = ?",
            (name,),
        )
        doc_vectors: Dict[int, Dict[str, float]] = {}
        for doc_id, vector_json in cur.fetchall():
            doc_vectors[doc_id] = _loads(vector_json)

        # 4. ID mapping 
        cur.execute(
            "SELECT internal_id, original_id "
            "FROM yeny_id_mapping WHERE index_name = ?",
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
            "FROM yeny_doc_lengths WHERE index_name = ?",
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
        2. Is *name* itself a physical index in ``yeny_metadata``?

        Args:
            name: Logical alias or physical index name to check.

        Returns:
            ``True`` if the index (or its alias target) exists in
            ``yeny_metadata``.
        """
        resolved = self.resolve_alias(name)
        cur = self.conn.cursor()
        cur.execute(
            "SELECT 1 FROM yeny_metadata WHERE index_name = ? LIMIT 1",
            (resolved,),
        )
        return cur.fetchone() is not None

    #  Alias / versioning support                                         #

    def resolve_alias(self, name: str) -> str:
        """Resolve *name* to a physical index name.

        If *name* is a registered alias, return its target.
        Otherwise return *name* unchanged.

        Args:
            name: Logical alias or physical index name.

        Returns:
            Physical index name the alias points to, or *name* if it
            is not a registered alias.
        """
        target = self.get_alias(name)
        return target if target is not None else name

    def set_alias(self, alias_name: str, target_index: str) -> None:
        """Create or update an alias → target mapping.

        Args:
            alias_name: Logical name users reference the index by.
            target_index: Physical versioned name the alias points to.
        """
        cur = self.conn.cursor()
        cur.execute(
            "INSERT OR REPLACE INTO yeny_aliases (alias_name, target_index) "
            "VALUES (?, ?)",
            (alias_name, target_index),
        )
        self.conn.commit()

    def get_alias(self, alias_name: str) -> Optional[str]:
        """Return the physical index name for *alias_name*.

        Args:
            alias_name: The logical alias to look up.

        Returns:
            Physical index name the alias points to, or ``None`` if
            *alias_name* is not registered.
        """
        cur = self.conn.cursor()
        cur.execute(
            "SELECT target_index FROM yeny_aliases WHERE alias_name = ?",
            (alias_name,),
        )
        row = cur.fetchone()
        return row[0] if row else None

    def list_aliases(self) -> Dict[str, str]:
        """Return all registered aliases.

        Returns:
            ``{alias_name: target_index}`` dict sorted by alias name.
        """
        cur = self.conn.cursor()
        cur.execute(
            "SELECT alias_name, target_index FROM yeny_aliases ORDER BY alias_name"
        )
        return {row[0]: row[1] for row in cur.fetchall()}

    def delete_alias(self, alias_name: str) -> None:
        """Remove an alias (does **not** delete the physical index).

        Args:
            alias_name: The alias to remove.
        """
        cur = self.conn.cursor()
        cur.execute(
            "DELETE FROM yeny_aliases WHERE alias_name = ?",
            (alias_name,),
        )
        self.conn.commit()

    def _generate_versioned_name(self, base_name: str) -> str:
        """Return ``base_name__vYYYYMMDD_HHMMSS``."""
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"{base_name}__v{ts}"

    def list_versions(self, base_name: str) -> list:
        """Return all physical versions of *base_name*, sorted oldest → newest.

        Shard entries (``__shard__``) are excluded — only parent
        version names are returned.

        Args:
            base_name: The logical/alias name whose versions to list.

        Returns:
            Sorted list of versioned physical names, e.g.
            ``["articles__v20260210_143022", "articles__v20260210_150545"]``.
        """
        cur = self.conn.cursor()
        cur.execute(
            "SELECT index_name FROM yeny_metadata "
            "WHERE index_name LIKE ? AND index_name NOT LIKE '%__shard__%' "
            "ORDER BY index_name",
            (f"{base_name}__v%",),
        )
        return [row[0] for row in cur.fetchall()]

    #  Source-info persistence (smart worker support)                       #

    def save_source_info(self, name: str, info: Dict[str, Any]) -> None:
        """Persist data-source metadata into ``yeny_metadata``.

        Args:
            name: Physical index name to associate the metadata with.
            info: Source-info dict with keys such as ``type``,
                ``table``, ``text_columns`` (str or list),
                ``id_column``, ``date_column``, ``where_clause``,
                and ``query``.
        """
        import json as _json
        text_col = info.get("text_columns")
        # Multi-column: serialize as JSON list; single column: plain string
        source_column = _json.dumps(text_col) if isinstance(text_col, list) else text_col
        cur = self.conn.cursor()
        cur.execute(
            "UPDATE yeny_metadata "
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
        """Load source metadata from ``yeny_metadata``.

        Args:
            name: Physical index name whose metadata to retrieve.

        Returns:
            Source-info dict (see :meth:`save_source_info` for key
            descriptions), or ``None`` if no metadata was stored.
        """
        cur = self.conn.cursor()
        cur.execute(
            "SELECT source_table, source_column, source_id_column, "
            "source_date_column, source_query, source_where "
            "FROM yeny_metadata WHERE index_name = ?",
            (name,),
        )
        row = cur.fetchone()
        if row is None:
            return None

        (source_table, source_column, source_id_column,
         source_date_column, source_query, source_where) = row

        # Deserialize text_column: JSON list for multi-column, plain string for single
        import json as _json
        try:
            parsed_col = _json.loads(source_column) if source_column else source_column
            text_column = parsed_col if isinstance(parsed_col, list) else source_column
        except (TypeError, ValueError):
            text_column = source_column

        # Query-based source
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

        # Table-based source
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

    def count_rows(self, table_name: str) -> Optional[int]:
        """Return ``SELECT COUNT(*) FROM <table_name>``.

        Args:
            table_name: Name of the user table to count rows in.

        Returns:
            Integer row count.
        """
        cur = self.conn.cursor()
        cur.execute(f"SELECT COUNT(*) FROM {table_name}")
        return cur.fetchone()[0]

    # Shard support (temporal partitioning)

    def save_shard_registry(self, index_name: str, shard_keys: list) -> None:
        """Persist the shard keys for a sharded index.

        Args:
            index_name: The versioned physical name of the parent index.
            shard_keys: List of shard keys to register
                (e.g. ``["2026_01", "9999_99"]``).
        """
        cur = self.conn.cursor()
        cur.execute(
            "DELETE FROM yeny_shard_registry WHERE index_name = ?",
            (index_name,),
        )
        if shard_keys:
            cur.executemany(
                "INSERT INTO yeny_shard_registry (index_name, shard_key) "
                "VALUES (?, ?)",
                [(index_name, key) for key in shard_keys],
            )
        self.conn.commit()

    def load_shard_registry(self, index_name: str) -> list:
        """Return shard keys for *index_name*, sorted.

        Args:
            index_name: The versioned physical name of the parent index.

        Returns:
            Sorted list of shard keys.  An empty list means the index
            is monolithic (not sharded).
        """
        cur = self.conn.cursor()
        cur.execute(
            "SELECT shard_key FROM yeny_shard_registry "
            "WHERE index_name = ? ORDER BY shard_key",
            (index_name,),
        )
        return [row[0] for row in cur.fetchall()]

    #  Extras                                                              #

    def delete(self, name: str) -> None:
        """Remove all data for *name* from every ``yeny_*`` table.

        If the index is sharded, all child shard entries and the shard
        registry are cleaned up automatically.

        Args:
            name: Physical index name to delete. Aliases pointing to
                this name are **not** removed automatically.
        """
        shard_keys = self.load_shard_registry(name)
        cur = self.conn.cursor()

        # Delete shard children first
        for key in shard_keys:
            shard_name = f"{name}__shard__{key}"
            for table in (
                "yeny_inverted_index",
                "yeny_doc_vectors",
                "yeny_id_mapping",
                "yeny_doc_lengths",
                "yeny_metadata",
            ):
                cur.execute(f"DELETE FROM {table} WHERE index_name = ?", (shard_name,))

        # Delete shard registry
        if shard_keys:
            cur.execute(
                "DELETE FROM yeny_shard_registry WHERE index_name = ?",
                (name,),
            )

        # Delete parent / main entry
        for table in (
            "yeny_inverted_index",
            "yeny_doc_vectors",
            "yeny_id_mapping",
            "yeny_doc_lengths",
            "yeny_metadata",
        ):
            cur.execute(f"DELETE FROM {table} WHERE index_name = ?", (name,))
        self.conn.commit()

    def list_indices(self):
        """Return a sorted list of all index names stored in the database.

        Returns:
            List of physical index names (excludes aliases).
        """
        cur = self.conn.cursor()
        cur.execute("SELECT index_name FROM yeny_metadata ORDER BY index_name")
        return [row[0] for row in cur.fetchall()]

    def close(self) -> None:
        """Close the SQLite connection if this instance owns it.

        When constructed with an external *connection*, closing is the
        caller's responsibility — this method is a no-op in that case.
        """
        if self._owns_connection:
            self.conn.close()

    def __del__(self):
        """Ensure the connection is released when the object is garbage-collected."""
        try:
            self.close()
        except Exception:
            pass

    def __repr__(self) -> str:
        """Return an unambiguous string identifying this storage instance."""
        return f"SQLiteStorage(db_path='{self.db_path}')"
