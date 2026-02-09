# Package metadata
__version__ = "0.1.0"
__author__ = "Luis Aries Meza Castillo"

# Main exportations
from .main import Corpy
from .exceptions import (
    CorpyError,
    CorpyEmptyCorpusError,
    CorpyInvalidDocumentError,
    CorpyEngineError,
    CorpySearchError,
)

# Models importations
from .models.search import SearchResult, SearchResponse

# for better engine exportations
from .engines.plus import get_engine, HAS_NUMPY, HAS_POLARS

__all__ = [
    # main Class
    "Corpy",

    # Models
    "SearchResult",
    "SearchResponse",
    
    # Exceptions
    "CorpyError",
    "CorpyEmptyCorpusError", 
    "CorpyInvalidDocumentError",
    "CorpyEngineError",
    "CorpySearchError",
    
    # Utilities
    "get_engine",
    "HAS_NUMPY",
    "HAS_POLARS",
    
    # Metadata
    "__version__",
    "__author__",
]