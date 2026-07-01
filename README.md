# Lucis

> A minimalist NLP toolkit and search engine generator for Python.

Lucis is a lightweight, production-oriented search toolkit that helps you build full-text search features quickly, while still giving you advanced controls when your dataset grows.

It follows a progressive-power philosophy:
- Start with pure Python and zero mandatory external dependencies.
- Scale to SQL-backed persistence and temporal sharding when needed.
- Keep API ergonomics simple through a single high-level `Lucis` entrypoint.

## Features

- Pure Python engines (`core` and `lite`)
- Built-in NLP preprocessors and tokenizers
- Ranked retrieval with structured response models
- Multiple storage backends:
    - JSON
    - SQLite
    - SQLAlchemy-compatible databases (including MySQL and PostgreSQL)
- Versioned index persistence with rollback support
- Temporal sharding for large time-series corpora
- Background reindexing with `IndexWorker`
- Health and diagnostics reporting
- Standalone utility functions for indexing and vector math

## Installation

Install from source:

```bash
git clone https://github.com/Ariiies/lucis.git
cd lucis
pip install .
```

Optional SQL support:

```bash
# Generic SQLAlchemy support
pip install .[alchemy]

# MySQL
pip install .[mysql]

# PostgreSQL
pip install .[postgresql]
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
print(response.to_dict())
```

Persist and reload:

```python
searcher.save()

# Later...
loaded = Lucis(name="demo_index")
response = loaded.search("python")
```

## Architecture Snapshot

- `lucis.main.Lucis`: high-level API and orchestration
- `lucis.engines`:
    - `CoreEngine`: TF-IDF + cosine similarity
    - `LiteEngine`: lightweight normalized TF approach
- `lucis.storage`:
    - `JSONStorage`
    - `SQLiteStorage`
    - `AlchemyStorage`
    - metadata/versioning layers
- `lucis.worker`: async/periodic reindex worker
- `lucis.health`: system and index health reporting
- `lucis.utils`: NLP, indexing helpers, math, serialization, mmap helpers

## Documentation

Lucis includes full documentation in Spanish and English.

- [English Index](docs/en/01-index.md)
- [Indice en Español](docs/es/01-index.md)

Useful entry points:

- Getting started: [English](docs/en/02-first-steps.md), [Español](docs/es/02-primeros-pasos.md)
- Lucis object reference: [English](docs/en/03-lucis-object.md), [Español](docs/es/03-objeto-lucis.md)
- API reference: [English](docs/en/15-api-reference.md), [Español](docs/es/15-api-referencia.md)
- Testing guide: [English](docs/en/16-tests.md), [Español](docs/es/16-pruebas.md)

## Testing

```bash
python -m pytest -q
```

## Contributing

Contributions are welcome. Open an issue or submit a pull request.

## License

[MIT License](LICENSE)
