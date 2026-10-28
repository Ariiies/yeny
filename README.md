<p align="center">
  <img src="https://raw.githubusercontent.com/Ariiies/yeny/main/assets/yeny_lockup3.png" height="120" align="middle" alt="Yeny Logo">
</p>

<p align="center">
  <a href="https://github.com/sponsors/Ariiies"><img src="https://img.shields.io/badge/Sponsor-GitHub-ea4aaa?logo=github" alt="Sponsor"></a>
  <a href="https://pypi.org/project/yeny/"><img src="https://img.shields.io/pypi/v/yeny" alt="PyPI"></a>
  <a href="https://www.python.org/"><img src="https://img.shields.io/badge/python-3.10+-blue" alt="Python"></a>
</p>

<p align="center">
  <b>🌐 Language / Idioma:</b> &nbsp;
  <strong>English</strong> &nbsp;|&nbsp;
  <a href="https://github.com/Ariiies/yeny/blob/main/README.es.md">Español</a>
</p>

> A lightweight toolkit for building custom search systems in Python.

### "An easy way to build search engines in Python."

Yeny is a lightweight, production-oriented search toolkit that helps you build full-text search features quickly, while still giving you advanced controls when your dataset grows.

It follows a progressive-power philosophy:
- Start with pure Python and zero mandatory external dependencies.
- Scale to SQL-backed persistence and temporal sharding when needed.
- Keep API ergonomics simple through a single high-level `Yeny` entrypoint.

## Table of Contents

