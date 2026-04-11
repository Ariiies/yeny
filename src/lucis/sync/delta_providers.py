"""
Delta provider factories for the IndexWorker.

A delta provider returns **only new documents** since the last call,
enabling efficient incremental indexing without fetching the full
corpus each cycle.
"""
from typing import Any, Callable, Optional

from .source_spec import SourceSpec
from .._internals import _build_sql_text_expr


def build_delta_fn(
    spec: SourceSpec,
    reader: Any,
    storage: Any,
    shard_manager: Any,
    engine: Any,
) -> Optional[Callable]:
    """Auto-generate a delta_fn that returns only NEW documents since last call.

    Strategy selection:

    1. **Table + id_column** (optimal): Uses ``WHERE id > last_max_id``
       to fetch only new rows at the SQL level.
    2. **Query or table without id_column** (universal): Fetches all
       data via ``data_fn`` and diffs against already-indexed IDs
       to extract only the new documents.

    Returns ``None`` only when *spec* is ``None`` (no auto-generation
    possible).
    """
    if spec is None:
        return None

    # Optimized path: table + id_column → SQL-level delta
    if spec.type == "table" and spec.id_column:
        return _build_delta_fn_by_id(spec, reader, storage)

    # Universal path: fetch all → diff against known IDs
    return _build_delta_fn_universal(spec, reader, storage, shard_manager, engine)


def _build_delta_fn_by_id(
    spec: SourceSpec,
    reader: Any,
    storage: Any,
) -> Callable:
    """Optimized delta: ``WHERE id > last_max_id`` at the SQL level.

    When a ``date_column`` is present, the returned callable
    produces ``(data, dates)`` tuples for shard routing.

    Uses *reader* for Alchemy sources, falls back to *storage*.
    """
    id_col = spec.id_column
    table_name = spec.table_name
    text_col = spec.text_column
    date_col = spec.date_column
    where = spec.where_clause

    # Prefer reader for source DB access
    source = reader if reader else storage
    last_max = [0]

    if hasattr(source, "_engine"):
        # AlchemyReader / AlchemyStorage
        from sqlalchemy import text as _sa_text

        with source._engine.connect() as conn:
            result = conn.execute(
                _sa_text(f"SELECT MAX({id_col}) FROM {table_name}")
            ).scalar()
            if result is not None:
                last_max[0] = result

        # Build text expression for multi-column support
        text_expr = source._sql_concat_columns(text_col)

        def _make_delta_commit(fn):
            """Attach deferred commit to a delta function."""
            fn._pending_max = None

            def commit():
                if fn._pending_max is not None:
                    last_max[0] = fn._pending_max
                    fn._pending_max = None

            fn.commit = commit
            return fn

        if date_col:
            def delta_alchemy_sharded():
                from sqlalchemy import text as _sa_t
                sql = (
                    f"SELECT {id_col}, {text_expr}, {date_col} "
                    f"FROM {table_name} WHERE {id_col} > :last_id"
                )
                if where:
                    sql += f" AND ({where})"
                sql += f" ORDER BY {id_col}"
                with source._engine.connect() as conn:
                    rows = conn.execute(
                        _sa_t(sql), {"last_id": last_max[0]}
                    ).fetchall()
                if not rows:
                    return {}, {}
                data = {str(row[0]): row[1] for row in rows}
                dates = {str(row[0]): row[2] for row in rows}
                delta_alchemy_sharded._pending_max = max(row[0] for row in rows)
                return data, dates
            return _make_delta_commit(delta_alchemy_sharded)
        else:
            def delta_alchemy():
                from sqlalchemy import text as _sa_t
                sql = f"SELECT {id_col}, {text_expr} FROM {table_name} WHERE {id_col} > :last_id"
                if where:
                    sql += f" AND ({where})"
                sql += f" ORDER BY {id_col}"
                with source._engine.connect() as conn:
                    rows = conn.execute(
                        _sa_t(sql), {"last_id": last_max[0]}
                    ).fetchall()
                if not rows:
                    return {}
                data = {str(row[0]): row[1] for row in rows}
                delta_alchemy._pending_max = max(row[0] for row in rows)
                return data
            return _make_delta_commit(delta_alchemy)

    else:
        # SQLiteStorage
        import sqlite3 as _sqlite3

        db_path = getattr(storage, "db_path", None)
        conn = _sqlite3.connect(db_path)
        result = conn.execute(
            f"SELECT MAX({id_col}) FROM {table_name}"
        ).fetchone()[0]
        conn.close()
        if result is not None:
            last_max[0] = result

        # Build text expression for multi-column support
        text_expr = _build_sql_text_expr(text_col)

        def _make_delta_commit(fn):
            """Attach deferred commit to a delta function."""
            fn._pending_max = None

            def commit():
                if fn._pending_max is not None:
                    last_max[0] = fn._pending_max
                    fn._pending_max = None

            fn.commit = commit
            return fn

        if date_col:
            def delta_sqlite_sharded():
                import sqlite3
                sql = (
                    f"SELECT {id_col}, {text_expr}, {date_col} "
                    f"FROM {table_name} WHERE {id_col} > ?"
                )
                if where:
                    sql += f" AND ({where})"
                sql += f" ORDER BY {id_col}"
                conn = sqlite3.connect(db_path)
                rows = conn.execute(sql, (last_max[0],)).fetchall()
                conn.close()
                if not rows:
                    return {}, {}
                data = {str(row[0]): row[1] for row in rows}
                dates = {str(row[0]): row[2] for row in rows}
                delta_sqlite_sharded._pending_max = max(row[0] for row in rows)
                return data, dates
            return _make_delta_commit(delta_sqlite_sharded)
        else:
            def delta_sqlite():
                import sqlite3
                sql = f"SELECT {id_col}, {text_expr} FROM {table_name} WHERE {id_col} > ?"
                if where:
                    sql += f" AND ({where})"
                sql += f" ORDER BY {id_col}"
                conn = sqlite3.connect(db_path)
                rows = conn.execute(sql, (last_max[0],)).fetchall()
                conn.close()
                if not rows:
                    return {}
                data = {str(row[0]): row[1] for row in rows}
                delta_sqlite._pending_max = max(row[0] for row in rows)
                return data
            return _make_delta_commit(delta_sqlite)


