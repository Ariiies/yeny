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
    
    # Exceptions
    "LucisError",
    "LucisEmptyCorpusError", 
    "LucisInvalidDocumentError",
    "LucisEngineError",
    "LucisSearchError",
    
    # Utilities
    "get_engine",
    "HAS_NUMPY",
    "HAS_POLARS",
    
    # Metadata
    "__version__",
    "__author__",
]