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
        return _build_delta_fn_by_id(spec, reader, storage, shard_manager, engine)

    # Universal path: fetch all → diff against known IDs
    return _build_delta_fn_universal(spec, reader, storage, shard_manager, engine)


def _index_max_id(shard_manager: Any, engine: Any) -> Optional[int]:
    """Highest original document id currently present in the index.

    Used to seed the incremental watermark from the **index** rather than
    from the live table, so rows inserted while the worker was down are
    picked up on the first cycle.

    Returns:
        ``int`` — max indexed id (``0`` when the index is genuinely empty,
        so the first cycle fetches the whole table once).  ``None`` — the
        max cannot be determined safely (non-numeric ids, or an ``id_map``
        only partially resident due to lazy/evicted shards).  The caller
        then falls back to the live ``MAX(id)`` seed.
    """
    if shard_manager is not None:
        total = getattr(shard_manager, "total_docs", 0) or 0
        if total <= 0:
            return 0
        # NOTE: do NOT use shard_manager.id_map here — internal doc ids are
        # per-shard (0-based), so the unified view silently drops docs on
        # key collisions.  Iterate each shard's own id_map instead.
        try:
            ids = [
                int(v)
                for shard in shard_manager.shards.values()
                for v in getattr(shard, "id_map", {}).values()
                if v is not None
            ]
        except (TypeError, ValueError):
            return None
    else:
        total = getattr(engine, "total_docs", 0) or 0
        if total <= 0:
            return 0
        id_map = getattr(engine, "id_map", None)
        if id_map is None:
            return None
        try:
            ids = [int(v) for v in id_map.values() if v is not None]
        except (TypeError, ValueError):
            return None

    if len(ids) < total:
        # id_map does not cover every indexed doc (lazy/evicted shards) —
        # a max computed from it could be too low and re-fetch rows that
        # are already indexed, so refuse to seed from it.
        return None
    return max(ids) if ids else 0


def _build_delta_fn_by_id(
    spec: SourceSpec,
    reader: Any,
    storage: Any,
    shard_manager: Any = None,
    engine: Any = None,
) -> Callable:
    """Optimized delta: ``WHERE id > last_max_id`` at the SQL level.

    When a ``date_column`` is present, the returned callable
    produces ``(data, dates)`` tuples for shard routing.

    Uses *reader* for Alchemy sources, falls back to *storage*.

    The ``last_max_id`` watermark is seeded from the **index** (see
    :func:`_index_max_id`) so rows inserted while the worker was down are
    fetched on the first cycle.  When the index cannot provide a safe max,
    it falls back to the live ``MAX(id)`` — the historical behaviour.
    """
    id_col = spec.id_column
    table_name = spec.table_name
    text_col = spec.text_column
    date_col = spec.date_column
    where = spec.where_clause

    # Prefer reader for source DB access
    source = reader if reader else storage
    last_max = [0]
    seed = _index_max_id(shard_manager, engine)

    if hasattr(source, "_engine"):
        # AlchemyReader / AlchemyStorage
        from sqlalchemy import text as _sa_text

        if seed is not None:
            last_max[0] = seed
        else:
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
        if seed is not None:
            last_max[0] = seed
        else:
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
