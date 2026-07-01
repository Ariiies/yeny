# Search engines

Lucis includes two search engines with different performance profiles. Both work in pure Python, with no external dependencies.

---

## CoreEngine — The heart of Lucis

`CoreEngine` is the main engine. It implements **Full TF-IDF with cosine similarity**, making it ideal when the accuracy of the results is most important.

```python
from lucis import Lucis

buscador = Lucis.from_dict(datos, name="preciso", engine="core")
```

### How does it work?

1. **Indexing**: Build a compact inverted index and pre-calculate the L2 norms of each document.
2. **Search**: Constructs a TF-IDF query vector on-the-fly, finds candidate documents and calculates cosine similarity.

### Default Tokenizer

`word_tokenizer` — Extracts only words (ignores numbers, converts to lowercase).

```python
from lucis.utils.nlp import word_tokenizer

word_tokenizer("Python 3.11 es increíble!")
# → ["python", "es", "increíble"]
```

### When to use CoreEngine

- Searches where **precise relevance** matters
- Small to medium corpus
- When you don't need incremental indexing

> **📐 Mathematical Note — TF-IDF and Cosine Similarity**
>
> **Normalized Term Frequency:**
> ```
> tf(t, d) = count(t, d) / |d|
> ```
> Where `count(t,d)` is how many times the term `t` appears in the document `d`, and `|d|` is the total number of tokens in the document.
>
> **Inverse Document Frequency (smoothed):**
> ```
> idf(t) = log((N + 1) / (df(t) + 1)) + 1
> ```
> Where `N` is the total number of documents and `df(t)` is the number of documents containing `t`.
>
> **TF-IDF:**
> ```
> tfidf(t, d) = tf(t, d) × idf(t)
> ```
>
> **Cosine Similarity:**
> ```
> cos(A, B) = (A · B) / (||A|| × ||B||)
> ```
> The final score is the cosine of the angle between the query vector and the vector of each document. 1.0 = identical, 0.0 = unrelated.

---

## LiteEngine — Light and fast

`LiteEngine` is a minimalist engine that uses only **Normalized Term Frequency**. No IDF, no cosine similarity. This makes it significantly lighter on RAM and disk.

```python
from lucis import Lucis

buscador = Lucis.from_dict(datos, name="rapido", engine="lite")
```

### How does it work?

The score for each document is simply:

```
score(d, Q) = Σ tf(t, d) / |d|   para cada término t en la query Q
```

There are no vectors, there is no IDF. It only counts how many times the query terms appear in each document, normalized by the length of the document.

### Default Tokenizer

`char_ngram_tokenizer(3)` with lowercase — Generates character trigrams, ideal for fuzzy search.

```python
from lucis.utils.nlp import char_ngram_tokenizer

tokenizer = char_ngram_tokenizer(3)
tokenizer("python")
# → ["pyt", "yth", "tho", "hon"]
```

This means that LiteEngine works well with typos and partial matches.

### When to use LiteEngine

- **Large volume** of documents where speed matters more than perfect accuracy
- **Limited RAM** — uses significantly less memory
- **Fuzzy search** — char n-grams tokenizer tolerates typos
- **Incremental indexing** — supports `add_documents()` and `remove_documents()`

> **📐 Mathematical Note — Normalized TF**
>
> ```
> score(d, Q) = Σ  tf(t, d) / |d|
> ```
>
> Where:
> - `tf(t, d)` = raw count of term `t` in document `d`
> - `|d|` = total tokens in document `d`
> - The sum is over all the `t` terms that appear in both the query `Q` and the document `d`

---

## Comparative table

| Feature | CoreEngine | LiteEngine |
|---|---|---|
| **Algorithm** | TF-IDF + Cosine Similarity | Normalized TF |
| **Precision** | ⭐⭐⭐ High | ⭐⭐ Good |
| **RAM Usage** | Moderate | Low |
| **Speed** | Quick | Very fast |
| **Dependencies** | None | None |
| **Tokenizer default** | `word_tokenizer` | `char_ngram(3)` |
| **`add_documents()`** | No | Yes |
| **`remove_documents()`** | No | Yes |
| **Best for** | Precision | Volume + Fuzzy |

---

## Standalone use of the engine

The motors are independent components. You can import and use them directly without the `Lucis` class, if you only need the search primitives:

```python
from lucis.engines import CoreEngine

# Crear engine directamente
engine = CoreEngine()

# Indexar
engine.build_index({
    "doc1": "Python es versátil",
    "doc2": "JavaScript domina el frontend",
    "doc3": "Python y JS son populares"
})

# Buscar (retorna lista de tuplas)
resultados = engine.search("python frontend", top_k=2)
for doc_id, score in resultados:
    print(f"  {doc_id}: {score:.4f}")
```

```python
from lucis.engines import LiteEngine

engine = LiteEngine()
engine.build_index(["documento uno", "documento dos", "documento tres"])

resultados = engine.search("uno tres", top_k=2)
for doc_id, score in resultados:
    print(f"  {doc_id}: {score:.4f}")
```

This is useful when you want to integrate just the search logic into your own application, without persistence or orchestration.

---

<!-- 
## 🔮 Coming soon — Optimized engines (Plus)

In future versions, Lucis will include optimized engines that will take advantage
NumPy for SIMD vectorized operations and Polars for processing 
parallel of large corpora:

- **NumpyEngine**: batch_cosine_similarity, TF-IDF array
- **PolarsEngine**: parallel build_index for massive corpora

Install with: `pip install lucis[plus]`
-->

## Next step

- [Preprocessors](preprocesadores.md) — Customize tokenization and text cleansing
- [Useful Functions](funciones-utiles.md) — Use search primitives as a standalone toolkit