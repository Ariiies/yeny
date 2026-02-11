# Package metadata
__version__ = "0.1.0"
__author__ = "Aries Meza"

# Main exportations
from .main import Lucis
from .exceptions import (
    LucisError,
    LucisEmptyCorpusError,
    LucisInvalidDocumentError,
    LucisEngineError,
    LucisSearchError,
)

# Models importations
from .models.search import SearchResult, SearchResponse

# Storage backends
from .storage.sqlite_storage import SQLiteStorage

# Worker (Phase 4 — Shadow Indexing)
from .worker import IndexWorker

# AlchemyStorage is lazy-loaded (requires sqlalchemy)
def __getattr__(name):
    if name == "AlchemyStorage":
        from .storage.alchemy_storage import AlchemyStorage
        return AlchemyStorage
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

# for better engine exportations
from .engines.plus import get_engine, HAS_NUMPY, HAS_POLARS

__all__ = [
    # main Class
    "Lucis",

    # Models
    "SearchResult",
    "SearchResponse",
    
    # Storage
    "SQLiteStorage",
    "AlchemyStorage",
    
    # Exceptions
    "LucisError",
    "LucisEmptyCorpusError", 
    "LucisInvalidDocumentError",
    "LucisEngineError",
    "LucisSearchError",
    
    # Worker
    "IndexWorker",
    
    # Utilities
    "get_engine",
    "HAS_NUMPY",
    "HAS_POLARS",
    
    # Metadata
    "__version__",
    "__author__",
]