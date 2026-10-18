# Data models

Yeny uses immutable dataclasses (`frozen=True`) to represent search results. This ensures integrity after creation, autocompletion in the IDE, and direct JSON serialization.

---

##SearchResult

Represents a single document found in a search.

```python
from yeny.models.search import SearchResult
```

| Field | Type | Description |
|---|---|---|
| `doc_id` | `DocId` | Original identifier of the document (preserves the input type: `str`, `int`, etc.) |
| `score` | `float` | Similarity score between query and document (0.0 to 1.0 for CoreEngine) |
| `rank` | `int` | Position in the results list (1-based, most relevant first) |
| `shard_key` | `Optional[str]` | Temporary shard key (e.g. `"2024_02"`). `None` for indexes without sharding. |

### Example

```python
resultado = response.results[0]

print(resultado.doc_id)      # "articulo_42"
print(resultado.score)       # 0.8734
print(resultado.rank)        # 1
print(resultado.shard_key)   # "2024_03" o None
```

> `SearchResult` is immutable (frozen). You cannot modify its fields after creation.

---

##SearchResponse

Complete response to a search, with context about the query, the engine, times and results.

```python
from yeny.models.search import SearchResponse
```

| Field | Type | Description |
|---|---|---|
| `query` | `Union[str, List[str]]` | The query as it was received |
| `tokens` | `List[str]` | Tokens actually used for the search (after preprocessing) |
| `engine` | `str` | Engine name (`"CoreEngine"` or `"LiteEngine"`) |
| `total_results` | `int` | Number of documents found |
| `search_time_ms` | `float` | Search time in milliseconds |
| `results` | `List[SearchResult]` | Ordered list of results |
| `shards_searched` | `int` | Number of shards consulted (0 = no sharding) |
| `total_shards` | `int` | Total shards in the index (0 = no sharding) |

### Example

```python
from yeny import Yeny

yn = Yeny(name="demo", engine="core")
yn.index({"a": "python web framework", "b": "java enterprise"})

response = yn.search("python")

# Metadata
print(response.query)            # "python"
print(response.tokens)           # ["python"]
print(response.engine)           # "CoreEngine"
print(response.total_results)    # 1
print(response.search_time_ms)   # 0.42

# Shards (0 cuando no hay sharding)
print(response.shards_searched)  # 0
print(response.total_shards)     # 0

# Iterar resultados
for r in response.results:
    print(f"  #{r.rank} {r.doc_id} → {r.score:.4f}")

# Acceso dict-like
print(response["total_results"])  # 1

# Serialización
data = response.to_dict()        # dict JSON-ready
```

---

## HealthReport

Health snapshot of a Yeny instance. Documented in detail in [Health Monitoring](10-health.md).

```python
from yeny.core.health import HealthReport
```

| Field | Type | Description |
|---|---|---|
| `timestamp` | `str` | Report date/time |
| `index_name` | `str` | Logical index name |
| `engine_name` | `str` | Engine in use |
| `is_indexed` | `bool` | If the index is constructed |
| `is_sharded` | `bool` | If you use temporary sharding |
| `total_docs` | `int` | Total documents |
| `index_ram_bytes` | `int` | Index RAM in bytes |
| `process_rss_bytes` | `Optional[int]` | Process RSS |
| `disk_yny_bytes` | `int` | .yny file size |
| `disk_meta_bytes` | `int` | DB metadata size |
| `shard_count` | `int` | Loaded Shards |
| `shards` | `List[ShardHealth]` | Detail by shard |
| `worker_running` | `bool` | If the worker is active |
| `worker_cycles` | `int` | Completed cycles |
| `worker_rebuilds` | `int` | Successful rebuilds |
| `worker_errors` | `int` | Failed rebuilds |
| `worker_last_rebuild_time` | `Optional[float]` | Duration of last rebuild(s) |
| `search_benchmark_ms` | `Optional[float]` | Benchmark latency |

Derived properties: `index_ram_human`, `process_rss_human`, `disk_total_bytes`, `disk_total_human`.

---

## ShardHealth

RAM statistics for an individual shard. Documented in [Temporary Sharding](08-temporary-sharding.md).

```python
from yeny.core.health import ShardHealth
```

| Field | Type | Description |
|---|---|---|
| `shard_key` | `str` | Temporary shard key |
| `total_docs` | `int` | Documents in the shard |
| `index_size_bytes` | `int` | Inverted Index RAM |
| `doc_lengths_size_bytes` | `int` | Document Lengths RAM |
| `id_map_size_bytes` | `int` | ID Map RAM |
| `doc_norms_size_bytes` | `int` | Standards RAM (CoreEngine; 0 for Lite) |
| `total_size_bytes` | `int` | Total sum |

---

## Next step

- [Exceptions](13-exceptions.md) — Error hierarchy
- [API Reference](15-api-reference.md) — Full signatures