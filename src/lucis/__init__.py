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
from .core.worker import IndexWorker

# Health monitoring (Phase 6 — Resource Protection)
from .core.health import HealthReport, HealthMonitor, health_check

# Shard constants (Phase 5 — Temporal Sharding)
from .core.shard import LUCIS_GLOBAL_SHARD, LUCIS_DEFAULT_DATE_COLUMNS

# Parallel preprocessing (Phase 9 — Multiprocessing)
from .utils.parallel import get_cpu_count, get_optimal_workers

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
    
    # Health
    "HealthReport",
    "HealthMonitor",
    "health_check",
    
    # Shard constants
    "LUCIS_GLOBAL_SHARD",
    "LUCIS_DEFAULT_DATE_COLUMNS",
    
    # Utilities
    "get_engine",
    "HAS_NUMPY",
    "HAS_POLARS",

    # Parallel / CPU awareness
    "get_cpu_count",
    "get_optimal_workers",
    
    # Metadata
    "__version__",
    "__author__",
]