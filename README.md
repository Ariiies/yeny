<p align="center">
  <img src="assets/lucis_lockup.svg" height="120" align="middle" alt="Lucis Logo">
</p>

[![Sponsor](https://img.shields.io/badge/Sponsor-GitHub-ea4aaa?logo=github)](https://github.com/sponsors/Ariiies)
[![PyPI](https://img.shields.io/pypi/v/lucis)](https://pypi.org/project/lucis/)
[![Python](https://img.shields.io/badge/python-3.10+-blue)](https://www.python.org/)

> A lightweight toolkit for building custom search systems in Python.

### "An easy way to build search engines in Python."

Lucis is a lightweight, production-oriented search toolkit that helps you build full-text search features quickly, while still giving you advanced controls when your dataset grows.

It follows a progressive-power philosophy:
- Start with pure Python and zero mandatory external dependencies.
- Scale to SQL-backed persistence and temporal sharding when needed.
- Keep API ergonomics simple through a single high-level `Lucis` entrypoint.

## Table of Contents

- [Features](#features)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Examples](#examples)
- [Architecture Snapshot](#architecture-snapshot)
- [Why Lucis?](#why-lucis)
- [Documentation](#documentation)
- [Benchmarks](#benchmarks)
- [Testing](#testing)
- [Sponsor](#sponsor)
- [Contributing](#contributing)
- [Roadmap](#roadmap)
- [License](#license)

## Features

- Pure Python engines (`core` and `lite`)
- Built-in NLP preprocessors and tokenizers
- Ranked retrieval with structured response models
- **Binary persistence (`.lcs`)** — memory-mapped index files for near-zero RAM loading, plus lightweight SQLite metadata (WAL mode). Persistence is **automatic** — `from_dict()`, `from_list()`, and `from_table()` all save without calling `.save()`.
- **Direct DB ingestion** — read from SQLite, MySQL, or PostgreSQL tables without polluting your database (read-only adapters, zero `lucis_*` tables on your DB)
- Versioned index persistence with rollback support
- Temporal sharding for large time-series corpora
- Background reindexing with `IndexWorker` (zero-downtime)
- Health and diagnostics reporting
- Standalone utility functions for indexing and vector math
- Optional JSON or full-SQL storage backends for simpler use cases

## Installation

Install from [PyPI](https://pypi.org/project/lucis/):

```bash
pip install lucis
```

Optional SQL support:

```bash
# Generic SQLAlchemy support
pip install lucis[alchemy]

# MySQL
pip install lucis[mysql]

# PostgreSQL
pip install lucis[postgresql]
```

Alternatively, install from source:

```bash
git clone https://github.com/Ariiies/lucis.git
cd lucis
pip install .
```

## Quick Start

```python
from lucis import Lucis

documents = {
    "doc1": "Python is a versatile language for backend systems",
    "doc2": "JavaScript dominates modern frontend development",
    "doc3": "Lucis makes search implementation straightforward",
}

searcher = Lucis.from_dict(documents, name="demo_index", engine="core")
response = searcher.search("python frontend", top_k=2)

print(response)
# Output:
# SearchResponse(
#     query='python frontend',
#     tokens=['python', 'frontend'],
#     engine='CoreEngine',
#     total_results=2,
#     search_time_ms=0.14,
#     results=[
#         SearchResult(doc_id='doc1', score=0.2757, rank=1),
#         SearchResult(doc_id='doc2', score=0.2414, rank=2)
#     ]
# )
```

Factories persist automatically. Reload later with the same logical name:

```python
loaded = Lucis(name="demo_index")
response = loaded.search("python")
```

Advanced infrastructure stays optional and typed:

```python
from lucis import Lucis
from lucis.config import LucisOptions, TableConfig, TableSource

options = LucisOptions(storage_dir="search_data", memory_limit_mb=512)
searcher = Lucis.from_table(
    TableSource(
        table="articles",
        connection_url=DB_URL,
        text_columns=["title", "body"],
        id_column="id",
        date_column="created_at",
    ),
    engine="lite",
    config=TableConfig(where_clause="published = 1"),
    options=options,
)
```

`LucisOptions.binary_dir` accepts `"auto"` (derive `<storage_dir>/lcs`),
`None` (disable `.lcs` persistence), or an explicit directory.

## Examples

Runnable, documented end-to-end scenarios live in [`examples/`](examples/):

- **[Encrypted search over MySQL](examples/encrypted_search/README.md)** —
  full-text search over Fernet-encrypted columns (`name`/`email`/`number`)
  using a blind index of HMAC-trigrams, temporal sharding, `.lcs`
  persistence and an interactive playground. The whole Lucis integration
  fits in ~15 lines inside `playground.py`.

```bash
cd examples/encrypted_search
pip install "../..[encrypted-search-example]"
python seed_controlled_data.py && python playground.py
```

See [`examples/encrypted_search/README.md`](examples/encrypted_search/README.md)
for setup, security model and adaptation guide.

## Architecture Snapshot

```
                  ┌──────────────────┐
                  │  DatabaseReader  │  ← read-only (your DB)
                  │ SQLite / MySQL / │
                  │   PostgreSQL     │
                  └────────┬─────────┘
                           │ data ingestion
                           ▼
Documents → Preprocessors → Engine → Storage
                │                │
                ▼                ▼
          Tokenizers      ┌──────────────┐
          (word, char,    │ .lcs binaries │  ← mmap (index data)
           n-gram)        │  + SQLite WAL │  ← metadata & aliases
                          └──────────────┘
```

- `lucis.main.Lucis`: high-level API and orchestration (Facade pattern)
- `lucis.engines`:
    - `CoreEngine`: TF-IDF + cosine similarity
    - `LiteEngine`: lightweight normalized TF approach
- `lucis.storage`:
    - `MetadataStorage` **(recommended)**: SQLite WAL for metadata + `.lcs` binaries for index data
    - `JSONStorage`: plain `.json` files (simple / debugging)
    - `SQLiteStorage`: full index serialized in SQLite tables
    - `AlchemyStorage`: full index serialized via SQLAlchemy (MySQL, PostgreSQL, etc.)
- `lucis.storage.DatabaseReader`: **read-only** adapter for ingesting from your DB without creating any `lucis_*` tables
- `lucis.worker`: async/periodic reindex worker (zero-downtime)
- `lucis.health`: system and index health reporting
- `lucis.utils`: NLP, indexing helpers, math, serialization, mmap helpers

## Why Lucis?

> **Note:** The comparison below is qualitative. Lucis benchmarks compare its
> own `core` and `lite` engines; they do not benchmark external projects.

| Feature | Lucis | Whoosh | Meilisearch | Elasticsearch |
|---|---|---|---|---|
| **Pure Python (zero deps)** | ✅ | ✅ | ❌ (Rust) | ❌ (Java) |
| **Direct DB table ingestion** | ✅ | ❌ | ❌ | ❌ |
| **Temporal sharding** | ✅ | ❌ | ❌ | ✅ |
| **Background worker** | ✅ | ❌ | ❌ | ✅ |
| **Rollback / versioning** | ✅ | ❌ | ❌ | ✅ |
| **Bilingual docs (EN + ES)** | ✅ | ❌ | ❌ | ❌ |
| **Zero external services** | ✅ | ✅ | ❌ | ❌ |

**Where Lucis shines:**

Lucis is built for **small to medium projects** that need search without the overhead of a full-blown search infrastructure. You don't need to spin up a separate server, configure clusters, or learn a new query DSL — just `pip install lucis` and you're done.

- **Small projects & prototypes** — When your dataset is in the thousands or low millions of documents, Lucis gives you production-quality search without standing up an Elasticsearch or Meilisearch instance.
- **Embedded use cases** — Ideal for CLI tools, desktop apps, or Python backends (Flask, FastAPI) that need search as a library, not a service.
- **High customizability** — Swap tokenizers, inject your own preprocessors, or even bring external NLP libraries (spaCy, NLTK). Lucis adapts to your domain, not the other way around.
- **SQL-native data** — If your data already lives in SQLite, MySQL, or PostgreSQL, Lucis ingests directly from tables or queries — no ETL pipeline needed.
- **Time-series corpora** — Temporal sharding lets you query logs, emails, or articles by date range without loading everything into RAM.

## Documentation

Lucis includes full documentation in Spanish and English.

- [English Index](docs/en/01-index.md)
- [Índice en Español](docs/es/01-index.md)

Useful entry points:

- Getting started: [English](docs/en/02-first-steps.md), [Español](docs/es/02-primeros-pasos.md)
- Lucis object reference: [English](docs/en/03-lucis-object.md), [Español](docs/es/03-objeto-lucis.md)
- API reference: [English](docs/en/15-api-reference.md), [Español](docs/es/15-api-referencia.md)
- Testing guide: [English](docs/en/16-tests.md), [Español](docs/es/16-pruebas.md)
- Benchmark guide: [English](docs/en/17-benchmarks.md), [Español](docs/es/17-benchmarks.md)

## Benchmarks

Lucis includes a deterministic local suite for comparing `CoreEngine` and
`LiteEngine` with the same generated corpus, queries, and tokenizer:

```bash
python -m benchmarks run --profile tiny
```

It measures index construction, public search latency, JSON/SQLite
persistence, `.lcs` serialization and `mmap` loading, artifact size, and
available RSS memory. Results are saved as timestamped JSON so runs can be
validated and compared without overwriting previous data.

These benchmarks measure speed, resource use, and persistence fidelity—not
search relevance or performance against other projects. See the
[English guide](docs/en/17-benchmarks.md), the
[guía en español](docs/es/17-benchmarks.md), or the
[runner quick reference](benchmarks/README.md).

## Testing

```bash
python -m pytest -q
```

## Sponsor

Lucis is an open-source project. If this toolkit has saved you time or helped you build robust search features, consider supporting its ongoing development and maintenance.

💝 [Sponsor Lucis on GitHub](https://github.com/sponsors/Ariiies)

## Contributing

Contributions are welcome. Open an issue or submit a pull request.

## Roadmap

These features are planned for future releases. Contributions and feedback are welcome!

### Engines

| Engine | Status | Description |
|---|---|---|
| **BM25Engine** | 🧪 Planned | BM25 relevance scoring — better IDF saturation and document length normalization than TF-IDF. Ideal for general-purpose search. |
| **NumpyEngine** | 🧪 Planned | NumPy-accelerated vector operations — SIMD-optimized `batch_cosine_similarity`, dense TF-IDF matrices, and `top_k` via `argpartition`. Install with `pip install lucis[plus]`. |
| **PolarsEngine** | 🔬 Research | Polars-powered parallel index construction for massive corpora. Streaming ingestion with lazy DataFrames. |

### Features

| Feature | Status | Description |
|---|---|---|
| **Fuzzy & typo-tolerant search** | 🧪 Planned | Built-in Levenshtein/Damerau-Levenshtein matching integrated into both engines. |
| **Faceted search** | 🔬 Research | Filter results by metadata fields (category, date, author) alongside full-text scoring. |
| **Multi-language stemming** | 🔬 Research | Stemming support for Spanish, English, French, and more via optional `nltk`/`stanza` integration. |

> **Legend:** 🧪 Planned = actively planned, 🔬 Research = exploring feasibility

## License

[MIT License](LICENSE)
