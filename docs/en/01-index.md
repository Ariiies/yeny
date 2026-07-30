# Lucis

> **A minimalist NLP toolkit and search engine generator for Python.**

Lucis is a lightweight and flexible library designed to help developers build and integrate search functionality into their applications with zero friction.

Follows a philosophy of **"progressive power"**:

1. **No dependencies**: The core runs on pure Python 3.11+. No C extensions, no heavy libraries.
2. **Plug-and-Play**: Simple API to ingest data and start searching immediately.
3. **Persistent**: Save and load your indexes (JSON, SQLite, MySQL, PostgreSQL).
4. **Integrated NLP**: Includes efficient tokenizers (Word, N-gram, Char-gram).

---

## Installation

```bash
# Instalar el núcleo (sin dependencias externas)
pip install lucis

# Instalar con soporte para bases de datos SQL (MySQL, PostgreSQL, etc.)
pip install lucis[alchemy]

# MySQL
pip install lucis[mysql]

# PostgreSQL
pip install lucis[postgresql]
```

## Quick example

```python
from lucis import Lucis

# Tu dataset (diccionario o lista)
documentos = {
    "doc1": "Python es increíble para ciencia de datos e IA",
    "doc2": "Los motores de búsqueda son sistemas complejos",
    "doc3": "Lucis hace simple construir buscadores"
}

# Inicializar y construir índice
buscador = Lucis.from_dict(documentos, name="mi_indice")

# ¡Buscar!
resultados = buscador.search("python búsqueda", top_k=2)
print(resultados)
```

**Output:**

```
SearchResponse(
    query='python búsqueda',
    tokens=['python', 'búsqueda'],
    engine='CoreEngine',
    total_results=2,
    search_time_ms=0.14,
    results=[
        SearchResult(doc_id='doc1', score=0.275692, rank=1),
        SearchResult(doc_id='doc2', score=0.241425, rank=2)
    ]
)
```

---

## Documentation

### Getting started
- [First steps](02-first-steps.md) — Your first search engine in 5 lines
- [The Lucis class](03-lucis-object.md) — Complete reference of the main object

### Fundamental concepts
- [Search Engines](04-engines.md) — CoreEngine vs LiteEngine
- [Preprocessors](05-preprocessors.md) — Custom tokenizers, cleaners, and pipelines
- [Storage](06-storage.md) — JSON, SQLite, MySQL, PostgreSQL

### Modular tools
- [Useful Functions](07-utility-functions.md) — Standalone Toolkit: build_index, bag of words, TF-IDF, cosine similarity
- [Tests](16-tests.md) — How to run the suite, coverage and test structure
- [Test Guide](16-tests.md) — Folder by folder, commands and recommended flow for contributors
- [Benchmarks](17-benchmarks.md) — Reproducible Core/Lite measurements and result interpretation

### Advanced features
- [Temporary Sharding](08-temporary-sharding.md) — Monthly partitioning for large datasets
- [IndexWorker](09-worker.md) — Automatic background reindexing
- [Health Monitoring](10-health.md) — RAM monitoring, timing and diagnostics

### Technical reference
- [How it works](11-how-it-works.md) — Internals: inverted index, .lcs format, math
- [Data Models](12-data-models.md) — SearchResult, SearchResponse, HealthReport
- [Exceptions](13-exceptions.md) — Error handling
- [Recipes](14-recipes.md) — Complete practical examples
- [API Reference](15-api-reference.md) — Comprehensive reference of all functions
- [Tests](16-tests.md) — System tests and unit tests
- [Benchmarks](17-benchmarks.md) — Profiles, metrics, commands and limitations

---

## License

MIT License — [Luis Aries Meza Castillo](https://github.com/Ariiies)
