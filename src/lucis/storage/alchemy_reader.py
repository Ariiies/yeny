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

logger = logging.getLogger("lucis.storage.alchemy_reader")

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
            "AlchemyReader requires SQLAlchemy. "
            "Install it with:  pip install lucis[alchemy]\n"
            "For MySQL add:    pip install pymysql"
        )


class AlchemyReader:
    """Read-only adapter for fetching user data from a SQL database.

    Unlike :class:`AlchemyStorage`, this class **never** creates or
    writes to ``lucis_*`` tables.  It only reads from user tables.

    Args:
        url: SQLAlchemy connection URL.
        engine: An existing ``sqlalchemy.engine.Engine`` instance.
        connect_args: Extra keyword arguments forwarded to
            ``create_engine``.
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
            if "pymysql" in url:
                ca = kwargs.setdefault("connect_args", {})
                ca.setdefault("local_infile", True)
            self._engine = create_engine(url, pool_pre_ping=True, **kwargs)
            self._owns_engine = True
        else:
            raise ValueError(
                "AlchemyReader requires either a 'url' or an 'engine'."
            )

        self.url = url or str(self._engine.url)

    # ── Text expression helpers ─────────────────────────────────────

    def _build_text_expr(self, table: Any, text_column: Union[str, List[str]]) -> Any:
        """Build a SQLAlchemy expression for one or more text columns."""
        if isinstance(text_column, str):
            return table.c[text_column]
        if len(text_column) == 1:
            return table.c[text_column[0]]

        dialect = self._engine.dialect.name
        if dialect in ("mysql", "mariadb"):
            return sa_func.concat_ws(
                ' ', *[table.c[col] for col in text_column]
            )
        else:
            parts = [
                sa_func.coalesce(table.c[col], sa_literal(''))
                for col in text_column
            ]
            expr = parts[0]
            for part in parts[1:]:
                expr = expr.concat(sa_literal(' ')).concat(part)
            return expr

    def _sql_concat_columns(self, text_column: Union[str, List[str]]) -> str:
        """Return a raw SQL fragment for concatenating text columns."""
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

    # ── Date column detection ──────────────────────────────────────

    def detect_date_column(
        self,
        table_name: str,
        schema: Optional[str] = None,
    ) -> Optional[str]:
        """Auto-detect a date column in the user table."""
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

    # ── Row readers ────────────────────────────────────────────────

    def read_table(
        self,
        table_name: str,
        text_column: Union[str, List[str]],
        id_column: Optional[str] = None,
        where_clause: Optional[str] = None,
        schema: Optional[str] = None,
    ) -> Union[Dict[str, str], list[str]]:
        """Read rows from a user table (no date routing)."""
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

    def read_table_with_dates(
        self,
        table_name: str,
        text_column: Union[str, List[str]],
        id_column: Optional[str] = None,
        date_column: Optional[str] = None,
        where_clause: Optional[str] = None,
        schema: Optional[str] = None,
    ) -> tuple:
        """Read rows with dates for shard routing."""
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
        """Stream rows as ``(doc_id, text, date_val)`` using a server-side cursor."""
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

        conn_opts = {"stream_results": True, "yield_per": batch_size}
        with self._engine.connect().execution_options(**conn_opts) as conn:
            result = conn.execute(stmt)
            if id_column and date_column:
                for row in result:
                    yield str(row[0]), row[1], row[2]
            elif id_column:
                for row in result:
                    yield str(row[0]), row[1], None
            elif date_column:
                for i, row in enumerate(result):
                    yield str(i), row[0], row[1]
            else:
                for i, row in enumerate(result):
                    yield str(i), row[0], None

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

    # ── Metadata queries (read-only) ──────────────────────────────

    def count_rows(self, table_name: str) -> Optional[int]:
        """Return ``SELECT COUNT(*) FROM <table_name>``."""
        with self._engine.connect() as conn:
            result = conn.execute(
                sa_text(f"SELECT COUNT(*) FROM {table_name}")
            )
            return result.scalar()

    # ── Lifecycle ──────────────────────────────────────────────────

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
        url = str(self._engine.url)
        return f"AlchemyReader(url='{url}')"
