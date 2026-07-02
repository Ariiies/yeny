# Temporary sharding

When your dataset contains millions of dated documents, loading everything into RAM is not feasible. Lucis **temporary sharding** automatically partitions documents into monthly shards (`YYYY_MM`), so that only the shards relevant to a query are loaded into memory.

---

## Architecture

```
┌─────────────┐
│   Lucis     │
│  (Facade)   │
└──────┬──────┘
       │
┌──────▼──────┐
│ShardManager │
└──────┬──────┘
       │
┌──────┼───────────┬───────────┐
▼      ▼           ▼           ▼
2024_01  2024_02  2024_03  9999_99
Engine   Engine   Engine   Engine
(shard)  (shard)  (shard)  (global)
```

Each shard is a separate instance of the engine (CoreEngine or LiteEngine) with its own inverted index. The `9999_99` shard is the **global shard**: it contains documents without a date or whose date could not be parsed.

---

## Enable sharding

Sharding is automatically enabled when you provide dates in your data:

```python
from lucis import Lucis

data = {
    "doc_1": "Lanzamiento del producto alfa",
    "doc_2": "Actualización de seguridad crítica",
    "doc_3": "Informe trimestral Q3",
}
dates = {
    "doc_1": "2024-01-15",
    "doc_2": "2024-03-22",
    "doc_3": "2024-03-28",
}

luc = Lucis(name="noticias", engine="lite")
luc.index(data, dates=dates)
```

This will create three shards: `2024_01`, `2024_03`, and `9999_99` (empty in this case).

### Date column auto-detection

When you use the `from_sqlite_table`, `from_alchemy_table`, or `from_*_query` methods, Lucis tries to detect the date column automatically by looking for columns named:

1. `created_at`
2. `updated_at`
3. `timestamp`

```python
# Auto-detección: busca "created_at", "updated_at", "timestamp"
luc = Lucis.from_sqlite_table(
    db_path="app.db",
    table_name="articulos",
    text_column="contenido",
    date_column="auto",       # ← activa auto-detección
)
```

If you prefer to specify the column:

```python
luc = Lucis.from_sqlite_table(
    db_path="app.db",
    table_name="articulos",
    text_column="contenido",
    date_column="fecha_publicacion",    # ← columna explícita
)
```

---

## Search with temporary filters

```python
# Todos los shards
resultados = luc.search("seguridad")

# Solo documentos de marzo 2024
resultados = luc.search("seguridad", since="2024-03", until="2024-03")

# Desde enero 2024 en adelante
resultados = luc.search("seguridad", since="2024-01")

# Hasta febrero 2024
resultados = luc.search("seguridad", until="2024-02")
```

The `since` and `until` filters accept:
- Direct shard keys: `"2024_01"`
- ISO year-month: `"2024-01"`
- Complete dates: `"2024-01-15"` (truncated to month: `2024_01`)
- Objects `datetime` and `date`

> The global shard (`9999_99`) is **always** included in the search, regardless of filters, because it contains undated documents that might be relevant.

---

## Memory management

For very large datasets, you can limit how many shards are kept loaded simultaneously:

### Quantity limit

```python
luc = Lucis(
    name="logs_idx",
    engine="lite",
    max_loaded_shards=6,    # ← máximo 6 shards en RAM
)
```

When a new shard is needed and there are already 6 loaded, the oldest one (LRU) is automatically evicted.

### Limit per RAM

```python
luc = Lucis(
    name="logs_idx",
    engine="lite",
    memory_limit_mb=2048,   # ← máximo 2 GB para shards
)
```

Shards are evicted when the sum of their estimated RAM exceeds the limit.

### Combination

You can use both limits — whichever is reached first triggers the eviction:

```python
luc = Lucis(
    name="logs_idx",
    engine="lite",
    max_loaded_shards=12,
    memory_limit_mb=4096,
)
```

### TTL of temporary shards

Shards loaded by a `since`/`until` filter receive a TTL (default 30 seconds). After that time, they are automatically evicted:

```python
luc = Lucis(
    name="logs_idx",
    engine="lite",
    max_loaded_shards=6,
    temp_ttl_seconds=60,    # ← mantener shards filtrados 60s
)
```

---

## Streaming indexing

For datasets larger than 100K rows, use `reindex_streaming` to avoid loading everything into RAM:

```python
luc = Lucis.from_alchemy_table(
    alchemy_url="mysql+pymysql://user:pass@host/db",
    table_name="articulos",
    text_column="contenido",
    date_column="fecha",
    engine="lite",
    max_loaded_shards=6,
    memory_limit_mb=2048,
)

# Streaming: consume filas en lotes, indexa shard por shard
def row_stream():
    return storage.stream_table_with_dates(
        "articulos", text_column="contenido", date_column="fecha"
    )

luc.reindex_streaming(row_stream())
```

If your data arrives **in chronological order**, enable `stream_ordered=True` to evict completed shards during ingestion:

```python
luc.reindex_streaming(row_stream(), stream_ordered=True)
```

> **⚠️ Caution**: Only use `stream_ordered=True` if you are sure that the data arrives ordered by date. With messy data, shards will close prematurely and lose documents.

---

## Utility functions

```python
from lucis.core.shard import date_to_shard_key, normalize_to_shard_key, shard_key_in_range

# Convertir fecha a clave de shard
date_to_shard_key("2024-03-15")          # "2024_03"
date_to_shard_key(None)                   # "9999_99"

# Normalizar filtros
normalize_to_shard_key("2024-03")         # "2024_03"
normalize_to_shard_key("2024-03-15")      # "2024_03"
normalize_to_shard_key("2024_03")         # "2024_03"

# ¿Está un shard en rango?
shard_key_in_range("2024_03", since="2024_01", until="2024_06")  # True
shard_key_in_range("2023_12", since="2024_01")                    # False
shard_key_in_range("9999_99", since="2024_01")                    # True (siempre)
```

---

## Shard persistence

When saving a sharded index, each shard is persisted independently:

```python
# Guardar — cada shard se serializa por separado
luc.save()

# Los archivos se nombran automáticamente:
# mi_idx__v20240315_120000__shard__2024_01.json
# mi_idx__v20240315_120000__shard__2024_02.json
# mi_idx__v20240315_120000__shard__9999_99.json

# Cargar — también carga shard por shard (lazy si hay memory management)
luc.load()
```

With `.lcs` binary storage, each shard generates its own file:

```
lucis_data/lcs/
  mi_idx__v20240315_120000__shard__2024_01.lcs
  mi_idx__v20240315_120000__shard__2024_02.lcs
  ...
```

`.lcs` files are loaded via **memory-mapped I/O** (mmap): the operating system loads them on demand, without consuming additional RAM from the Python heap.

---

## Next step

- [IndexWorker](09-worker.md) — Automatic background reindexing
- [Health Monitoring](10-health.md) — RAM and shard diagnostics