# Yeny Architecture Reference

This document provides a concise, technical reference for engineers and AI agents working on **Yeny**. It details system design, component boundaries, execution invariants, and extension points grounded directly in the codebase.

---

## 1. System Overview & Design Philosophy

Yeny is a modular full-text search toolkit built around a **progressive-power philosophy**:
- **Zero-Dependency Core:** Core indexing, search algorithms, NLP tokenizers, and binary memory-mapped persistence run on pure Python 3.10+ using only standard-library modules (`dataclasses`, `array`, `mmap`, `struct`, `sqlite3`, `json`).
- **Optional Infrastructure:** Advanced storage adapters (e.g., MySQL, PostgreSQL) and external data ingestion rely on optional extras (`sqlalchemy`, `pymysql`, `psycopg2-binary`) that are lazily imported on demand.
- **Future Native Acceleration:** A parallel development track incorporates optional Rust extensions (via PyO3) for compute-intensive tokenization and inverted index kernels without compromising the pure-Python fallback.
- **Ergonomic Facade:** All ingestion methods, search pipelines, background maintenance, and persistence mechanics are surfaced through a unified facade (`Yeny`), configured via immutable dataclasses.

---

## 2. High-Level Pattern: Facade + Mixins

The primary entry point is `yeny.Yeny` (`src/yeny/main.py`). Rather than maintaining a monolithic class, `Yeny` orchestrates four specialized mixins via multiple inheritance:

```
                          ┌────────────────────────┐
                          │       yeny.Yeny        │
                          │   (src/yeny/main.py)   │
                          └───────────┬────────────┘
                                      │
         ┌────────────────────────────┼────────────────────────────┬────────────────────────────┐
         ▼                            ▼                            ▼                            ▼
┌──────────────────┐         ┌──────────────────┐         ┌──────────────────┐         ┌──────────────────┐
│   LoaderMixin    │         │   SearchMixin    │         │ PersistenceMixin │         │ AutomationMixin  │
│ (mixins/loaders) │         │ (mixins/search)  │         │ (mixins/persist) │         │ (mixins/auto)    │
└──────────────────┘         └──────────────────┘         └──────────────────┘         └──────────────────┘
```

- **`LoaderMixin` (`src/yeny/mixins/loaders/`):** Consolidates factory class methods (`from_dict`, `from_list`, `from_sqlite_table`, `from_sqlite_query`, `from_table`, `from_query`) partitioned across `BasicLoadersMixin`, `SQLiteLoadersMixin`, and `DatabaseLoadersMixin`.
- **`SearchMixin` (`src/yeny/mixins/search.py`):** Coordinates query preprocessing, shard routing/preloading, engine scoring, and structuring responses into `SearchResponse` containing `SearchResult` objects.
- **`PersistenceMixin` (`src/yeny/mixins/persistence.py`):** Manages `.save()`, `.load()`, `.rollback()`, version generation, logical alias pointers, and `.yny` binary exports.
- **`AutomationMixin` (`src/yeny/mixins/automation.py`):** Drives mutating operations (`index`, `reindex`, `reindex_streaming`, `reindex_async`, `add_documents`, `remove_documents`), creates `IndexWorker` instances, and provisions health monitoring.

### Decoupling via `_internals.py`
To prevent circular imports between `main.py` and mixins, internal shared state resides in `src/yeny/_internals.py`:
- **`_ENGINE_REGISTRY`:** Maps engine identifiers (`"core"`, `"lite"`) to their concrete classes.
- **Lazy Loaders:** `_get_alchemy_storage_class()` and `_get_database_reader_class()` defer importing optional dependencies until explicitly requested.
- **SQL Utilities:** `_build_sql_text_expr()` generates raw multi-column concatenation expressions for database queries.

---

## 3. Core Subsystems & Responsibilities

