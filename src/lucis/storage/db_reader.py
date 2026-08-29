"""
Read-only data source adapter for SQLAlchemy-backed databases.

Provides access to user tables (SELECT, COUNT, stream) without
creating or writing to any ``lucis_*`` tables.  All Lucis metadata
is handled by :class:`~lucis.storage.metadata_storage.MetadataStorage`
(SQLite) instead.

Requires the ``sqlalchemy`` extra::

    pip install lucis[alchemy]
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Union

logger = logging.getLogger("lucis.storage.db_reader")

try:
    from sqlalchemy import (
        create_engine,
        MetaData,
        Table,
        select,
        text as sa_text,
        func as sa_func,
        literal as sa_literal,
    )
    from sqlalchemy.engine import Engine

    HAS_SQLALCHEMY = True
except ImportError:  # pragma: no cover
    HAS_SQLALCHEMY = False


def _require_sqlalchemy() -> None:
    if not HAS_SQLALCHEMY:
        raise ImportError(
            "DatabaseReader requires SQLAlchemy. "
            "Install it with:  pip install lucis[alchemy]\n"
            "For MySQL add:    pip install pymysql"
        )


class DatabaseReader:
    """Read-only adapter for fetching user data from a SQL database.

    Unlike :class:`AlchemyStorage`, this class **never** creates or
    writes to ``lucis_*`` tables.  It only reads from user tables.

    Args:
        connection_url: SQLAlchemy connection URL.
        engine: An existing ``sqlalchemy.engine.Engine`` instance.
        connect_args: Extra keyword arguments forwarded to
            ``create_engine``.
    """

    def __init__(
        self,
        connection_url: Optional[str] = None,
        engine: Optional[Any] = None,
        connect_args: Optional[Dict[str, Any]] = None,
    ):
        _require_sqlalchemy()

        if engine is not None:
            self._engine: Engine = engine
            self._owns_engine = False
        elif connection_url is not None:
            kwargs: Dict[str, Any] = {}
            if connect_args:
                kwargs["connect_args"] = dict(connect_args)
            if "pymysql" in connection_url:
                ca = kwargs.setdefault("connect_args", {})
                ca.setdefault("local_infile", True)
            self._engine = create_engine(
                connection_url, pool_pre_ping=True, **kwargs
            )
            self._owns_engine = True
        else:
            raise ValueError(
                "DatabaseReader requires either 'connection_url' or 'engine'."
            )

        self.connection_url = connection_url or str(self._engine.url)

    # Text expression helpers 

    def _build_text_expr(
        self, table: Any, text_columns: Union[str, List[str]]
    ) -> Any:
        """Build a SQLAlchemy expression for one or more text columns."""
        if isinstance(text_columns, str):
            return table.c[text_columns]
        if len(text_columns) == 1:
            return table.c[text_columns[0]]

        dialect = self._engine.dialect.name
        if dialect in ("mysql", "mariadb"):
            return sa_func.concat_ws(
                ' ', *[table.c[col] for col in text_columns]
            )
        else:
            parts = [
                sa_func.coalesce(table.c[col], sa_literal(''))
                for col in text_columns
            ]
            expr = parts[0]
            for part in parts[1:]:
                expr = expr.concat(sa_literal(' ')).concat(part)
            return expr

    def _sql_concat_columns(self, text_columns: Union[str, List[str]]) -> str:
        """Return a raw SQL fragment for concatenating text columns."""
        if isinstance(text_columns, str):
            return text_columns
        if len(text_columns) == 1:
            return text_columns[0]

        dialect = self._engine.dialect.name
        if dialect in ("mysql", "mariadb"):
            return f"CONCAT_WS(' ', {', '.join(text_columns)})"
        else:
            coalesced = [f"COALESCE({col}, '')" for col in text_columns]
            return " || ' ' || ".join(coalesced)

    # Date column detection

    def detect_date_column(
        self,
        table: str,
        schema: Optional[str] = None,
    ) -> Optional[str]:
        """Auto-detect a date column in the user table."""
        from ..core.shard import LUCIS_DEFAULT_DATE_COLUMNS

        user_meta = MetaData()
        user_table = Table(
            table, user_meta, autoload_with=self._engine, schema=schema
        )
        table_columns = {col.name for col in user_table.columns}
        for candidate in LUCIS_DEFAULT_DATE_COLUMNS:
            if candidate in table_columns:
                return candidate
        return None

    # Row readers

    def read_table(
        self,
        table: str,
        text_columns: Union[str, List[str]],
        id_column: Optional[str] = None,
        where_clause: Optional[str] = None,
        schema: Optional[str] = None,
    ) -> Union[Dict[str, str], list[str]]:
        """Read rows from a user table (no date routing)."""
        user_meta = MetaData()
        user_table = Table(
            table, user_meta, autoload_with=self._engine, schema=schema
        )
        text_expr = self._build_text_expr(user_table, text_columns)
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

    def read_table_with_dates(
        self,
        table: str,
        text_columns: Union[str, List[str]],
        id_column: Optional[str] = None,
        date_column: Optional[str] = None,
        where_clause: Optional[str] = None,
        schema: Optional[str] = None,
    ) -> tuple:
        """Read rows with dates for shard routing."""
        user_meta = MetaData()
        user_table = Table(
            table, user_meta, autoload_with=self._engine, schema=schema
        )
        text_expr = self._build_text_expr(user_table, text_columns)
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
        table: str,
        text_columns: Union[str, List[str]],
        id_column: Optional[str] = None,
        date_column: Optional[str] = None,
        where_clause: Optional[str] = None,
        schema: Optional[str] = None,
        batch_size: int = 5_000,
    ):
        """Stream rows as ``(doc_id, text, date_val)`` via keyset pagination.

        Instead of holding a single server-side cursor open for the
        entire dataset (which times out on large tables), this method
        fetches short batches using keyset pagination::

            SELECT ... WHERE id > :last_id ORDER BY id LIMIT :batch_size

        Each batch opens and closes its own connection, making the
        approach immune to MySQL ``wait_timeout`` / ``net_read_timeout``
        disconnects regardless of how long the caller takes to process
        each batch.

        When *id_column* is ``None`` a positional counter is used as
        ``doc_id`` and a simple ``LIMIT/OFFSET`` fallback is used instead,
        though this path is slower for very large tables.
        """
        user_meta = MetaData()
        user_table = Table(
            table, user_meta, autoload_with=self._engine, schema=schema
        )
        text_expr = self._build_text_expr(user_table, text_columns)

        if id_column:
            yield from self._stream_keyset(
                user_table, text_expr, id_column, date_column,
                where_clause, batch_size,
            )
        else:
            yield from self._stream_offset(
                user_table, text_expr, date_column,
                where_clause, batch_size,
            )

    # Keyset pagination (preferred)

    def _stream_keyset(self, table, text_expr, id_column, date_column,
                       where_clause, batch_size):
        """Paginate using ``WHERE id > :last ORDER BY id``."""
        id_col = table.c[id_column]

        cols = [id_col, text_expr]
        if date_column:
            cols.append(table.c[date_column])

        base_stmt = select(*cols)
        if where_clause:
            base_stmt = base_stmt.where(sa_text(where_clause))
        base_stmt = base_stmt.order_by(id_col)

        last_id: Any = None

        while True:
            stmt = base_stmt.limit(batch_size)
            if last_id is not None:
                stmt = stmt.where(id_col > last_id)

            with self._engine.connect() as conn:
                rows = conn.execute(stmt).fetchall()

            if not rows:
                break

            if date_column:
                for row in rows:
                    yield str(row[0]), row[1], row[2]
            else:
                for row in rows:
                    yield str(row[0]), row[1], None

            last_id = rows[-1][0]

            if len(rows) < batch_size:
                break

    # Offset fallback (no id_column)

    def _stream_offset(self, table, text_expr, date_column,
                       where_clause, batch_size):
        """Paginate using ``LIMIT/OFFSET`` when no id column is available."""
        cols = [text_expr]
        if date_column:
            cols.append(table.c[date_column])

        base_stmt = select(*cols)
        if where_clause:
            base_stmt = base_stmt.where(sa_text(where_clause))

        offset = 0
        global_idx = 0

        while True:
            stmt = base_stmt.limit(batch_size).offset(offset)

            with self._engine.connect() as conn:
                rows = conn.execute(stmt).fetchall()

            if not rows:
                break

            if date_column:
                for row in rows:
                    yield str(global_idx), row[0], row[1]
                    global_idx += 1
            else:
                for row in rows:
                    yield str(global_idx), row[0], None
                    global_idx += 1

            offset += batch_size

            if len(rows) < batch_size:
                break

    def read_query(
        self,
        query: str,
    ) -> Union[Dict[str, str], list[str]]:
        """Execute an arbitrary SELECT and return Lucis-ready data."""
        with self._engine.connect() as conn:
            result = conn.execute(sa_text(query))
            rows = result.fetchall()

        if not rows:
            raise ValueError("The query returned no results.")

        if len(rows[0]) == 1:
            return [row[0] for row in rows]
        else:
            return {str(row[0]): row[1] for row in rows}

    # Metadata queries (read-only)

    def count_rows(self, table: str) -> Optional[int]:
        """Return ``SELECT COUNT(*) FROM <table>``."""
        with self._engine.connect() as conn:
            result = conn.execute(
                sa_text(f"SELECT COUNT(*) FROM {table}")
            )
            return result.scalar()

    # Lifecycle management

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
        connection_url = str(self._engine.url)
        return f"DatabaseReader(connection_url='{connection_url}')"
