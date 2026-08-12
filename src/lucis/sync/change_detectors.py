"""
Change detector factories for the IndexWorker.

A change detector is a no-argument callable that returns ``True`` when
the source data has changed since the last check.  Supports deferred
commit semantics so the worker can confirm changes only after a
successful rebuild cycle.
"""
from typing import Any, Callable, Optional

from .source_spec import SourceSpec


def build_change_detector(
    spec: SourceSpec,
    reader: Any,
    storage: Any,
    shard_manager: Any,
    engine: Any,
    is_indexed: bool,
) -> Optional[Callable]:
    """Auto-generate a count-based change detector from a SourceSpec.

    Works for both ``"table"`` sources (uses ``count_rows``) and
    ``"query"`` sources (wraps the original query in
    ``SELECT COUNT(*) FROM (…)``).

    Uses *reader* for database sources, then falls back to *storage*.
    """
    if spec is None:
        return None

    # Prefer reader for source DB access
    source = reader if reader else storage
    if shard_manager is not None:
        last_count = [shard_manager.total_docs]
    else:
        last_count = [engine.total_docs if is_indexed else 0]

    def _make_detector(fetch_count)->Callable[[], bool]:
        """Wrap a count-fetcher into a detector with deferred commit."""
        def detector():
            current = fetch_count()
            if current != last_count[0]:
                detector._pending = current
                detector._pending_count = current
                return True
            detector._pending = None
            detector._pending_count = None
            return False

        detector._pending = None
        detector._last_count = last_count[0]
        detector._pending_count = None
        detector._supports_deletion_detection = True

        def commit():
            if detector._pending is not None:
                last_count[0] = detector._pending
                detector._last_count = last_count[0]
                detector._pending = None
                detector._pending_count = None

        detector.commit = commit
        return detector

    if spec.type == "table":
        table_name = spec.table

        # Enhanced table detector: if id_column exists, track COUNT + MAX(id)
        # so mixed "delete + insert" cycles are detected even when count
        # remains unchanged.
        if spec.id_column:
            id_col = spec.id_column
            where = spec.where_clause
            last_max = [0]

            def _fetch_count_max_table():
                if hasattr(source, "_engine"):
                    from sqlalchemy import text as _sa_text
                    sql = f"SELECT COUNT(*), MAX({id_col}) FROM {table_name}"
                    if where:
                        sql += f" WHERE ({where})"
                    with source._engine.connect() as conn:
                        row = conn.execute(
                            _sa_text(sql)
                        ).fetchone()
                    cnt = int(row[0] or 0)
                    mx = int(row[1] or 0)
                    return cnt, mx
                import sqlite3
                db_path = getattr(source, "db_path", None)
                sql = f"SELECT COUNT(*), MAX({id_col}) FROM {table_name}"
                if where:
                    sql += f" WHERE ({where})"
                conn = sqlite3.connect(db_path)
                row = conn.execute(sql).fetchone()
                conn.close()
                cnt = int(row[0] or 0)
                mx = int(row[1] or 0)
                return cnt, mx

            # Seed only the MAX(id) fingerprint from the live table.  The
            # count baseline intentionally keeps the *indexed* doc count
            # (set above), so a drift introduced while the worker was down
            # (DB rows != indexed docs) fires on the very first cycle and
            # gets reconciled incrementally by the delta.
            _, m0 = _fetch_count_max_table()
            last_max[0] = m0

            def detector_table_count_max():
                current_count, current_max = _fetch_count_max_table()
                changed = (
                    current_count != last_count[0]
                    or current_max != last_max[0]
                )
                if changed:
                    detector_table_count_max._pending = current_count
                    detector_table_count_max._pending_count = current_count
                    detector_table_count_max._pending_max_id = current_max
                    return True
                detector_table_count_max._pending = None
                detector_table_count_max._pending_count = None
                detector_table_count_max._pending_max_id = None
                return False

            detector_table_count_max._pending = None
            detector_table_count_max._last_count = last_count[0]
            detector_table_count_max._pending_count = None
            detector_table_count_max._last_max_id = last_max[0]
            detector_table_count_max._pending_max_id = None
            detector_table_count_max._supports_deletion_detection = True

            def commit_table_count_max():
                if detector_table_count_max._pending is not None:
                    last_count[0] = detector_table_count_max._pending
                    detector_table_count_max._last_count = last_count[0]
                    detector_table_count_max._pending = None
                    detector_table_count_max._pending_count = None
                if detector_table_count_max._pending_max_id is not None:
                    last_max[0] = detector_table_count_max._pending_max_id
                    detector_table_count_max._last_max_id = last_max[0]
                    detector_table_count_max._pending_max_id = None

            detector_table_count_max.commit = commit_table_count_max
            return detector_table_count_max

        return _make_detector(lambda: source.count_rows(table_name))

    elif spec.type == "query":
        query_str = spec.query

        if hasattr(source, "_engine"):
            from sqlalchemy import text as _sa_text

            def _fetch_alchemy():
                with source._engine.connect() as conn:
                    return conn.execute(
                        _sa_text(
                            f"SELECT COUNT(*) FROM ({query_str}) AS _lucis_subq"
                        )
                    ).scalar()

            return _make_detector(_fetch_alchemy)

        else:
            db_path = getattr(source, "db_path", None)

            def _fetch_sqlite()->int:
                import sqlite3
                conn = sqlite3.connect(db_path)
                current = conn.execute(
                    f"SELECT COUNT(*) FROM ({query_str})"
                ).fetchone()[0]
                conn.close()
                return current

            return _make_detector(_fetch_sqlite)

    return None
