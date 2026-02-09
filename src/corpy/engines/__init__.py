"""Exports para el submódulo engines."""

from .core import CoreEngine
from .plus import get_engine, HAS_NUMPY, HAS_POLARS

__all__ = [
    "CoreEngine",
    "get_engine",
    "HAS_NUMPY",
    "HAS_POLARS",
]