def _build_delta_fn_universal(
    spec: SourceSpec,
    reader: Any,
    storage: Any,
    shard_manager: Any,
    engine: Any,
) -> Callable:
    """Universal delta: fetch all data → diff against indexed IDs.

    Less efficient than the SQL-level approach (still reads the full
    table/query), but works with **any** source type and correctly
    produces only the new documents for ``add_documents()``.

    When the data_fn returns ``(data, dates)`` tuples (sharded mode),
    the delta also returns ``(new_data, new_dates)``.
    """
    from .data_providers import build_data_fn
    data_fn = build_data_fn(spec, reader, storage, engine.name)

    def delta_universal():
        result = data_fn()

        # Detect sharded mode: data_fn returns (data, dates)
        if isinstance(result, tuple) and len(result) == 2:
            all_data, all_dates = result
            known_ids = set(str(v) for v in shard_manager.id_map.values())
            new_data = {
                k: v for k, v in all_data.items()
                if str(k) not in known_ids
            }
            new_dates = {k: v for k, v in all_dates.items() if k in new_data}
            return new_data, new_dates

        # Non-sharded mode
        all_data = result
        if isinstance(all_data, dict):
            known_ids = set(str(v) for v in engine.id_map.values())
            new_data = {
                k: v for k, v in all_data.items()
                if str(k) not in known_ids
            }
            return new_data
        else:
            current_count = engine.total_docs
            if len(all_data) <= current_count:
                return []
            return all_data[current_count:]

    return delta_universal