- [Features](#features)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Examples](#examples)
- [Architecture Snapshot](#architecture-snapshot)
- [Why Yeny?](#why-yeny)
- [Documentation](#documentation)
- [Benchmarks](#benchmarks)
- [Testing](#testing)
- [Sponsor](#sponsor)
- [Contributing](#contributing)
- [Roadmap](#roadmap)
- [Dedication](#dedication)
- [License](#license)

## Features

- Pure Python engines (`core` and `lite`)
- Built-in NLP preprocessors and tokenizers
- Ranked retrieval with structured response models
- **Binary persistence (`.yny`)** — memory-mapped index files for near-zero RAM loading, plus lightweight SQLite metadata (WAL mode). Persistence is **automatic** — `from_dict()`, `from_list()`, and `from_table()` all save without calling `.save()`.
- **Direct DB ingestion** — read from SQLite, MySQL, or PostgreSQL tables without polluting your database (read-only adapters, zero `yeny_*` tables on your DB)
- Versioned index persistence with rollback support
- Temporal sharding for large time-series corpora
- Background reindexing with `IndexWorker` (zero-downtime)
- Health and diagnostics reporting
- Standalone utility functions for indexing and vector math
- Optional JSON or full-SQL storage backends for simpler use cases

## Installation

Install from [PyPI](https://pypi.org/project/yeny/):

```bash
pip install yeny
```

Optional SQL support:

```bash
# Generic SQLAlchemy support
pip install yeny[alchemy]

# MySQL
pip install yeny[mysql]

# PostgreSQL
pip install yeny[postgresql]
```

Alternatively, install from source:

```bash
git clone https://github.com/Ariiies/yeny.git
cd yeny
pip install .
```

## Quick Start

```python
from yeny import Yeny

documents = {
    "doc1": "Python is a versatile language for backend systems",
    "doc2": "JavaScript dominates modern frontend development",
    "doc3": "Yeny makes search implementation straightforward",
}

searcher = Yeny.from_dict(documents, name="demo_index", engine="core")
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

Factories persist automatically by default, generating the `yeny_data/yny/` directory with `.yny` binaries and SQLite metadata (`yeny_meta.db`). Reload later with the same logical name:

```python
loaded = Yeny(name="demo_index")
response = loaded.search("python")
```

For unit tests, quick prototyping, or zero-disk ephemeral environments, run 100% in-memory:

```python
searcher = Yeny.from_list(["hello world"], persist=False)  # or options=YenyOptions(storage_type=None)
response = searcher.search("hello")
```

Advanced infrastructure stays optional and typed:

```python
from yeny import Yeny
from yeny.config import YenyOptions, TableConfig, TableSource

options = YenyOptions(storage_dir="search_data", memory_limit_mb=512)
searcher = Yeny.from_table(
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

`YenyOptions.binary_dir` accepts `"auto"` (derive `<storage_dir>/yny`),
`None` (disable `.yny` persistence), or an explicit directory.

## Examples

Runnable, documented end-to-end scenarios live in [`examples/`](https://github.com/Ariiies/yeny/tree/main/examples):

- **[Encrypted search over MySQL](https://github.com/Ariiies/yeny/blob/main/examples/encrypted_search/README.md)** —
  full-text search over Fernet-encrypted columns (`name`/`email`/`number`)
  using a blind index of HMAC-trigrams, temporal sharding, `.yny`
  persistence and an interactive playground. The whole Yeny integration
  fits in ~15 lines inside `playground.py`.

```bash
cd examples/encrypted_search
pip install "../..[encrypted-search-example]"
python seed_controlled_data.py && python playground.py
```

See [`examples/encrypted_search/README.md`](https://github.com/Ariiies/yeny/blob/main/examples/encrypted_search/README.md)
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
          (word, char,    │ .yny binaries │  ← mmap (index data)
           n-gram)        │  + SQLite WAL │  ← metadata & aliases
                          └──────────────┘
```

- `yeny.main.Yeny`: high-level API and orchestration (Facade pattern)
- `yeny.engines`:
    - `CoreEngine`: TF-IDF + cosine similarity
    - `LiteEngine`: lightweight normalized TF approach
- `yeny.storage`:
    - `MetadataStorage` **(recommended)**: SQLite WAL for metadata + `.yny` binaries for index data
    - `JSONStorage`: plain `.json` files (simple / debugging)
    - `SQLiteStorage`: full index serialized in SQLite tables
    - `AlchemyStorage`: full index serialized via SQLAlchemy (MySQL, PostgreSQL, etc.)
- `yeny.storage.DatabaseReader`: **read-only** adapter for ingesting from your DB without creating any `yeny_*` tables
- `yeny.worker`: async/periodic reindex worker (zero-downtime)
- `yeny.health`: system and index health reporting
- `yeny.utils`: NLP, indexing helpers, math, serialization, mmap helpers

## Why Yeny?

> **Note:** The comparison below is qualitative. Yeny benchmarks compare its
> own `core` and `lite` engines; they do not benchmark external projects.

| Feature | Yeny | Whoosh | Meilisearch | Elasticsearch |
|---|---|---|---|---|
| **Pure Python (zero deps)** | ✅ | ✅ | ❌ (Rust) | ❌ (Java) |
| **Direct DB table ingestion** | ✅ | ❌ | ❌ | ❌ |
| **Temporal sharding** | ✅ | ❌ | ❌ | ✅ |
| **Background worker** | ✅ | ❌ | ❌ | ✅ |
| **Rollback / versioning** | ✅ | ❌ | ❌ | ✅ |
| **Bilingual docs (EN + ES)** | ✅ | ❌ | ❌ | ❌ |
| **Zero external services** | ✅ | ✅ | ❌ | ❌ |

**Where Yeny shines:**

Yeny is built for **small to medium projects** that need search without the overhead of a full-blown search infrastructure. You don't need to spin up a separate server, configure clusters, or learn a new query DSL — just `pip install yeny` and you're done.

- **Small projects & prototypes** — When your dataset is in the thousands or low millions of documents, Yeny gives you production-quality search without standing up an Elasticsearch or Meilisearch instance.
- **Embedded use cases** — Ideal for CLI tools, desktop apps, or Python backends (Flask, FastAPI) that need search as a library, not a service.
- **High customizability** — Swap tokenizers, inject your own preprocessors, or even bring external NLP libraries (spaCy, NLTK). Yeny adapts to your domain, not the other way around.
- **SQL-native data** — If your data already lives in SQLite, MySQL, or PostgreSQL, Yeny ingests directly from tables or queries — no ETL pipeline needed.
- **Time-series corpora** — Temporal sharding lets you query logs, emails, or articles by date range without loading everything into RAM.

## Documentation

Yeny includes full documentation in Spanish and English.

- [English Index](https://github.com/Ariiies/yeny/blob/main/docs/en/01-index.md)
- [Índice en Español](https://github.com/Ariiies/yeny/blob/main/docs/es/01-index.md)

Useful entry points:

- Getting started: [English](https://github.com/Ariiies/yeny/blob/main/docs/en/02-first-steps.md), [Español](https://github.com/Ariiies/yeny/blob/main/docs/es/02-primeros-pasos.md)
- Yeny object reference: [English](https://github.com/Ariiies/yeny/blob/main/docs/en/03-yeny-object.md), [Español](https://github.com/Ariiies/yeny/blob/main/docs/es/03-objeto-yeny.md)
- API reference: [English](https://github.com/Ariiies/yeny/blob/main/docs/en/15-api-reference.md), [Español](https://github.com/Ariiies/yeny/blob/main/docs/es/15-api-referencia.md)
- Testing guide: [English](https://github.com/Ariiies/yeny/blob/main/docs/en/16-tests.md), [Español](https://github.com/Ariiies/yeny/blob/main/docs/es/16-pruebas.md)
- Benchmark guide: [English](https://github.com/Ariiies/yeny/blob/main/docs/en/17-benchmarks.md), [Español](https://github.com/Ariiies/yeny/blob/main/docs/es/17-benchmarks.md)

## Benchmarks

Yeny includes a deterministic local suite for comparing `CoreEngine` and
`LiteEngine` with the same generated corpus, queries, and tokenizer:

```bash
python -m benchmarks run --profile tiny
```

It measures index construction, public search latency, JSON/SQLite
persistence, `.yny` serialization and `mmap` loading, artifact size, and
available RSS memory. Results are saved as timestamped JSON so runs can be
validated and compared without overwriting previous data.

These benchmarks measure speed, resource use, and persistence fidelity—not
search relevance or performance against other projects. See the
[English guide](https://github.com/Ariiies/yeny/blob/main/docs/en/17-benchmarks.md), the
[guía en español](https://github.com/Ariiies/yeny/blob/main/docs/es/17-benchmarks.md), or the
[runner quick reference](https://github.com/Ariiies/yeny/blob/main/benchmarks/README.md). The published cross-platform
campaign, raw results, generated reports, and presentation are available in
the [benchmark documentation package](https://github.com/Ariiies/yeny/blob/main/docs/benchmarks/README.md).

## Testing

```bash
python -m pytest -q
```

## Sponsor

Yeny is an open-source project. If this toolkit has saved you time or helped you build robust search features, consider supporting its ongoing development and maintenance.

💝 [Sponsor Yeny on GitHub](https://github.com/sponsors/Ariiies)

## Contributing

Contributions are welcome. Open an issue or submit a pull request.

## Roadmap

Development moves step by step—prioritizing pure-Python ergonomics first, while progressively building optional native acceleration in parallel.

### Planned Engines (Pure Python)

| Engine | Status | Description |
|---|---|---|
| **BM25Engine** | 🧪 Planned | BM25 relevance scoring — better IDF saturation and document length normalization than TF-IDF. Ideal for general-purpose search. |
| **NanoEngine / CountEngine** | 🧪 Planned | Ultra-lightweight raw term-frequency (bag-of-words) engine with zero normalization overhead. Built for maximum speed in simple keyword-matching scenarios alongside `LiteEngine`. |

### Parallel Track: Rust Acceleration

| Component | Status | Description |
|---|---|---|
| **Rust Core & Tokenizers** | 🦀 In Progress | Gradual integration of optional Rust bindings (via PyO3) developed in parallel to accelerate tokenization, inverted index construction, and scoring kernels while keeping the pure-Python fallback intact. |

### Tentative / Future Exploration

- 🔬 **Fuzzy & typo-tolerant search:** Built-in Levenshtein/Damerau-Levenshtein matching integrated into the search pipeline.
- 🔬 **Faceted search:** Filter results by metadata fields (category, date, author) alongside full-text scoring.
- 🔬 **Multi-language stemming:** Optional stemming support for Spanish, English, and more.

> **Legend:** 🧪 Planned = next in the pipeline · 🦀 In Progress = parallel track · 🔬 Tentative = long-term exploration

## Dedication

> **In loving memory of my mother, Yeny.**
>
> This project is named after her as a tribute to her life, her warmth, and everything she taught me. Every line of code in **Yeny** is shared freely with the developer community in her honor—so that her name continues to build, connect, and help others create. ❤️

## License

[MIT License](https://github.com/Ariiies/yeny/blob/main/LICENSE)
