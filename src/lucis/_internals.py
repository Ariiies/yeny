"""
Internal shared utilities for the Lucis facade and its mixins.
Not part of the public API — used to break circular imports between
main.py and the mixin modules.
"""
from .engines.core import CoreEngine
from .engines.lite import LiteEngine

# ── Engine registry ──
# Maps friendly names to engine classes.
# As new engines are added, register them here.
_ENGINE_REGISTRY = {
    "core": CoreEngine,
    "lite": LiteEngine,
}

# ── Lazy import flags ──
_AlchemyStorage = None
_AlchemyReader = None


def _get_alchemy_storage_class():
    """Lazy-load ``AlchemyStorage`` to avoid a hard dependency on SQLAlchemy.

    Returns:
        The :class:`~lucis.storage.AlchemyStorage` class, imported on
        first call and cached globally afterwards.
    """
    global _AlchemyStorage
    if _AlchemyStorage is None:
        from .storage.alchemy_storage import AlchemyStorage
        _AlchemyStorage = AlchemyStorage
    return _AlchemyStorage


def _get_alchemy_reader_class():
    """Lazy-load ``AlchemyReader`` to avoid a hard dependency on SQLAlchemy."""
    global _AlchemyReader
    if _AlchemyReader is None:
        from .storage.alchemy_reader import AlchemyReader
        _AlchemyReader = AlchemyReader
    return _AlchemyReader


def _build_sql_text_expr(text_column):
    """Build a raw SQL expression for single or multi-column text.

    Used for SQLite raw SQL queries.  Concatenates multiple columns
    with spaces using ``||`` and wraps each in ``COALESCE(col, '')``
    to handle NULLs.

    Args:
        text_column: A single column name (str) or list of column names.

    Returns:
        A SQL expression string.
    """
    if isinstance(text_column, str):
        return text_column
    if len(text_column) == 1:
        return text_column[0]
    coalesced = [f"COALESCE({col}, '')" for col in text_column]
    return " || ' ' || ".join(coalesced)
