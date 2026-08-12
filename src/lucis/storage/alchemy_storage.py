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

import csv
import io
import logging
import os
import tempfile
from datetime import datetime
from typing import Any, Dict, Generator, List, Optional, Union

from ..utils.serialization import dumps as _dumps, loads as _loads

logger = logging.getLogger("lucis.storage.alchemy")

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
        func as sa_func,
        literal as sa_literal,
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
                kwargs["connect_args"] = dict(connect_args)
            # For MySQL/PyMySQL: enable LOAD DATA LOCAL INFILE support
            # automatically so csv_bulk_insert works out of the box.
            if "pymysql" in url:
                ca = kwargs.setdefault("connect_args", {})
                ca.setdefault("local_infile", True)
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
        # Upgrade TEXT → LONGTEXT on existing MySQL/MariaDB tables
        self._upgrade_text_columns()

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
            Column("source_date_column", String(255), nullable=True),
            Column("source_query", Text, nullable=True),
            Column("source_where", Text, nullable=True),
        )

        # utf8mb4_bin collation ensures case-sensitive exact matching on MySQL/MariaDB.
        # Other dialects (SQLite, PostgreSQL) don't support it, so we omit it there.
        _dialect = self._engine.dialect.name
        _word_col_kwargs: Dict[str, Any] = {"nullable": False}
        if _dialect in ("mysql", "mariadb"):
            _word_col = Column("word", String(255, collation="utf8mb4_bin"), **_word_col_kwargs)
        else:
            _word_col = Column("word", String(255), **_word_col_kwargs)

        self._t_inverted_index = Table(
            "lucis_inverted_index",
            self._metadata,
            Column("index_name", String(255), nullable=False),
            _word_col,
            Column("postings", Text(2**24), nullable=False),
        )
        Index(
            "pk_lucis_inv",
            self._t_inverted_index.c.index_name,
            self._t_inverted_index.c.word,
            unique=True,
        )

        self._t_doc_vectors = Table(
            "lucis_doc_vectors",
            self._metadata,
            Column("index_name", String(255), nullable=False),
            Column("doc_internal_id", Integer, nullable=False),
            Column("vector", Text(2**24), nullable=False),
        )
        Index(
            "pk_lucis_vec",
            self._t_doc_vectors.c.index_name,
            self._t_doc_vectors.c.doc_internal_id,
            unique=True,
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

        self._t_shard_registry = Table(
            "lucis_shard_registry",
            self._metadata,
            Column("index_name", String(255), nullable=False),
            Column("shard_key", String(10), nullable=False),
        )
        Index(
            "pk_lucis_shard_reg",
            self._t_shard_registry.c.index_name,
            self._t_shard_registry.c.shard_key,
            unique=True,
        )

    # Internal helpers

    def _upgrade_text_columns(self) -> None:
        """Upgrade TEXT columns to LONGTEXT on MySQL/MariaDB for existing tables.

        This is a no-op on non-MySQL backends (PostgreSQL TEXT is already
        unlimited) and safe to call multiple times.
        """
        dialect = self._engine.dialect.name
        if dialect not in ("mysql", "mariadb"):
            return
        alterations = [
            ("lucis_inverted_index", "postings"),
            ("lucis_doc_vectors", "vector"),
        ]
        with self._engine.begin() as conn:
            for table_name, col_name in alterations:
                try:
                    row = conn.execute(
                        sa_text(
                            "SELECT DATA_TYPE FROM INFORMATION_SCHEMA.COLUMNS "
                            "WHERE TABLE_SCHEMA = DATABASE() "
                            f"AND TABLE_NAME = :tbl AND COLUMN_NAME = :col"
                        ),
                        {"tbl": table_name, "col": col_name},
                    ).fetchone()
                    if row and row[0].lower() != "longtext":
                        conn.execute(
                            sa_text(
                                f"ALTER TABLE `{table_name}` "
                                f"MODIFY COLUMN `{col_name}` LONGTEXT NOT NULL"
                            )
                        )
                except Exception:
                    pass  # table may not exist yet on first run

    @staticmethod
    def _chunked_insert(
        conn: Any,
        table: Any,
        rows: Any,
        chunk_size: int = 200,
        max_payload_bytes: int = 1_000_000,
    ) -> None:
        """Insert *rows* into *table* in small batches.

        Applies **two** flush thresholds to avoid MySQL
        ``max_allowed_packet`` errors:

        1. **Row count** — at most *chunk_size* rows per batch.
        2. **Payload size** — at most *max_payload_bytes* estimated
           bytes per batch (default 1 MB, conservative to account
           for PyMySQL SQL-building overhead which can add 20-30%
           on top of raw data).

        Uses a **pre-check** pattern: before adding a new row to the
        current batch, it verifies that doing so would not exceed
        either threshold.  If it would, the current batch is flushed
        first.  This guarantees each batch stays strictly under the
        configured limits (the only exception is a single row that
        by itself exceeds *max_payload_bytes* — it is inserted alone).

        This is critical for the inverted-index table where a single
        ``postings`` JSON value can exceed 300 KB when a token appears
        in hundreds of thousands of documents.

        Accepts both lists and iterators/generators.  When a generator
        is supplied the rows are consumed lazily — only the current
        chunk is materialised in RAM.

        Args:
            conn: An active SQLAlchemy connection.
            table: SQLAlchemy ``Table`` object to insert into.
            rows: List or iterable of row dicts to insert.
            chunk_size: Maximum rows per ``INSERT`` statement.
            max_payload_bytes: Approximate byte-size cap per batch.
                Before adding a row, if accumulated data would exceed
                this threshold the batch is flushed first.  Set to
                ``0`` to disable size-based flushing.
        """

        def _estimate_row_bytes(row: dict) -> int:
            """Cheap estimate: sum of str/bytes value lengths."""
            total = 0
            for v in row.values():
                if isinstance(v, str):
                    total += len(v)
                elif isinstance(v, bytes):
                    total += len(v)
                else:
                    total += 8  # int/float/etc.
            return total

        if isinstance(rows, list):
            # Fast path for pre-built lists (id_mapping, doc_lengths — small rows)
            if max_payload_bytes <= 0:
                for i in range(0, len(rows), chunk_size):
                    conn.execute(table.insert(), rows[i : i + chunk_size])
            else:
                chunk_start = 0
                acc_bytes = 0
                for i, row in enumerate(rows):
                    row_bytes = _estimate_row_bytes(row)
                    # Pre-check: flush BEFORE adding if limits would be exceeded
                    if i > chunk_start and (
                        (i - chunk_start) >= chunk_size
                        or acc_bytes + row_bytes >= max_payload_bytes
                    ):
                        conn.execute(table.insert(), rows[chunk_start:i])
                        chunk_start = i
                        acc_bytes = 0
                    acc_bytes += row_bytes
                if chunk_start < len(rows):
                    conn.execute(table.insert(), rows[chunk_start:])
        else:
            # Streaming path for generators — never materialise full list
            chunk: list = []
            acc_bytes = 0
            for row in rows:
                row_bytes = _estimate_row_bytes(row)
                # Pre-check: flush BEFORE adding if limits would be exceeded
                if chunk and (
                    len(chunk) >= chunk_size
                    or (max_payload_bytes > 0 and acc_bytes + row_bytes >= max_payload_bytes)
                ):
                    conn.execute(table.insert(), chunk)
                    chunk = []
                    acc_bytes = 0
                chunk.append(row)
                acc_bytes += row_bytes
            if chunk:
                conn.execute(table.insert(), chunk)

    # ── CSV Bulk Insert (LOAD DATA LOCAL INFILE) ──

    @staticmethod
    def _csv_bulk_insert(
        conn: Any,
        table_name: str,
        columns: List[str],
        rows: Any,
        batch_rows: int = 50_000,
    ) -> int:
        """Bulk-insert rows via ``LOAD DATA LOCAL INFILE`` (MySQL/MariaDB).

        Writes rows to a temporary CSV file on disk, then issues a
        ``LOAD DATA LOCAL INFILE`` statement to load the file directly
        into the target table.  This bypasses the SQL parser and
        value-by-value binding, resulting in **10-50× faster** inserts
        compared to ``executemany(INSERT ...)``.

        The CSV is written in batches of *batch_rows* to limit peak
        disk usage.  Each batch is loaded and the temp file is
        truncated before writing the next batch.

        **Memory profile:** Only the current batch of rows (dicts) plus
        the temp CSV file on disk are materialised at any time.  For a
        50K-row batch with ~200-byte rows, that is ~10 MB of RAM and
        ~10 MB on disk — negligible.

        **Compatibility:**
        - Requires ``local_infile=True`` on the PyMySQL connection
          (auto-configured by ``AlchemyStorage.__init__``).
        - The MySQL server must have ``local_infile=ON`` (default on
          most installations; on managed services use the server
          parameter group / console to enable it).

        Args:
            conn: An active SQLAlchemy connection (inside a transaction).
            table_name: Target MySQL table name (e.g. ``"lucis_inverted_index"``).
            columns: Ordered list of column names matching the CSV field order.
            rows: Iterable (list or generator) of ``dict`` rows.
                  Keys must be a superset of *columns*.
            batch_rows: Max rows per temp-file batch.  Default 50 000.
                Tune down if disk space is very limited; tune up for
                maximum throughput on fast storage.

        Returns:
            Total number of rows loaded.
        """
        total_loaded = 0

        # We use a named temp file (delete=False) so the MySQL client
        # library can open it by path.  We clean up manually.
        tmp = tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".csv",
            prefix="lucis_bulk_",
            delete=False,
            newline="",
            encoding="utf-8",
        )
        tmp_path = tmp.name

        try:
            batch: List[dict] = []

            def _flush_batch() -> int:
                """Write *batch* to CSV file, LOAD DATA, return row count."""
                if not batch:
                    return 0

                # Rewind and truncate the temp file for this batch
                tmp.seek(0)
                tmp.truncate()

                writer = csv.writer(
                    tmp,
                    delimiter="\t",
                    quoting=csv.QUOTE_NONE,
                    escapechar="\\",
                    lineterminator="\n",
                )
                for row_dict in batch:
                    writer.writerow([row_dict[col] for col in columns])
                tmp.flush()

                # Build and execute LOAD DATA LOCAL INFILE
                # Use forward slashes — MySQL accepts them on all platforms.
                file_path_sql = tmp_path.replace("\\", "/")
                col_list = ", ".join(f"`{c}`" for c in columns)
                sql = (
                    f"LOAD DATA LOCAL INFILE '{file_path_sql}' "
                    f"INTO TABLE `{table_name}` "
                    f"FIELDS TERMINATED BY '\\t' "
                    f"ESCAPED BY '\\\\' "
                    f"LINES TERMINATED BY '\\n' "
                    f"({col_list})"
                )
                conn.execute(sa_text(sql))
                loaded = len(batch)
                batch.clear()
                return loaded

            for row in rows:
                batch.append(row)
                if len(batch) >= batch_rows:
                    total_loaded += _flush_batch()

            # Final flush
            total_loaded += _flush_batch()

        finally:
            tmp.close()
            try:
                os.unlink(tmp_path)
            except OSError:
                pass

        return total_loaded

    def _is_mysql(self) -> bool:
        """Return ``True`` if the backend is MySQL or MariaDB."""
        return self._engine.dialect.name in ("mysql", "mariadb")

    # Cross-field search support

    def _build_text_expr(self, table: Any, text_column: Union[str, List[str]]) -> Any:
        """Build a SQLAlchemy expression for one or more text columns.

        When *text_column* is a list of column names, the columns are
        concatenated with a space separator at the SQL level.  NULL
        values are coalesced to empty strings so they don't poison the
        result.

        Args:
            table: A reflected SQLAlchemy ``Table`` object.
            text_column: A single column name or a list of column names.

        Returns:
            A SQLAlchemy column expression suitable for ``select()``.
        """
        if isinstance(text_column, str):
            return table.c[text_column]
        if len(text_column) == 1:
            return table.c[text_column[0]]

        dialect = self._engine.dialect.name
        if dialect in ("mysql", "mariadb"):
            # CONCAT_WS handles NULLs by skipping them
            return sa_func.concat_ws(
                ' ', *[table.c[col] for col in text_column]
            )
        else:
            # PostgreSQL / SQLite: COALESCE + ||
            parts = [
                sa_func.coalesce(table.c[col], sa_literal(''))
                for col in text_column
            ]
            expr = parts[0]
            for part in parts[1:]:
                expr = expr.concat(sa_literal(' ')).concat(part)
            return expr

    def _sql_concat_columns(self, text_column: Union[str, List[str]]) -> str:
        """Return a raw SQL fragment for concatenating text columns.

        Used by auto-generated delta functions that build SQL strings
        directly (via ``sa_text()``).

        Args:
            text_column: Single column name or list of column names.

        Returns:
            A SQL expression string, e.g. ``"CONCAT_WS(' ', col1, col2)"``
            on MySQL or ``"COALESCE(col1, '') || ' ' || COALESCE(col2, '')"``
            on PostgreSQL/SQLite.
        """
        if isinstance(text_column, str):
            return text_column
        if len(text_column) == 1:
            return text_column[0]

        dialect = self._engine.dialect.name
        if dialect in ("mysql", "mariadb"):
            return f"CONCAT_WS(' ', {', '.join(text_column)})"
        else:
            coalesced = [f"COALESCE({col}, '')" for col in text_column]
            return " || ' ' || ".join(coalesced)

    # BaseStorage interface 

    def save(self, data: Dict[str, Any], name: str) -> None:
        """
        Persist the engine state into the ``lucis_*`` tables.

        ``data`` is the bundle produced by ``BaseEngine.persist()`` and
        contains the keys: *index*, *doc_vectors*, *id_map*, *doc_lengths*,
        *total_docs*, *id_type*.

        On **MySQL / MariaDB** the heavy tables (inverted index, vectors,
        id mapping, doc lengths) are loaded via ``LOAD DATA LOCAL INFILE``
        using temporary CSV files — this is **10-50× faster** than
        row-by-row ``INSERT`` statements.  If the CSV path fails for
        any reason (server policy, Docker volumes, etc.), it falls back
        transparently to the traditional ``_chunked_insert`` path.

        On all other dialects (SQLite, PostgreSQL) the ``_chunked_insert``
        path is used directly.

        Args:
            data: Engine-state dict to persist.
            name: Physical index name (storage key).

        Raises:
            sqlalchemy.exc.SQLAlchemyError: If the write fails (the
                transaction is rolled back automatically by the context
                manager).
        """
        use_csv = self._is_mysql()

        if use_csv:
            try:
                self._save_with_csv(data, name)
                return
            except Exception as exc:
                logger.warning(
                    "CSV bulk save failed (%s) — retrying with chunked INSERT.",
                    exc,
                )
                # Fall through to the chunked path below

        self._save_with_chunked_insert(data, name)

    def _save_common_header(self, conn: Any, data: Dict[str, Any], name: str) -> None:
        """Persist metadata and wipe previous index data (shared by both paths).

        Args:
            conn: An active SQLAlchemy connection inside a transaction.
            data: Engine-state dict.
            name: Physical index name.
        """
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
                engine_name=data.get("engine_name", "CoreEngine"),
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

    # ── Row generators (shared by both save paths) ──

    @staticmethod
    def _make_inv_rows(data: Dict[str, Any], name: str) -> Generator:
        """Yield inverted-index row dicts."""
        for word, docs in data["index"].items():
            yield {
                "index_name": name,
                "word": word,
                "postings": _dumps(
                    {int(doc_id): freq for doc_id, freq in docs.items()}
                ),
            }

    @staticmethod
    def _make_vec_rows(data: Dict[str, Any], name: str) -> Generator:
        """Yield doc-vector row dicts."""
        for doc_id, vector in data.get("doc_vectors", {}).items():
            yield {
                "index_name": name,
                "doc_internal_id": int(doc_id),
                "vector": _dumps(vector),
            }

    @staticmethod
    def _make_id_rows(data: Dict[str, Any], name: str) -> Generator:
        """Yield id-mapping row dicts."""
        for internal_id, original_id in data["id_map"].items():
            yield {
                "index_name": name,
                "internal_id": int(internal_id),
                "original_id": str(original_id),
            }

    @staticmethod
    def _make_len_rows(data: Dict[str, Any], name: str) -> Generator:
        """Yield doc-length row dicts."""
        for doc_id, length in data["doc_lengths"].items():
            yield {
                "index_name": name,
                "doc_internal_id": int(doc_id),
                "length": length,
            }

    # ── CSV bulk path (MySQL / MariaDB) ──

    def _save_with_csv(self, data: Dict[str, Any], name: str) -> None:
        """Persist engine state using ``LOAD DATA LOCAL INFILE``.

        This path is **10-50× faster** than row-by-row INSERTs for
        large indices.  The entire save is wrapped in a single
        transaction so partial failures are rolled back cleanly.

        Args:
            data: Engine-state dict.
            name: Physical index name.
        """
        with self._engine.begin() as conn:
            self._save_common_header(conn, data, name)

            # 3. Inverted index
            inv_cols = ["index_name", "word", "postings"]
            n_inv = self._csv_bulk_insert(
                conn, "lucis_inverted_index", inv_cols,
                self._make_inv_rows(data, name),
            )
            logger.info("CSV bulk: %d inverted-index rows → %s", n_inv, name)

            # 4. Doc vectors (optional — LiteEngine omits them)
            if data.get("doc_vectors"):
                vec_cols = ["index_name", "doc_internal_id", "vector"]
                n_vec = self._csv_bulk_insert(
                    conn, "lucis_doc_vectors", vec_cols,
                    self._make_vec_rows(data, name),
                )
                logger.info("CSV bulk: %d doc-vector rows → %s", n_vec, name)

            # 5. ID mapping
            id_cols = ["index_name", "internal_id", "original_id"]
            n_id = self._csv_bulk_insert(
                conn, "lucis_id_mapping", id_cols,
                self._make_id_rows(data, name),
            )
            logger.info("CSV bulk: %d id-mapping rows → %s", n_id, name)

            # 6. Doc lengths
            len_cols = ["index_name", "doc_internal_id", "length"]
            n_len = self._csv_bulk_insert(
                conn, "lucis_doc_lengths", len_cols,
                self._make_len_rows(data, name),
            )
            logger.info("CSV bulk: %d doc-length rows → %s", n_len, name)

    # ── Chunked INSERT path (universal fallback) ──

    def _save_with_chunked_insert(self, data: Dict[str, Any], name: str) -> None:
        """Persist engine state using traditional chunked INSERTs.

        Works with any SQL dialect.  Used as the primary path for
        non-MySQL backends and as a fallback when CSV bulk insert
        is unavailable.

        Args:
            data: Engine-state dict.
            name: Physical index name.
        """
        with self._engine.begin() as conn:
            self._save_common_header(conn, data, name)

            # 3. Inverted index
            self._chunked_insert(
                conn, self._t_inverted_index,
                self._make_inv_rows(data, name),
                chunk_size=50, max_payload_bytes=1_000_000,
            )

            # 4. Doc vectors (optional)
            if data.get("doc_vectors"):
                self._chunked_insert(
                    conn, self._t_doc_vectors,
                    self._make_vec_rows(data, name),
                    chunk_size=500,
                )

            # 5. ID mapping
            self._chunked_insert(
                conn, self._t_id_mapping,
                self._make_id_rows(data, name),
                chunk_size=1000,
            )

            # 6. Doc lengths
            self._chunked_insert(
                conn, self._t_doc_lengths,
                self._make_len_rows(data, name),
                chunk_size=1000,
            )

    def load(self, name: str) -> Dict[str, Any]:
        """
        Reconstruct an engine state dict from the ``lucis_*`` tables.
        Uses streaming iteration (``yield_per``) on large tables.

        Args:
            name: Physical index name (same key used in :meth:`save`).

        Returns:
            Engine-state dict ready to pass to ``BaseEngine.load_engine``.

        Raises:
            FileNotFoundError: If *name* is not found in ``lucis_metadata``.
        """
        with self._engine.connect() as conn:
            # 1. Metadata (single row — fetchone is fine)
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

            # 2. Inverted index — stream row-by-row, build dict incrementally
            index: Dict[str, Dict[int, int]] = {}
            result = conn.execute(
                select(
                    self._t_inverted_index.c.word,
                    self._t_inverted_index.c.postings,
                ).where(self._t_inverted_index.c.index_name == name)
            ).yield_per(2_000)

            for word, postings_json in result:
                index[word] = {
                    int(k): v for k, v in _loads(postings_json).items()
                }

            # 3. Document vectors — stream row-by-row
            doc_vectors: Dict[int, Dict[str, float]] = {}
            result = conn.execute(
                select(
                    self._t_doc_vectors.c.doc_internal_id,
                    self._t_doc_vectors.c.vector,
                ).where(self._t_doc_vectors.c.index_name == name)
            ).yield_per(2_000)

            for doc_id, vector_json in result:
                doc_vectors[doc_id] = _loads(vector_json)

            # 4. ID mapping — stream row-by-row
            id_map: Dict[int, Any] = {}
            result = conn.execute(
                select(
                    self._t_id_mapping.c.internal_id,
                    self._t_id_mapping.c.original_id,
                ).where(self._t_id_mapping.c.index_name == name)
            ).yield_per(5_000)

            for internal_id, original_id in result:
                if id_type == "sequential":
                    id_map[internal_id] = int(original_id)
                else:
                    id_map[internal_id] = original_id

            # 5. Document lengths — stream row-by-row
            doc_lengths: Dict[int, int] = {}
            result = conn.execute(
                select(
                    self._t_doc_lengths.c.doc_internal_id,
                    self._t_doc_lengths.c.length,
                ).where(self._t_doc_lengths.c.index_name == name)
            ).yield_per(5_000)

            for doc_id, length in result:
                doc_lengths[doc_id] = length

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

        Args:
            name: Logical alias or physical index name to check.

        Returns:
            ``True`` if the index (or its alias target) exists in
            ``lucis_metadata``.
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
        """Remove all data for *name* from every ``lucis_*`` table.

        If the index is sharded, all child shard entries and the shard
        registry are cleaned up automatically.

        Args:
            name: Physical index name to delete.  Aliases pointing to
                this name are **not** removed automatically.
        """
        # Collect shard children (if any)
        shard_keys = self.load_shard_registry(name)

        with self._engine.begin() as conn:
            # Delete shard data first
            for key in shard_keys:
                shard_name = f"{name}__shard__{key}"
                for table in (
                    self._t_inverted_index,
                    self._t_doc_vectors,
                    self._t_id_mapping,
                    self._t_doc_lengths,
                    self._t_metadata,
                ):
                    conn.execute(
                        delete(table).where(table.c.index_name == shard_name)
                    )

            # Delete shard registry
            if shard_keys:
                conn.execute(
                    delete(self._t_shard_registry).where(
                        self._t_shard_registry.c.index_name == name
                    )
                )

            # Delete parent / main entry
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
        """Return a sorted list of all index names stored in the database.

        Returns:
            List of physical index names present in ``lucis_metadata``
            (excludes aliases).
        """
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

        Args:
            name: Logical alias or physical index name.

        Returns:
            Physical index name the alias points to, or *name* if it
            is not a registered alias.
        """
        target = self.get_alias(name)
        return target if target is not None else name

    def set_alias(self, alias_name: str, target_index: str) -> None:
        """Create or update an alias → target mapping (atomic).

        Args:
            alias_name: Logical name users reference the index by.
            target_index: Physical versioned name the alias should
                point to (e.g. ``"articles__v20260210_143022"``).
        """
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
        """Return the physical index name for *alias_name*.

        Args:
            alias_name: The logical alias to look up.

        Returns:
            Physical index name the alias points to, or ``None`` if
            *alias_name* is not registered.
        """
        with self._engine.connect() as conn:
            row = conn.execute(
                select(self._t_aliases.c.target_index).where(
                    self._t_aliases.c.alias_name == alias_name
                )
            ).fetchone()
        return row[0] if row else None

    def list_aliases(self) -> Dict[str, str]:
        """Return all registered aliases.

        Returns:
            ``{alias_name: target_index}`` dict sorted by alias name.
        """
        with self._engine.connect() as conn:
            rows = conn.execute(
                select(
                    self._t_aliases.c.alias_name,
                    self._t_aliases.c.target_index,
                ).order_by(self._t_aliases.c.alias_name)
            ).fetchall()
        return {row[0]: row[1] for row in rows}

    def delete_alias(self, alias_name: str) -> None:
        """Remove an alias (does **not** delete the physical index).

        Args:
            alias_name: The alias to remove.
        """
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
        """Return all physical versions of *base_name*, sorted oldest → newest.

        Shard entries (``__shard__``) are excluded — only parent
        version names are returned.

        Args:
            base_name: The logical/alias name whose versions to list.

        Returns:
            Sorted list of versioned physical names, e.g.
            ``["articles__v20260210_143022", "articles__v20260210_150545"]``.
        """
        with self._engine.connect() as conn:
            rows = conn.execute(
                select(self._t_metadata.c.index_name)
                .where(self._t_metadata.c.index_name.like(f"{base_name}__v%"))
                .where(~self._t_metadata.c.index_name.like("%__shard__%"))
                .order_by(self._t_metadata.c.index_name)
            ).fetchall()
        return [row[0] for row in rows]

    # Source-info persistence (smart worker support)

    def save_source_info(self, name: str, info: Dict[str, Any]) -> None:
        """Persist data-source metadata into ``lucis_metadata``.

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
        with self._engine.begin() as conn:
            conn.execute(
                self._t_metadata.update()
                .where(self._t_metadata.c.index_name == name)
                .values(
                    source_table=info.get("table"),
                    source_column=source_column,
                    source_id_column=info.get("id_column"),
                    source_date_column=info.get("date_column"),
                    source_query=info.get("query"),
                    source_where=info.get("where_clause"),
                )
            )

    def load_source_info(self, name: str) -> Optional[Dict[str, Any]]:
        """Load source metadata from ``lucis_metadata``.

        Args:
            name: Physical index name whose metadata to retrieve.

        Returns:
            Source-info dict (see :meth:`save_source_info` for key
            descriptions), or ``None`` if no metadata was stored.
        """
        with self._engine.connect() as conn:
            row = conn.execute(
                select(
                    self._t_metadata.c.source_table,
                    self._t_metadata.c.source_column,
                    self._t_metadata.c.source_id_column,
                    self._t_metadata.c.source_date_column,
                    self._t_metadata.c.source_query,
                    self._t_metadata.c.source_where,
                ).where(self._t_metadata.c.index_name == name)
            ).fetchone()

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
        with self._engine.connect() as conn:
            result = conn.execute(
                sa_text(f"SELECT COUNT(*) FROM {table_name}")
            )
            return result.scalar()

    # Shard support (temporal partitioning)

    def get_total_docs(self, name: str) -> int:
        """Return *total_docs* for *name* without loading the full index.

        Uses a single metadata-only query — much lighter than ``load()``.
        Returns 0 if the index does not exist.

        Args:
            name: Physical index name (already resolved from alias).

        Returns:
            Document count stored in ``lucis_metadata``, or 0.
        """
        with self._engine.connect() as conn:
            row = conn.execute(
                select(self._t_metadata.c.total_docs)
                .where(self._t_metadata.c.index_name == name)
                .limit(1)
            ).fetchone()
        return int(row[0]) if row else 0

    def save_shard_registry(self, index_name: str, shard_keys: list) -> None:
        """Persist the shard keys for a sharded index.

        Args:
            index_name: The versioned physical name of the parent index.
            shard_keys: List of shard keys to register
                (e.g. ``["2026_01", "9999_99"]``).
        """
        with self._engine.begin() as conn:
            conn.execute(
                delete(self._t_shard_registry).where(
                    self._t_shard_registry.c.index_name == index_name
                )
            )
            if shard_keys:
                rows = [
                    {"index_name": index_name, "shard_key": key}
                    for key in shard_keys
                ]
                conn.execute(self._t_shard_registry.insert(), rows)

    def load_shard_registry(self, index_name: str) -> list:
        """Return shard keys for *index_name*, sorted.

        Args:
            index_name: The versioned physical name of the parent index.

        Returns:
            Sorted list of shard keys.  An empty list means the index
            is monolithic (not sharded).
        """
        with self._engine.connect() as conn:
            rows = conn.execute(
                select(self._t_shard_registry.c.shard_key)
                .where(self._t_shard_registry.c.index_name == index_name)
                .order_by(self._t_shard_registry.c.shard_key)
            ).fetchall()
        return [row[0] for row in rows]

    def detect_date_column(
        self,
        table_name: str,
        schema: Optional[str] = None,
    ) -> Optional[str]:
        """Auto-detect a date column in the user table.

        Checks for columns named ``created_at``, ``updated_at``, or
        ``timestamp`` (in that order).

        Args:
            table_name: Name of the user table to inspect.
            schema: Database schema (optional, e.g. ``"public"`` for
                PostgreSQL).

        Returns:
            The column name if found, otherwise ``None``.
        """
        from ..core.shard import LUCIS_DEFAULT_DATE_COLUMNS

        user_meta = MetaData()
        user_table = Table(
            table_name, user_meta, autoload_with=self._engine, schema=schema
        )
        table_columns = {col.name for col in user_table.columns}
        for candidate in LUCIS_DEFAULT_DATE_COLUMNS:
            if candidate in table_columns:
                return candidate
        return None

    def read_table_with_dates(
        self,
        table_name: str,
        text_column: Union[str, List[str]],
        id_column: Optional[str] = None,
        date_column: Optional[str] = None,
        where_clause: Optional[str] = None,
        schema: Optional[str] = None,
    ) -> tuple:
        """Read rows with dates for shard routing.

        Supports **cross-field search**: pass a list of column names
        to concatenate them into a single document at the SQL level.

        Args:
            table_name: Source table name.
            text_column: Column name or list of column names for document text.
            id_column: Column to use as document ID (optional).
                When ``None``, row indices are used as string keys.
            date_column: Column for temporal shard routing (optional).
            where_clause: Optional SQL ``WHERE`` filter
                (without the ``WHERE`` keyword).
            schema: Database schema (optional).

        Returns:
            Tuple ``(data, dates)`` where:

            - *data*: ``Dict[str, str]`` mapping ``{doc_id: text}``.
            - *dates*: ``Dict[str, Any]`` mapping ``{doc_id: date_value}``.
        """
        user_meta = MetaData()
        user_table = Table(
            table_name, user_meta, autoload_with=self._engine, schema=schema
        )

        text_expr = self._build_text_expr(user_table, text_column)
        cols = []
        if id_column:
            cols.append(user_table.c[id_column])
        cols.append(text_expr)
        if date_column:
            cols.append(user_table.c[date_column])

        stmt = select(*cols)
        if where_clause:
            stmt = stmt.where(sa_text(where_clause))

        with self._engine.connect() as conn:
            rows = conn.execute(stmt).fetchall()

        data: Dict[str, str] = {}
        dates: Dict[str, Any] = {}

        if id_column and date_column:
            for row in rows:
                doc_id = str(row[0])
                data[doc_id] = row[1]
                dates[doc_id] = row[2]
        elif id_column:
            for row in rows:
                doc_id = str(row[0])
                data[doc_id] = row[1]
                dates[doc_id] = None
        elif date_column:
            for i, row in enumerate(rows):
                doc_id = str(i)
                data[doc_id] = row[0]
                dates[doc_id] = row[1]
        else:
            for i, row in enumerate(rows):
                doc_id = str(i)
                data[doc_id] = row[0]
                dates[doc_id] = None

        return data, dates

    def stream_table_with_dates(
        self,
        table_name: str,
        text_column: Union[str, List[str]],
        id_column: Optional[str] = None,
        date_column: Optional[str] = None,
        where_clause: Optional[str] = None,
        schema: Optional[str] = None,
        batch_size: int = 5_000,
    ):
        """Stream rows from a table as ``(doc_id_str, text, date_val)`` tuples.

        Uses a **server-side cursor** (``yield_per``) so only *batch_size*
        rows are fetched from the database at a time.  The peak RAM
        from data ingestion is bounded by ``batch_size × row_size``
        instead of holding all rows in memory at once.

        This is the streaming counterpart to :meth:`read_table_with_dates`
        and is the recommended path for datasets > 100 K rows.

        Args:
            table_name: Source table name.
            text_column: Column name or list of column names for text.
            id_column: Column to use as document ID (optional).
            date_column: Column for temporal shard routing (optional).
            where_clause: Optional SQL ``WHERE`` filter.
            schema: Database schema (optional).
            batch_size: Number of rows to buffer per server fetch.
                Default 5 000 — a safe balance between network round-trips
                and memory pressure.

        Yields:
            ``(doc_id_str, text, date_val)`` tuples.
            *doc_id_str* is always a string.
            *date_val* is ``None`` when *date_column* is not given.

        Example::

            for doc_id, text, date in storage.stream_table_with_dates(
                "emails", "body", id_column="id", date_column="created_at"
            ):
                ...
        """
        user_meta = MetaData()
        user_table = Table(
            table_name, user_meta, autoload_with=self._engine, schema=schema
        )

        text_expr = self._build_text_expr(user_table, text_column)
        cols = []
        if id_column:
            cols.append(user_table.c[id_column])
        cols.append(text_expr)
        if date_column:
            cols.append(user_table.c[date_column])

        stmt = select(*cols)
        if where_clause:
            stmt = stmt.where(sa_text(where_clause))

        # stream_results=True + yield_per activates the server-side cursor
        # so SQLAlchemy fetches *batch_size* rows per network round-trip.
        conn_opts = {"stream_results": True, "yield_per": batch_size}
        row_counter = 0

        with self._engine.connect().execution_options(**conn_opts) as conn:
            result = conn.execute(stmt)
            if id_column and date_column:
                for row in result:
                    yield str(row[0]), row[1], row[2]
                    row_counter += 1
            elif id_column:
                for row in result:
                    yield str(row[0]), row[1], None
                    row_counter += 1
            elif date_column:
                for i, row in enumerate(result):
                    yield str(i), row[0], row[1]
                    row_counter += 1
            else:
                for i, row in enumerate(result):
                    yield str(i), row[0], None
                    row_counter += 1

    # Read helpers

    def read_table(
        self,
        table_name: str,
        text_column: Union[str, List[str]],
        id_column: Optional[str] = None,
        where_clause: Optional[str] = None,
        schema: Optional[str] = None,
    ) -> Union[Dict[str, str], list[str]]:
        """
        Read rows from an existing user table and return them in
        a format ready for ``Lucis.index()``.

        This is a convenience helper so users don't have to write raw SQL.

        Supports **cross-field search**: pass a list of column names
        to concatenate them into a single document at the SQL level.

        Args:
            table_name: Name of the source table.
            text_column: Column name (or list of column names) that
                contain the document text.  When a list is given, the
                columns are concatenated with spaces at the SQL level.
            id_column: Column to use as document ID (optional).
                If ``None``, results are returned as a ``list[str]``.
            where_clause: Optional SQL ``WHERE`` filter
                (without the ``WHERE`` keyword).
            schema: Database schema (e.g. ``"public"`` for PostgreSQL).

        Returns:
            ``Dict[str, str]`` if *id_column* is given, else ``list[str]``.

        Example — single column::

            data = storage.read_table(
                "articles", text_column="content", id_column="article_id"
            )

        Example — cross-field (multiple columns)::

            data = storage.read_table(
                "articles",
                text_column=["title", "content", "tags"],
                id_column="article_id",
            )
        """
        # Reflect the user table from the database
        user_meta = MetaData()
        user_table = Table(
            table_name, user_meta, autoload_with=self._engine, schema=schema
        )

        text_expr = self._build_text_expr(user_table, text_column)
        if id_column:
            cols = [user_table.c[id_column], text_expr]
        else:
            cols = [text_expr]

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
        """Dispose the engine when the object is garbage-collected."""
        try:
            self.close()
        except Exception:
            pass

    def __repr__(self) -> str:
        """Return a masked URL representation (password hidden by SQLAlchemy)."""
        # Mask password in URL for safety
        url = str(self._engine.url)
        return f"AlchemyStorage(url='{url}')"
