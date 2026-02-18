"""
Production storage backend powered by SQLAlchemy.

Supports any database that SQLAlchemy supports (MySQL, PostgreSQL,
MariaDB, Oracle, SQL Server, etc.) through a unified interface.

Requires the ``sqlalchemy`` extra::

    pip install lucis[alchemy]

For MySQL you also need a driver::

    pip install pymysql        # pure-Python, recommended
    pip install mysqlclient    # C-extension, faster

For PostgreSQL::

    pip install psycopg2-binary
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional, Union

try:
    from sqlalchemy import (
        create_engine,
        MetaData,
        Table,
        Column,
        String,
        Integer,
        Float,
        Text,
        Index,
        text as sa_text,
        inspect,
        select,
        delete,
    )
    from sqlalchemy.engine import Engine, Connection
    from sqlalchemy.orm import Session

    HAS_SQLALCHEMY = True
except ImportError:  # pragma: no cover
    HAS_SQLALCHEMY = False

from .base import BaseStorage


def _require_sqlalchemy() -> None:
    """Raise a friendly error if SQLAlchemy is not installed."""
    if not HAS_SQLALCHEMY:
        raise ImportError(
            "AlchemyStorage requires SQLAlchemy. "
            "Install it with:  pip install lucis[alchemy]\n"
            "For MySQL add:    pip install pymysql\n"
            "For PostgreSQL:   pip install psycopg2-binary"
        )


class AlchemyStorage(BaseStorage):
    """
    Production storage backend using SQLAlchemy.

    Connects to any SQL database supported by SQLAlchemy and creates
    the necessary ``lucis_*`` tables to persist search indices.
    All Lucis tables are prefixed with ``lucis_`` so they never
    collide with the user's own tables.

    Two modes of operation:
        1. **Index**: read user data, build the index, persist it.
        2. **Load**: read previously-persisted index tables (skip recomputation).

    Args:
        url: SQLAlchemy connection URL, e.g.
            ``"mysql+pymysql://user:pass@localhost/mydb"`` or
            ``"postgresql+psycopg2://user:pass@localhost/mydb"``.
        engine: An existing ``sqlalchemy.engine.Engine`` instance.
            If provided, *url* is ignored.
        connect_args: Extra keyword arguments forwarded to
            ``create_engine`` (e.g. ``{"charset": "utf8mb4"}``).

    Note:
        You must provide **either** *url* **or** *engine*, not both.

    Example – MySQL with PyMySQL::

        storage = AlchemyStorage(
            url="mysql+pymysql://root:secret@localhost:3306/my_app"
        )
        storage.save(engine_state, "articles_idx")
        state = storage.load("articles_idx")

    Example – PostgreSQL::

        storage = AlchemyStorage(
            url="postgresql+psycopg2://postgres:secret@localhost/my_app"
        )

    Example – shared engine::

        from sqlalchemy import create_engine
        sa_engine = create_engine("mysql+pymysql://root:s@localhost/app")
        storage = AlchemyStorage(engine=sa_engine)
    """

    def __init__(
        self,
        url: Optional[str] = None,
        engine: Optional[Any] = None,
        connect_args: Optional[Dict[str, Any]] = None,
    ):
        _require_sqlalchemy()

        if engine is not None:
            self._engine: Engine = engine
            self._owns_engine = False
        elif url is not None:
            kwargs: Dict[str, Any] = {}
            if connect_args:
                kwargs["connect_args"] = connect_args
            # pool_pre_ping ensures stale connections are recycled
            self._engine = create_engine(url, pool_pre_ping=True, **kwargs)
            self._owns_engine = True
        else:
            raise ValueError(
                "AlchemyStorage requires either a 'url' or an 'engine'. "
                "Example url: 'mysql+pymysql://user:pass@localhost/mydb'"
            )

        self.url = url or str(self._engine.url)

        # Define table schemas using SQLAlchemy Core
        self._metadata = MetaData()
        self._define_tables()
        # Create tables if they don't exist (safe, idempotent)
        self._metadata.create_all(self._engine)

    # Table definitions

    def _define_tables(self) -> None:
        """Define all ``lucis_*`` tables using SQLAlchemy Core."""

        self._t_metadata = Table(
            "lucis_metadata",
            self._metadata,
            Column("index_name", String(255), primary_key=True),
            Column("total_docs", Integer, nullable=False),
            Column("id_type", String(50), nullable=False),
            Column("engine_name", String(100), nullable=False),
            Column("source_table", String(255), nullable=True),
            Column("source_column", String(255), nullable=True),
            Column("source_id_column", String(255), nullable=True),
            Column("source_query", Text, nullable=True),
            Column("source_where", Text, nullable=True),
        )

        self._t_inverted_index = Table(
            "lucis_inverted_index",
            self._metadata,
            Column("index_name", String(255), nullable=False),
            Column("word", String(255), nullable=False),
            Column("doc_internal_id", Integer, nullable=False),
            Column("frequency", Integer, nullable=False),
        )
        # Composite primary key + indexes for fast lookups
        Index(
            "pk_lucis_inv",
            self._t_inverted_index.c.index_name,
            self._t_inverted_index.c.word,
            self._t_inverted_index.c.doc_internal_id,
            unique=True,
        )
        Index(
            "idx_lucis_inv_word",
            self._t_inverted_index.c.index_name,
            self._t_inverted_index.c.word,
        )
        Index(
            "idx_lucis_inv_doc",
            self._t_inverted_index.c.index_name,
            self._t_inverted_index.c.doc_internal_id,
        )

        self._t_doc_vectors = Table(
            "lucis_doc_vectors",
            self._metadata,
            Column("index_name", String(255), nullable=False),
            Column("doc_internal_id", Integer, nullable=False),
            Column("word", String(255), nullable=False),
            Column("tfidf_score", Float, nullable=False),
        )
        Index(
            "pk_lucis_vec",
            self._t_doc_vectors.c.index_name,
            self._t_doc_vectors.c.doc_internal_id,
            self._t_doc_vectors.c.word,
            unique=True,
        )
        Index(
            "idx_lucis_vec_doc",
            self._t_doc_vectors.c.index_name,
            self._t_doc_vectors.c.doc_internal_id,
        )

        self._t_id_mapping = Table(
            "lucis_id_mapping",
            self._metadata,
            Column("index_name", String(255), nullable=False),
            Column("internal_id", Integer, nullable=False),
            Column("original_id", String(255), nullable=False),
        )
        Index(
            "pk_lucis_idmap",
            self._t_id_mapping.c.index_name,
            self._t_id_mapping.c.internal_id,
            unique=True,
        )

        self._t_doc_lengths = Table(
            "lucis_doc_lengths",
            self._metadata,
            Column("index_name", String(255), nullable=False),
            Column("doc_internal_id", Integer, nullable=False),
            Column("length", Integer, nullable=False),
        )
        Index(
            "pk_lucis_doclen",
            self._t_doc_lengths.c.index_name,
            self._t_doc_lengths.c.doc_internal_id,
            unique=True,
        )

        self._t_aliases = Table(
            "lucis_aliases",
            self._metadata,
            Column("alias_name", String(255), primary_key=True),
            Column("target_index", String(255), nullable=False),
        )

    # BaseStorage interface 

    def save(self, data: Dict[str, Any], name: str) -> None:
        """
        Persist the engine state into the ``lucis_*`` tables.

        ``data`` is the bundle produced by ``CoreEngine.persist()`` and
        contains the keys: *index*, *doc_vectors*, *id_map*, *doc_lengths*,
        *total_docs*, *id_type*.
        """
        with self._engine.begin() as conn:
            # 1. Metadata — upsert (delete + insert for portability)
            conn.execute(
                delete(self._t_metadata).where(
                    self._t_metadata.c.index_name == name
                )
            )
            conn.execute(
                self._t_metadata.insert().values(
                    index_name=name,
                    total_docs=data["total_docs"],
                    id_type=data["id_type"],
                    engine_name="CoreEngine",
                )
            )

            # 2. Wipe previous data for this index
            for table in (
                self._t_inverted_index,
                self._t_doc_vectors,
                self._t_id_mapping,
                self._t_doc_lengths,
            ):
                conn.execute(
                    delete(table).where(table.c.index_name == name)
                )

            # 3. Inverted index
            inv_rows = [
                {
                    "index_name": name,
                    "word": word,
                    "doc_internal_id": int(doc_id),
                    "frequency": freq,
                }
                for word, docs in data["index"].items()
                for doc_id, freq in docs.items()
            ]
            if inv_rows:
                conn.execute(self._t_inverted_index.insert(), inv_rows)

            # 4. TF-IDF document vectors
            vec_rows = [
                {
                    "index_name": name,
                    "doc_internal_id": int(doc_id),
                    "word": word,
                    "tfidf_score": score,
                }
                for doc_id, vector in data["doc_vectors"].items()
                for word, score in vector.items()
            ]
            if vec_rows:
                conn.execute(self._t_doc_vectors.insert(), vec_rows)

            # 5. ID mapping (internal → original)
            id_rows = [
                {
                    "index_name": name,
                    "internal_id": int(internal_id),
                    "original_id": str(original_id),
                }
                for internal_id, original_id in data["id_map"].items()
            ]
            if id_rows:
                conn.execute(self._t_id_mapping.insert(), id_rows)

            # 6. Document lengths
            len_rows = [
                {
                    "index_name": name,
                    "doc_internal_id": int(doc_id),
                    "length": length,
                }
                for doc_id, length in data["doc_lengths"].items()
            ]
            if len_rows:
                conn.execute(self._t_doc_lengths.insert(), len_rows)

    def load(self, name: str) -> Dict[str, Any]:
        """
        Reconstruct an engine state dict from the ``lucis_*`` tables.

        The returned dict has the same shape that ``CoreEngine.load_engine``
        expects: *index*, *doc_vectors*, *id_map*, *doc_lengths*,
        *total_docs*, *id_type*.
        """
        with self._engine.connect() as conn:
            # 1. Metadata
            row = conn.execute(
                select(
                    self._t_metadata.c.total_docs,
                    self._t_metadata.c.id_type,
                ).where(self._t_metadata.c.index_name == name)
            ).fetchone()

            if row is None:
                raise FileNotFoundError(
                    f"Index '{name}' not found in database"
                )
            total_docs, id_type = row

            # 2. Inverted index
            rows = conn.execute(
                select(
                    self._t_inverted_index.c.word,
                    self._t_inverted_index.c.doc_internal_id,
                    self._t_inverted_index.c.frequency,
                ).where(self._t_inverted_index.c.index_name == name)
            ).fetchall()

            index: Dict[str, Dict[int, int]] = {}
            for word, doc_id, freq in rows:
                index.setdefault(word, {})[doc_id] = freq

            # 3. Document vectors
            rows = conn.execute(
                select(
                    self._t_doc_vectors.c.doc_internal_id,
                    self._t_doc_vectors.c.word,
                    self._t_doc_vectors.c.tfidf_score,
                ).where(self._t_doc_vectors.c.index_name == name)
            ).fetchall()

            doc_vectors: Dict[int, Dict[str, float]] = {}
            for doc_id, word, score in rows:
                doc_vectors.setdefault(doc_id, {})[word] = score

            # 4. ID mapping
            rows = conn.execute(
                select(
                    self._t_id_mapping.c.internal_id,
                    self._t_id_mapping.c.original_id,
                ).where(self._t_id_mapping.c.index_name == name)
            ).fetchall()

            id_map: Dict[int, Any] = {}
            for internal_id, original_id in rows:
                if id_type == "sequential":
                    id_map[internal_id] = int(original_id)
                else:
                    id_map[internal_id] = original_id

            # 5. Document lengths
            rows = conn.execute(
                select(
                    self._t_doc_lengths.c.doc_internal_id,
                    self._t_doc_lengths.c.length,
                ).where(self._t_doc_lengths.c.index_name == name)
            ).fetchall()

            doc_lengths: Dict[int, int] = {
                doc_id: length for doc_id, length in rows
            }

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
        with self._engine.connect() as conn:
            row = conn.execute(
                select(self._t_metadata.c.index_name)
                .where(self._t_metadata.c.index_name == resolved)
                .limit(1)
            ).fetchone()
        return row is not None

    # Extras 

    def delete(self, name: str) -> None:
        """Remove all data for the given index from every ``lucis_*`` table."""
        with self._engine.begin() as conn:
            for table in (
                self._t_inverted_index,
                self._t_doc_vectors,
                self._t_id_mapping,
                self._t_doc_lengths,
                self._t_metadata,
            ):
                conn.execute(
                    delete(table).where(table.c.index_name == name)
                )

    def list_indices(self):
        """Return a list of all index names stored in the database."""
        with self._engine.connect() as conn:
            rows = conn.execute(
                select(self._t_metadata.c.index_name).order_by(
                    self._t_metadata.c.index_name
                )
            ).fetchall()
        return [row[0] for row in rows]

    # Alias / versioning support

    def resolve_alias(self, name: str) -> str:
        """Resolve *name* to a physical index name.

        If *name* is a registered alias, return its target.
        Otherwise return *name* unchanged.
        """
        target = self.get_alias(name)
        return target if target is not None else name

    def set_alias(self, alias_name: str, target_index: str) -> None:
        """Create or update an alias → target mapping (atomic)."""
        with self._engine.begin() as conn:
            conn.execute(
                delete(self._t_aliases).where(
                    self._t_aliases.c.alias_name == alias_name
                )
            )
            conn.execute(
                self._t_aliases.insert().values(
                    alias_name=alias_name,
                    target_index=target_index,
                )
            )

    def get_alias(self, alias_name: str) -> Optional[str]:
        """Return the physical index name for *alias_name*, or ``None``."""
        with self._engine.connect() as conn:
            row = conn.execute(
                select(self._t_aliases.c.target_index).where(
                    self._t_aliases.c.alias_name == alias_name
                )
            ).fetchone()
        return row[0] if row else None

    def list_aliases(self) -> Dict[str, str]:
        """Return all aliases as ``{alias_name: target_index}``."""
        with self._engine.connect() as conn:
            rows = conn.execute(
                select(
                    self._t_aliases.c.alias_name,
                    self._t_aliases.c.target_index,
                ).order_by(self._t_aliases.c.alias_name)
            ).fetchall()
        return {row[0]: row[1] for row in rows}

    def delete_alias(self, alias_name: str) -> None:
        """Remove an alias (does NOT delete the physical index)."""
        with self._engine.begin() as conn:
            conn.execute(
                delete(self._t_aliases).where(
                    self._t_aliases.c.alias_name == alias_name
                )
            )

    def _generate_versioned_name(self, base_name: str) -> str:
        """Return ``base_name__vYYYYMMDD_HHMMSS``."""
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"{base_name}__v{ts}"

    def list_versions(self, base_name: str) -> list:
        """Return all physical versions of *base_name*, sorted oldest → newest."""
        with self._engine.connect() as conn:
            rows = conn.execute(
                select(self._t_metadata.c.index_name)
                .where(self._t_metadata.c.index_name.like(f"{base_name}__v%"))
                .order_by(self._t_metadata.c.index_name)
            ).fetchall()
        return [row[0] for row in rows]

    # Source-info persistence (smart worker support)

    def save_source_info(self, name: str, info: Dict[str, Any]) -> None:
        """Persist data-source metadata into ``lucis_metadata``."""
        with self._engine.begin() as conn:
            conn.execute(
                self._t_metadata.update()
                .where(self._t_metadata.c.index_name == name)
                .values(
                    source_table=info.get("table_name"),
                    source_column=info.get("text_column"),
                    source_id_column=info.get("id_column"),
                    source_query=info.get("query"),
                    source_where=info.get("where_clause"),
                )
            )

    def load_source_info(self, name: str) -> Optional[Dict[str, Any]]:
        """Load source metadata from ``lucis_metadata``."""
        with self._engine.connect() as conn:
            row = conn.execute(
                select(
                    self._t_metadata.c.source_table,
                    self._t_metadata.c.source_column,
                    self._t_metadata.c.source_id_column,
                    self._t_metadata.c.source_query,
                    self._t_metadata.c.source_where,
                ).where(self._t_metadata.c.index_name == name)
            ).fetchone()

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
        with self._engine.connect() as conn:
            result = conn.execute(
                sa_text(f"SELECT COUNT(*) FROM {table_name}")
            )
            return result.scalar()

    # Read helpers

    def read_table(
        self,
        table_name: str,
        text_column: str,
        id_column: Optional[str] = None,
        where_clause: Optional[str] = None,
        schema: Optional[str] = None,
    ) -> Union[Dict[str, str], list[str]]:
        """
        Read rows from an existing user table and return them in
        a format ready for ``Lucis.index()``.

        This is a convenience helper so users don't have to write raw SQL.

        Args:
            table_name: Name of the source table.
            text_column: Column that contains the document text.
            id_column: Column to use as document ID (optional).
                If ``None``, results are returned as a ``list[str]``.
            where_clause: Optional SQL ``WHERE`` filter
                (without the ``WHERE`` keyword).
            schema: Database schema (e.g. ``"public"`` for PostgreSQL).

        Returns:
            ``Dict[str, str]`` if *id_column* is given, else ``list[str]``.

        Example::

            storage = AlchemyStorage(url="mysql+pymysql://…")
            data = storage.read_table(
                "articles", text_column="content", id_column="article_id"
            )
            luc = Lucis(name="articles_idx", storage=storage)
            luc.index(data)
        """
        # Reflect the user table from the database
        user_meta = MetaData()
        user_table = Table(
            table_name, user_meta, autoload_with=self._engine, schema=schema
        )

        if id_column:
            cols = [user_table.c[id_column], user_table.c[text_column]]
        else:
            cols = [user_table.c[text_column]]

        stmt = select(*cols)
        if where_clause:
            stmt = stmt.where(sa_text(where_clause))

        with self._engine.connect() as conn:
            rows = conn.execute(stmt).fetchall()

        if id_column:
            return {str(row[0]): row[1] for row in rows}
        else:
            return [row[0] for row in rows]

    def read_query(
        self,
        query: str,
    ) -> Union[Dict[str, str], list[str]]:
        """
        Execute an arbitrary SQL ``SELECT`` and return Lucis-ready data.

        * If the query returns **one** column → ``list[str]``.
        * If it returns **two or more** columns → first column is the ID,
          second column is the text → ``Dict[str, str]``.

        Args:
            query: A raw ``SELECT`` statement.

        Returns:
            Data ready for ``Lucis.index()``.

        Example::

            data = storage.read_query(
                "SELECT id, title || ' ' || body FROM posts WHERE published = 1"
            )
        """
        with self._engine.connect() as conn:
            result = conn.execute(sa_text(query))
            rows = result.fetchall()

        if not rows:
            raise ValueError("The query returned no results.")

        if len(rows[0]) == 1:
            return [row[0] for row in rows]
        else:
            return {str(row[0]): row[1] for row in rows}

    def close(self) -> None:
        """Dispose of the engine's connection pool (only if we own it)."""
        if self._owns_engine:
            self._engine.dispose()

    def __del__(self):
        try:
            self.close()
        except Exception:
            pass

    def __repr__(self) -> str:
        # Mask password in URL for safety
        url = str(self._engine.url)
        return f"AlchemyStorage(url='{url}')"
