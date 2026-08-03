"""Small database helper for the example (auxiliary — NOT required reading).

Only data plumbing lives here:

- ``load_env()``            read the local .env into os.environ
- ``get_engine()``          SQLAlchemy engine from DATABASE_URL
- ``ensure_table()``        create the leads table if missing
- ``insert_leads()``        batch insert (encrypting name/email/number)
- ``get_decrypted_lead()``  fetch one row by id, decrypted for display
- ``count_leads()``         row count
- ``truncate_table()``      wipe the scenario

The *database* must exist beforehand; this module only creates the TABLE.
Encryption comes from preprocessor.py — this file contains no crypto logic.
"""
import functools
import itertools
import os
import re

from sqlalchemy import bindparam, create_engine, text

from preprocessor import encrypt_text, try_decrypt

#: Rows are plain dicts.  These are the example's leads columns:
ROW_KEYS = ("reference", "name", "email", "number", "ip", "created_at")

#: Columns encrypted on insert (when present in a row).  Plain-text
#: tables simply don't list these, so nothing is encrypted for them.
ENCRYPTED_COLUMNS = ("name", "email", "number")


def _identifier(name):
    """Sanitize a table/column identifier (it goes into raw SQL)."""
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name or ""):
        raise SystemExit(f"Invalid identifier: {name!r}")
    return name


# ── .env loading ─────────────────────────────────────────────────────────────


def load_env(path=None):
    """Load ``.env`` (next to this file) into ``os.environ``.

    Real environment variables always win — nothing already set is
    overwritten.  Uses python-dotenv when installed, otherwise a tiny
    built-in parser (enough for plain KEY=value files).
    """
    if path is None:
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    if not os.path.isfile(path):
        return
    try:
        from dotenv import load_dotenv

        load_dotenv(path, override=False)
        return
    except ImportError:
        pass
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key, value = key.strip(), value.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = value


def require_env(name):
    """Read a mandatory variable or exit with an actionable message."""
    value = os.environ.get(name, "").strip()
    if not value:
        raise SystemExit(
            f"Missing required setting: {name}\n"
            "  → Copy .env.example to .env and fill it in (see README)."
        )
    return value


# ── Connection / table ───────────────────────────────────────────────────────


def database_url():
    return require_env("DATABASE_URL")


def table_name():
    """Configured table name (sanitized — it goes into raw SQL)."""
    return _identifier(os.environ.get("TABLE_NAME", "leads").strip() or "leads")


@functools.lru_cache(maxsize=1)
def table_columns():
    """Column names of the configured table (cached introspection)."""
    engine = get_engine()
    try:
        with engine.connect() as conn:
            rows = conn.execute(text(f"SHOW COLUMNS FROM {table_name()}")).fetchall()
        return {row[0] for row in rows}
    finally:
        engine.dispose()


def table_exists():
    """True when the configured table exists in the database."""
    engine = get_engine()
    try:
        with engine.connect() as conn:
            row = conn.execute(
                text("SHOW TABLES LIKE :name"), {"name": table_name()}
            ).fetchone()
        return row is not None
    finally:
        engine.dispose()


def get_engine():
    """SQLAlchemy engine for the configured database."""
    return create_engine(database_url(), pool_pre_ping=True)


def ensure_table():
    """Create the EXAMPLE leads table if it does not exist yet.

    This DDL is leads-specific (used by the seed scripts and by the
    playground when TABLE_NAME=leads).  ``created_at`` is NULL-able by
    design: rows without a date land in Lucis' universal shard (9999_99).
    """
    ddl = f"""
    CREATE TABLE IF NOT EXISTS {table_name()} (
        id INT PRIMARY KEY AUTO_INCREMENT,
        reference VARCHAR(64) NULL UNIQUE,
        name TEXT NOT NULL,
        email TEXT NOT NULL,
        number TEXT NOT NULL,
        ip VARCHAR(45) NOT NULL,
        created_at DATETIME NULL
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
    """
    engine = get_engine()
    try:
        with engine.begin() as conn:
            conn.execute(text(ddl))
    finally:
        engine.dispose()


# ── Insertion ────────────────────────────────────────────────────────────────


def _prepare_row(row):
    """Encrypt ENCRYPTED_COLUMNS present in the row; everything else as-is."""
    return {
        key: (
            encrypt_text(str(value))
            if key in ENCRYPTED_COLUMNS and value is not None
            else value
        )
        for key, value in row.items()
    }


def insert_leads(rows, batch_size=1000, skip_duplicates=True, progress=None):
    """Insert row dicts in batches.  Returns ``(inserted, skipped)``.

    With ``skip_duplicates=True`` (default) rows whose ``reference``
    already exists are skipped, batch by batch — re-running any seed
    script is always safe.  (Skipped automatically when the table has no
    ``reference`` column.)  ``progress(inserted, skipped)`` is called
    after every batch if given.
    """
    engine = get_engine()
    has_reference = "reference" in table_columns()
    existing_sql = (
        text(f"SELECT reference FROM {table_name()} WHERE reference IN :refs").bindparams(
            bindparam("refs", expanding=True)
        )
        if has_reference
        else None
    )

    inserted = skipped = 0
    rows_iter = iter(rows)
    try:
        with engine.begin() as conn:
            while True:
                chunk = list(itertools.islice(rows_iter, batch_size))
                if not chunk:
                    break
                existing = set()
                if skip_duplicates and existing_sql is not None:
                    refs = [row["reference"] for row in chunk if row.get("reference")]
                    if refs:
                        existing = {r[0] for r in conn.execute(existing_sql, {"refs": refs})}
                fresh = [row for row in chunk if row.get("reference") not in existing]
                skipped += len(chunk) - len(fresh)
                if fresh:
                    keys = [_identifier(k) for k in fresh[0]]
                    insert_sql = text(
                        f"INSERT INTO {table_name()} ({', '.join(keys)})"
                        f" VALUES ({', '.join(':' + k for k in keys)})"
                    )
                    conn.execute(insert_sql, [_prepare_row(row) for row in fresh])
                    inserted += len(fresh)
                if progress:
                    progress(inserted, skipped)
    finally:
        engine.dispose()
    return inserted, skipped


# ── Reads ────────────────────────────────────────────────────────────────────


def count_leads():
    """Total rows in the table."""
    engine = get_engine()
    try:
        with engine.connect() as conn:
            return int(conn.execute(text(f"SELECT COUNT(*) FROM {table_name()}")).scalar_one())
    finally:
        engine.dispose()


def get_decrypted_lead(doc_id, columns=ROW_KEYS):
    """Fetch one row by id for display (None if missing).

    ``columns`` are the columns to read — pass your table's TEXT_COLUMNS
    for non-leads tables.  Every value goes through ``try_decrypt``,
    which is a no-op for plaintext columns.
    """
    cols = [_identifier(c) for c in columns]
    engine = get_engine()
    try:
        with engine.connect() as conn:
            row = conn.execute(
                text(
                    f"SELECT {', '.join(cols)} FROM {table_name()} WHERE id = :id"
                ),
                {"id": doc_id},
            ).fetchone()
    finally:
        engine.dispose()
    if not row:
        return None
    return {col: try_decrypt(str(value)) if value is not None else "" for col, value in zip(cols, row)}


# ── Cleanup ──────────────────────────────────────────────────────────────────


def truncate_table():
    """Delete every row (structure kept)."""
    engine = get_engine()
    try:
        with engine.begin() as conn:
            conn.execute(text(f"TRUNCATE TABLE {table_name()}"))
    finally:
        engine.dispose()