```
src/yeny/
├── main.py              # Facade entrypoint composing mixins
├── config.py            # Immutable configuration dataclasses
├── _internals.py        # Engine registry, lazy loaders, SQL helpers
├── exceptions.py        # Domain exception hierarchy
├── mixins/              # Facade mixin implementations
│   ├── loaders/         # Ingestion factories (dict, list, sqlite, db)
│   ├── search.py        # Query execution & response wrapping
│   ├── persistence.py   # Versioning, aliases, save/load orchestration
│   └── automation.py    # Reindexing, background tasks, sync
├── engines/             # Inverted index & scoring kernels
│   ├── base.py          # BaseEngine abstract contract
│   ├── core.py          # CoreEngine (TF-IDF + cosine similarity, .yny/mmap supported)
│   ├── lite.py          # LiteEngine (Normalized TF, .yny/mmap supported)
│   └── plus.py          # Optional vectorized engines (NumpyEngine, PolarsEngine) & selector factory
├── storage/             # Index persistence backends & ingestion
│   ├── base.py          # BaseStorage universal interface
│   ├── metadata_storage.py # SQLite WAL for metadata + .yny binaries
│   ├── memory_storage.py   # Zero-disk ephemeral RAM backend
│   ├── sqlite_storage.py   # Full SQLite database storage
│   ├── json_storage.py     # Flat JSON file storage
│   ├── alchemy_storage.py  # SQLAlchemy storage (MySQL/PostgreSQL)
│   └── db_reader.py        # Read-only external database adapter
├── core/                # Advanced lifecycle & runtime infrastructure
│   ├── shard.py         # ShardManager (temporal partitioning & LRU cache)
│   ├── worker.py        # IndexWorker (zero-downtime shadow rebuilder)
│   └── health.py        # Diagnostic metrics & memory inspection
├── sync/                # Auto-sync specification & query generators
│   └── source_spec.py   # SourceSpec dataclass for ingestion origins
├── models/              # Structured result models (SearchResponse, SearchResult)
└── utils/               # Internal computational building blocks
    ├── nlp/             # Tokenizers (Word, CharNgram, Simple) & normalizers
    ├── compact.py       # CompactPostings & CompactDocLengths (array.array)
    ├── mmap_storage.py  # .yny binary format encoder, decoder & YnyHandle
    ├── math/            # Vector norms, dot products, sorting
    ├── index/           # Inverted index construction & IDF computation
    └── parallel.py      # Multiprocessing text preprocessing
```

### Key Subsystems Detailed
1. **`config.py`:**
   - `YenyOptions`: Shared infrastructure configuration (`storage_dir`, `storage_type`, `db_path`, `connection_url`, `max_loaded_shards`, `memory_limit_mb`, `binary_dir`).
   - `TableSource`: Target table, connection URL, column mapping (`text_columns`, `id_column`, `date_column`).
   - `TableConfig`: Ingestion parameters (`where_clause`, `schema`, `shard_batch_size`, `stream_ordered`).
2. **`engines/`:**
   - `CoreEngine`: TF-IDF relevance with cosine similarity. Maintains inverted index with `CompactPostings` and precomputes scalar L2 norms (`doc_norms`). Fully supports `.yny` binary persistence and zero-copy `mmap` loading via `YnyHandle`. Default tokenizer: `WordTokenizer`.
   - `LiteEngine`: Normalized Term Frequency scoring (`score = sum(tf(t, d) / |d|)`). Eliminates IDF and vector overhead for maximum throughput and minimal memory. Fully supports `.yny` binary persistence and zero-copy `mmap` loading via `YnyHandle`. Default tokenizer: `CharNgramTokenizer(3)` with lowercase.
   - `plus.py`: Optional acceleration layer offering `NumpyEngine` (SIMD matrix operations) and `PolarsEngine` (lazy columnar processing for large corpora), with availability flags (`HAS_NUMPY`, `HAS_POLARS`) and the `get_engine(preference="auto")` selector factory. Gated behind optional dependencies (`pip install yeny[plus]` / numpy / polars).
3. **`storage/`:**
   - `MetadataStorage` **(Recommended Default):** Stores aliases, document counts, and shard registries in SQLite (`yeny_meta.db` with WAL mode). Heavy posting data is offloaded to `.yny` binaries.
   - `MemoryStorage`: Completely in-memory heap storage (`dict`), leaving no filesystem traces.
   - `DatabaseReader`: Read-only SQLAlchemy adapter for streaming external rows without modifying the source database.
4. **`core/`:**
   - `ShardManager`: Partitions corpora into monthly buckets (`YYYY_MM`, or `9999_99` for undated records). Enforces shard caching policies via `max_loaded_shards` and `memory_limit_mb`.
   - `IndexWorker`: Executes periodic or change-driven shadow index builds in a daemon thread, swapping aliases upon completion.
   - `health.py`: Measures object footprints via recursive `_deep_getsizeof`, inspecting active shards, process RSS, and engine stats.
