# Package metadata
__version__ = "0.1.1"
__author__ = "Aries Meza"

# Main exportations
from .main import Yeny
from .exceptions import (
    YenyError,
    YenyEmptyCorpusError,
    YenyInvalidDocumentError,
    YenyEngineError,
    YenySearchError,
)

# Models importations
from .models.search import SearchResult, SearchResponse

# Storage backends
from .storage.sqlite_storage import SQLiteStorage
from .storage.metadata_storage import MetadataStorage
from .storage.json_storage import JSONStorage
from .storage.memory_storage import MemoryStorage

# Sync layer (Phase 10 — Modular Architecture)
from .sync.source_spec import SourceSpec

# Worker (Phase 4 — Shadow Indexing)
from .core.worker import IndexWorker

# Health monitoring (Phase 6 — Resource Protection)
from .core.health import HealthReport, HealthMonitor, health_check

# Shard constants (Phase 5 — Temporal Sharding)
from .core.shard import YENY_GLOBAL_SHARD, YENY_DEFAULT_DATE_COLUMNS

# Parallel preprocessing (Phase 9 — Multiprocessing)
from .utils.parallel import get_cpu_count, get_optimal_workers

# AlchemyStorage is lazy-loaded because it requires SQLAlchemy.
def __getattr__(name):
    if name == "AlchemyStorage":
        from .storage.alchemy_storage import AlchemyStorage
        return AlchemyStorage
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

# for better engine exportations
from .engines.plus import get_engine, HAS_NUMPY, HAS_POLARS

__all__ = [
    # main Class
    "Yeny",

    # Models
    "SearchResult",
    "SearchResponse",
    
    # Storage
    "SQLiteStorage",
    "MetadataStorage",
    "JSONStorage",
    "MemoryStorage",
    "AlchemyStorage",
    
    # Exceptions
    "YenyError",
    "YenyEmptyCorpusError", 
    "YenyInvalidDocumentError",
    "YenyEngineError",
    "YenySearchError",
    
    # Worker
    "IndexWorker",

    # Sync
    "SourceSpec",
    
    # Health
    "HealthReport",
    "HealthMonitor",
    "health_check",
    
    # Shard constants
    "YENY_GLOBAL_SHARD",
    "YENY_DEFAULT_DATE_COLUMNS",
    
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
