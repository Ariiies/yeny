from .base import BaseStorage
from .json_storage import JSONStorage
from .sqlite_storage import SQLiteStorage
from .metadata_storage import MetadataStorage

# AlchemyStorage and AlchemyReader are lazy-imported to avoid hard dependency on sqlalchemy
def __getattr__(name):
    if name == "AlchemyStorage":
        from .alchemy_storage import AlchemyStorage
        return AlchemyStorage
    if name == "AlchemyReader":
        from .alchemy_reader import AlchemyReader
        return AlchemyReader
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = [
    "BaseStorage",
    "JSONStorage",
    "SQLiteStorage",
    "MetadataStorage",
    "AlchemyStorage",
    "AlchemyReader",
]
