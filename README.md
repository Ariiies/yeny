# Corpy

> **A minimalist NLP toolkit and search engine generator for Python.**

Corpy is a lightweight, flexible library designed to help developers build and integrate search functionality into their applications with zero friction. 

It follows a "progressive power" philosophy:
1.  **Core Engine**: Starts as a pure Python dependency-free toolkit (perfect for simple use cases or restricted environments).
2.  **Plus Engine**: Upgrades seamlessly to use **NumPy** and **Polars** for high-performance vector operations when available.

## 🚀 Features

-   **Zero Dependencies (Core)**: The base engine runs on standard Python 3.11+. No C-extensions, no heavy libraries.
-   **Optional Performance (Plus)**: Install the `[plus]` extra to unlock SIMD-accelerated computing with NumPy.
-   **Plug-and-Play**: Simple API to ingest data and start searching immediately.
-   **Persistable**: Save and load your indices (currently JSON-based, SQL planned).
-   **Built-in NLP**: Includes efficiently implemented tokenizers (Word, N-gram, Char-gram).

## 📦 Installation

Since this project is currently in private beta, you can install it locally:

```bash
git clone https://github.com/Ariiies/corpy.git
cd corpy

# Install Core (No external dependencies)
pip install .

# Install with Plus features (NumPy + Polars support)
pip install .[plus]
```

## ⚡ Quick Start

### 1. Basic Usage (Core)

```python
from corpy import Corpy

# Your dataset (List or Dict)
documents = {
    "doc1": "Python is amazing for data science and AI",
    "doc2": "Search engines are complex systems",
    "doc3": "Corpy makes building searchers simple"
}

# Initialize and build index
# This automatically chooses the best available engine (Plus if installed, else Core)
cp = Corpy.from_dict(documents, name="demo_index")

# Search!
results = cp.search("python search", top_k=2)

print(results)
# Output:
# SearchResponse(query='python search', tokens=['python', 'search'], engine='CoreEngine', total_results=2, search_time_ms=0.14, results=[SearchResult(doc_id='doc1', score=0.4512, rank=1), SearchResult(doc_id='doc2', score=0.3841, rank=2)])

# You can also get a clean dictionary representation
print(results.to_dict())
# Output:
# {'query': 'python search', 'tokens': ['python', 'search'], 'engine': 'CoreEngine', 'total_results': 2, 'results': [{'doc_id': 'doc1', 'score': 0.4512, 'rank': 1}, ...]}
```

### 2. Persistence

Save your engine to disk and load it later:

```python
# Save the index to 'corpy_data/' (default storage)
cp.save()

# ... later, in another script ...
cp_loaded = Corpy(name="demo_index")
results = cp_loaded.search("data science")
```

## 🏗 Architecture

Corpy is built on a modular architecture:

-   `corpy.engines`: implementation of search algorithms.
    -   `CoreEngine`: Dictionary-based inverted index + Math implementation in pure Python.
    -   `PlusEngine`: Vectorized operations using `numpy.ndarray`.
-   `corpy.storage`: Handles data persistence (currently `JSONStorage`).
-   `corpy.utils`: Reusable NLP utilities (tokenizers, stopword filters).

## 🗺 Roadmap (v0.x -> v1.0)

- [x] **v0.1.0**: Initial release with Core (Dict) and Plus (NumPy) engines. JSON persistence.
- [ ] **v0.2.0**: Enhanced queries (Phrase search `"term1 term2"`, Boolean operators).
- [ ] **v0.3.0**: SQL Persistence backend (SQLite/PostgreSQL) for larger datasets.
- [ ] **v0.4.0**: BM25 Ranking algorithm implementation.
- [ ] **v1.0.0**: Stable API and PyPI release.

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📄 License

[MIT License](LICENSE)
