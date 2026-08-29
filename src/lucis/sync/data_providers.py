"""
Data provider factories for the IndexWorker.

Each factory reads a ``SourceSpec`` and returns a no-argument callable
that fetches the full corpus (or a streaming iterator) from the
configured data source.
"""
from typing import Any, Callable, Optional

from .source_spec import SourceSpec
from .._internals import _build_sql_text_expr


def build_data_fn(
    spec: SourceSpec,
    reader: Any,
    storage: Any,
    engine_name: str,
) -> Callable:
    """Auto-generate a ``data_fn`` callable from a SourceSpec.

    For sharded indices (``date_column`` present), the returned
    callable produces ``(data, dates)`` tuples.  For non-sharded
    indices, it returns ``Dict`` or ``List`` as before.

    Uses *reader* for database sources (read-only access to
    the production DB) and falls back to *storage* for other
    backends.

    Args:
        spec: Source description.
        reader: Optional DatabaseReader instance.
        storage: Storage backend.
        engine_name: Engine name (for error messages).

    Returns:
        A no-argument callable that fetches the full corpus.

    Raises:
        LucisEngineError: If the spec has an unknown ``type`` field.
    """
    from ..exceptions import LucisEngineError

    date_col = spec.date_column

    if spec.type == "table":
        table_name = spec.table
        text_col = spec.text_columns
        id_col = spec.id_column
        where = spec.where_clause

        # Sharded: return (data, dates)
        if date_col:
            if reader and hasattr(reader, "read_table_with_dates"):
                def fetch_with_dates():
                    return reader.read_table_with_dates(
                        table_name, text_col, id_col, date_col, where,
                    )
                return fetch_with_dates
            elif hasattr(storage, "read_table_with_dates"):
                def fetch_with_dates_storage():
                    return storage.read_table_with_dates(
                        table_name, text_col, id_col, date_col, where,
                    )
                return fetch_with_dates_storage

        # Non-sharded: Alchemy reader or storage
        if reader and hasattr(reader, "read_table"):
            def fetch():
                return reader.read_table(
                    table_name, text_col, id_col, where
                )
            return fetch

        if hasattr(storage, "read_table"):
            def fetch_storage():
                return storage.read_table(
                    table_name, text_col, id_col, where
                )
            return fetch_storage

        # Non-sharded: SQLite
        text_expr = _build_sql_text_expr(text_col)
        cols = f"{id_col}, {text_expr}" if id_col else text_expr
        sql = f"SELECT {cols} FROM {table_name}"
        if where:
            sql += f" WHERE {where}"
        db_path = getattr(storage, "db_path", None)

        def fetch_sqlite():
            import sqlite3
            conn = sqlite3.connect(db_path)
            cursor = conn.execute(sql)
            if id_col:
                data = {str(row[0]): row[1] for row in cursor}
            else:
                data = [row[0] for row in cursor]
            conn.close()
            return data
        return fetch_sqlite

    elif spec.type == "query":
        query_str = spec.query

        if reader and hasattr(reader, "read_query"):
            def fetch_q():
                return reader.read_query(query_str)
            return fetch_q
        elif hasattr(storage, "read_query"):
            def fetch_q_storage():
                return storage.read_query(query_str)
            return fetch_q_storage
        else:
            db_path = getattr(storage, "db_path", None)

            def fetch_q_sqlite():
                import sqlite3
                conn = sqlite3.connect(db_path)
                cursor = conn.execute(query_str)
                first = cursor.fetchone()
                if first is None:
                    conn.close()
                    return []
                cursor = conn.execute(query_str)
                if len(first) == 1:
                    data = [row[0] for row in cursor]
                else:
                    data = {str(row[0]): row[1] for row in cursor}
                conn.close()
                return data
            return fetch_q_sqlite

    raise LucisEngineError(
        engine_name=engine_name,
        detail=f"Cannot auto-generate data_fn: unknown source type '{spec.type}'",
    )


def build_streaming_fn(
    spec: SourceSpec,
    reader: Any,
    storage: Any,
) -> Optional[Callable]:
    """Return a no-arg callable that produces a streaming row iterator.

    Available when: source is a ``"table"``, a *reader* (or *storage*)
    has ``stream_table_with_dates``, **and** a ``date_column`` is
    configured (sharded mode).

    Returns ``None`` when any of these conditions is not met —
    callers should fall back to :func:`build_data_fn`.

    The returned callable has the signature::

        def streaming_fn() -> Iterator[(doc_id, text, date_val)]

    Each call to ``streaming_fn()`` opens a fresh server-side cursor
    on the database.
    """
    if spec is None or spec.type != "table":
        return None
    if not spec.date_column:
        return None  # Streaming rebuild only meaningful for sharded mode

    # Prefer the read-only database reader; fall back to storage.
    source = reader if reader else storage
    if not hasattr(source, "stream_table_with_dates"):
        return None

    table_name = spec.table
    text_col = spec.text_columns
    id_col = spec.id_column
    date_col = spec.date_column
    where = spec.where_clause
    schema = spec.schema

    def streaming_fn():
        return source.stream_table_with_dates(
            table_name, text_col, id_col, date_col, where, schema,
        )
    return streaming_fn
