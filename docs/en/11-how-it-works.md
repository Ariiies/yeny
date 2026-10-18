# How Yeny works

This page explains the internals of the search engine: what data structures are built, how relevance is calculated, and how memory is optimized.

---

##Inverted index

The heart of Yeny is an **inverted index**: a dictionary that maps each vocabulary word to the list of documents where it appears, along with its frequency.

### Conceptual example

Given the corpus:

| doc\_id | text |
|---|---|
| 0 | "python is great" |
| 1 | "python dominates the web" |
| 2 | "java is great too" |

The resulting inverted index would be:

```
"python"   → {0: 1, 1: 1}
"es"       → {0: 1, 2: 1}
"genial"   → {0: 1, 2: 1}
"domina"   → {1: 1}
"la"       → {1: 1}
"web"      → {1: 1}
"java"     → {2: 1}
"también"  → {2: 1}
```

Each entry (`{doc_id: frecuencia}`) is called **posting list**.

### O(n) Construction

`build_index` builds the index in a single traversal of the corpus:

1. For each document, the frequencies of each token (Bag of Words) are counted.
2. Each `(token, doc_id, freq)` pair is inserted into the inverted index.
3. Posting lists are compressed to `CompactPostings` (see below).

---

## CompactPostings — Efficient posting lists

Instead of Python dictionaries (`{doc_id: freq}`), Yeny stores each posting list as two ordered parallel arrays:

```
CompactPostings:
  _doc_ids:  [0, 1, 42, 999, ...]     ← array.array('i'), ordenados
  _freqs:    [2, 1,  5,   3, ...]     ← array.array('I'), paralelo
```

**Why?**

| Structure | RAM per entry | Lookup |
|---|---|---|
| `dict` Python | ~100 bytes | O(1) |
| `CompactPostings` | ~8 bytes | O(log n) bisect |

At an index of 2M documents, this reduces RAM from ~3.5 GB to ~300–400 MB (**~90% savings**). The lookup for bisect is O(log n), but the adjacent layout in memory is much more cache-friendly.

The interface supports dictionaries:

```python
# CompactPostings se comporta como dict read-only
postings.get(42)       # frecuencia del doc 42, o 0
postings.keys()        # array de doc_ids
postings.items()       # iterador (doc_id, freq)
42 in postings         # True/False
postings.to_dict()     # {42: 5, 999: 3, ...} — dict regular
```

---

##CompactDocLengths

Document lengths (total number of tokens) also use a compact array instead of a dictionary:

```
CompactDocLengths:
  _data: array.array('I', [15, 23, 8, 42, ...])
  # índice = doc_id, valor = longitud
```

O(1) lookup by direct indexing. Same RAM savings as CompactPostings.

---

## Relevance calculation

### CoreEngine — TF-IDF + Cosine Similarity

The `CoreEngine` implements the classic TF-IDF model with cosine similarity:

**1. Term Frequency (TF)** — local weight of the term in the document:

$$TF(t, d) = \frac{f(t, d)}{|d|}$$

Where $f(t, d)$ is the number of times the term $t$ appears in document $d$, and $|d|$ is the total length of the document.

**2. Inverse Document Frequency (IDF)** — overall term weight:

$$IDF(t) = \log\left(\frac{N + 1}{df(t) + 1}\right) + 1$$

Where $N$ is the total number of documents and $df(t)$ is the number of documents containing $t$. Smoothing (+1) prevents division by zero.

**3. TF-IDF**:

$$TF\text{-}IDF(t, d) = TF(t, d) \times IDF(t)$$

**4. Cosine Similarity**:

$$\text{sim}(q, d) = \frac{\vec{q} \cdot \vec{d}}{|\vec{q}| \times |\vec{d}|}$$

CoreEngine pre-calculates document norms (`doc_norms`) during indexing, so searching only needs to:
1. Tokenize the query.
2. Calculate the TF-IDF vector of the query (sparse — only the present terms).
3. Calculate the dot product with each candidate document.
4. Divide by the pre-calculated norms.

### LiteEngine — TF Normalized

The `LiteEngine` uses simpler and faster scoring:

$$\text{score}(q, d) = \sum_{t \in q} \frac{f(t, d)}{|d|}$$

It does not calculate IDF or document standards. This makes it faster but less accurate for queries with rare terms.

---

## Binary format .yny

For ultra-efficient persistence, Yeny can save shards in binary `.yny` (Yeny Compact Storage) format that is loaded via memory-mapped I/O:

```
┌────────────────────────────────────┐
│ Header: magic + version + offsets  │
├────────────────────────────────────┤
│ Vocabulary: tokens (UTF-8)         │
├────────────────────────────────────┤
│ Posting data: doc_ids + freqs      │
│ (arrays de enteros compactados)    │
├────────────────────────────────────┤
│ Doc lengths array                  │
├────────────────────────────────────┤
│ ID map (original → internal)       │
└────────────────────────────────────┘
```

**Advantages of mmap:**

- **Almost instantaneous loading**: The OS maps the file without copying it to RAM.
- **RAM on demand**: Only accessed pages are loaded into physical memory.
- **Shared between processes**: Multiple workers can read the same `.yny`.

`.yny` files are generated automatically when you save an index with `generate_yny()` or during indexing with binary storage.

---

## Shadow indexing — Reindexing without downtime

When you call `reindex()`, Yeny does not destroy the active index. Instead:

1. **Create a new version** with a versioned physical name (e.g. `mi_idx__v20240315_120000`).
2. **Builds the index** in the background on the new version.
3. **Swap the alias** — the logical name (`mi_idx`) points to the new version.
4. **Searches are never interrupted** — during the rebuild they used the previous version.

This is the mechanism underlying both `reindex()` and `IndexWorker`.

---

## Parallelism

Yeny uses `concurrent.futures.ThreadPoolExecutor` to parallelize expensive operations:

- **Multi-shard search**: Each shard is searched in an independent thread, the results are merged and re-ranked.
- **Persistence**: Shards are saved in parallel.

The number of workers is automatically configured according to the available cores.

---

## Next step

- [Data Models](12-data-models.md) — SearchResult, SearchResponse
- [API Reference](15-api-reference.md) — All signatures and parameters