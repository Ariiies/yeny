from .base import BaseStorage
from .json_storage import JSONStorage
from .sqlite_storage import SQLiteStorage
from .metadata_storage import MetadataStorage
from .memory_storage import MemoryStorage

# SQLAlchemy-backed adapters are lazy-imported to avoid a hard dependency.
def __getattr__(name):
    if name == "AlchemyStorage":
        from .alchemy_storage import AlchemyStorage
        return AlchemyStorage
    if name == "DatabaseReader":
        from .db_reader import DatabaseReader
        return DatabaseReader
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = [
    "BaseStorage",
    "JSONStorage",
    "SQLiteStorage",
    "MetadataStorage",
    "MemoryStorage",
    "AlchemyStorage",
    "DatabaseReader",
]