5. **`utils/compact.py` & `utils/mmap_storage.py`:**
   - `CompactPostings`: Stores postings as two sorted, parallel arrays (`array.array('i')` doc IDs, `array.array('I')` frequencies) using `bisect` lookups, consuming ~8 bytes per entry instead of ~100 bytes in standard dicts.
   - `.yny` Format: Binary representation consisting of a 4-byte magic signature (`b"YNY\x01"`), uint32 header length, 4096-byte aligned JSON metadata header, and contiguous array payloads read via `mmap` and `memoryview`.

---

## 4. Key Architectural Invariants

Agents and contributors must maintain these strict architectural guarantees:

1. **Default Persistence Guarantee:**
   - Factories default to `MetadataStorage` (SQLite WAL `yeny_meta.db`) paired with `.yny` binary files.
   - Updates generate timestamped physical versions (e.g., `<name>__v<timestamp>`).
   - Logical alias pointers (`yeny_aliases`) are updated atomically, enabling instantaneous rollbacks via `yn.rollback()`.
2. **Zero-Disk Ephemeral Execution:**
   - Setting `persist=False`, `storage_type=None`, or `storage_type="memory"` routes all state into `MemoryStorage`.
   - Under this mode, `binary_dir` is forced to `None`, ensuring zero files or directories are created on disk. Ideal for test suites.
3. **Read-Only Database Ingestion:**
   - `DatabaseReader` and `from_table` / `from_query` treat external relational databases strictly as read-only data providers.
   - Under no circumstances does Yeny execute DDL/DML, create `yeny_*` metadata tables, or write temporary artifacts into external production databases.
4. **Preprocessor Consistency:**
   - The preprocessor callable assigned or defaulted during index construction is permanently bound to the instance (`yn.preprocessor`).
   - The identical transformation pipeline is automatically applied to search queries to guarantee identical tokenization in the vector space.
5. **Post-Build Memory Hygiene:**
   - Building an index consumes transient RAM for raw strings, dictionaries, and token lists.
   - `Yeny._post_index_cleanup()` flushes build-time structures and reloads compact/mmap representations from storage, clearing `functools.lru_cache` on preprocessors and invoking `gc.collect()`.

---

## 5. Extension Points

### 1. Adding a New Engine
1. Inherit from `BaseEngine` in `src/yeny/engines/base.py`:
   ```python
   from yeny.engines.base import BaseEngine

   class CustomEngine(BaseEngine):
       @property
       def name(self) -> str:
           return "CustomEngine"

       def build_index(self, corpus: list[str] | dict[Any, str]) -> None:
           texts, self.id_map = self._normalize_corpus(corpus)
           # Construct index structures...

       def search(self, query: str | list[str], top_k: int = 10) -> list[tuple[Any, float]]:
           # Return ranked list of (doc_id, score)...
   ```
2. Register the engine class in `_ENGINE_REGISTRY` (`src/yeny/_internals.py`):
   ```python
   _ENGINE_REGISTRY["custom"] = CustomEngine
   ```

### 2. Adding a New Storage Backend
1. Inherit from `BaseStorage` in `src/yeny/storage/base.py`:
   ```python
   from yeny.storage.base import BaseStorage

   class CustomStorage(BaseStorage):
       def save(self, engine_state: dict[str, Any], name: str) -> None:
           ...
       def load(self, name: str) -> dict[str, Any]:
           ...
       def exists(self, name: str) -> bool:
           ...
   ```
2. If the storage supports zero-downtime swaps and versioning, override `resolve_alias`, `set_alias`, `get_alias`, `list_aliases`, and `load_shard_registry`.

### 3. Injecting a Custom Tokenizer / Preprocessor
Provide any callable adhering to `(str) -> Union[str, List[str]]`:
```python
# Function returning tokens directly:
yn = Yeny(name="custom_tok", preprocessor=lambda text: text.split())

# Function returning normalized string (Yeny applies SimpleTokenizer automatically):
yn = Yeny(name="custom_cleaner", preprocessor=lambda text: text.lower().strip())
```
