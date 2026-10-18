"""
Auto-selects the fastest available JSON-compatible serializer.

If ``orjson`` is installed it is used automatically (≈ 4× faster
than stdlib ``json`` on large payloads).  Otherwise the standard
library ``json`` module is used — zero mandatory dependencies.

Both backends produce and consume **str** values (not bytes), so
they are drop-in replacements for ``json.dumps`` / ``json.loads``
and fully compatible with SQL TEXT columns.

Usage::

    from yeny.utils.serialization import dumps, loads

    text = dumps({"hello": 42})   # str
    obj  = loads(text)             # dict
"""
from __future__ import annotations

try:
    import orjson as _orjson

    # OPT_NON_STR_KEYS lets orjson accept int dict keys (common in Yeny postings: {doc_id: freq})
    # and serialise them as strings.
    _OPT = _orjson.OPT_NON_STR_KEYS

    def dumps(obj: object) -> str:
        """Serialize *obj* to a JSON ``str`` (orjson backend)."""
        # orjson.dumps returns bytes → decode to str for TEXT columns
        return _orjson.dumps(obj, option=_OPT).decode("utf-8")

    def loads(s: str | bytes) -> object:
        """Deserialize a JSON ``str`` (or bytes) to a Python object."""
        return _orjson.loads(s)

    BACKEND: str = "orjson"

except ImportError:
    import json as _json

    def dumps(obj: object) -> str:          # type: ignore[misc]
        """Serialize *obj* to a JSON ``str`` (stdlib backend)."""
        return _json.dumps(obj)

    def loads(s: str | bytes) -> object:    # type: ignore[misc]
        """Deserialize a JSON ``str`` (or bytes) to a Python object."""
        return _json.loads(s)

    BACKEND: str = "json"                   # type: ignore[no-redef]
