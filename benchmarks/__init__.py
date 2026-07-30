"""Small, reproducible benchmark infrastructure for Lucis.

The package exposes deterministic data/query generation and the configuration
models needed by the command-line runner. Benchmark execution remains outside
the production ``lucis`` package.
"""

from .config import BenchmarkProfile, BenchmarkRunConfig, load_profiles
from .datasets import DatasetManifest, GeneratedDataset, generate_dataset
from .queries import GeneratedQueries, QueryManifest, QuerySpec, build_queries

__all__ = [
    "BenchmarkProfile",
    "BenchmarkRunConfig",
    "DatasetManifest",
    "GeneratedDataset",
    "GeneratedQueries",
    "QueryManifest",
    "QuerySpec",
    "build_queries",
    "generate_dataset",
    "load_profiles",
]
