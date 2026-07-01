# The Lucis class

`Lucis` is the main orchestrator of the library. Implements the **Facade pattern**: connect search engines, storage and tokenizers behind a clean and minimal API.

There are three ways to create an instance:

1. **From data** — `Lucis.from_dict()` or `Lucis.from_list()`
2. **Load existing** — `Lucis(name="mi_indice")` (auto-load if exists)
3. **Empty** — `Lucis(name="nuevo", autoload=False)` and then `.index(data)`

---

## Builder

```python
from lucis import Lucis

buscador = Lucis(
    name="mi_indice",              # Identificador para persistencia
    storage_dir="lucis_data",      # Directorio para archivos JSON
    storage_type="json",           # "json", "sqlite" o "alchemy"
    engine="core",                 # "core" o "lite"
    preprocessor=None,             # Callable (str) → str | list[str]
    autoload=True,                 # Cargar automáticamente si existe
    max_loaded_shards=0,           # 0 = cargar todos los shards
    memory_limit_mb=None,          # Límite de RAM para shards
    binary_dir="auto",             # Directorio para archivos .lcs
)
```

### Main parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `name` | `str` | `"default"` | Index name, used for persistence |
| `storage_type` | `str` | `"json"` | Backend: `"json"`, `"sqlite"` or `"alchemy"` |
| `engine` | `str` | `"core"` | Engine: `"core"` (TF-IDF) or `"lite"` (TF) |
| `preprocessor` | `Callable` | `None` | Custom text preprocessor |
| `autoload` | `bool` | `True` | Auto-load existing index when instantiating |
| `storage_dir` | `str` | `"lucis_data"` | Folder for JSON storage |
| `db_path` | `str` | `None` | SQLite DB Path (required if `storage_type="sqlite"`) |
| `alchemy_url` | `str` | `None` | SQLAlchemy URL (required if `storage_type="alchemy"`) |
| `max_loaded_shards` | `int` | `0` | Simultaneous Shards in RAM (0 = all) |
| `memory_limit_mb` | `int` | `None` | Maximum RAM budget in MB |
| `binary_dir` | `str` | `"auto"` | Directory for `.lcs` binaries |

---

##Factory methods

### `from_dict(data, name, **kwargs)`

Create an instance from a `{id: texto}` dictionary. Preserve the original keys as IDs in the results.

```python
datos = {
    "art_001": "Python es un lenguaje versátil",
    "art_002": "Django simplifica el desarrollo web",
    "art_003": "FastAPI es el framework más rápido"
}

buscador = Lucis.from_dict(datos, name="articulos")
resultados = buscador.search("python web")
# resultados.results[0].doc_id → "art_001"
```

### `from_list(data, name, **kwargs)`

Create an instance from a list of texts. The IDs are sequential (0, 1, 2...).

```python
textos = [
    "Python es un lenguaje versátil",
    "Django simplifica el desarrollo web",
]

buscador = Lucis.from_list(textos, name="articulos")
resultados = buscador.search("python")
# resultados.results[0].doc_id → 0
```

### `from_sqlite_table(table_name, db_path, text_column, ...)`

Creates an instance by reading rows from an existing SQLite table.

```python
buscador = Lucis.from_sqlite_table(
    table_name="articulos",
    db_path="blog.db",
    text_column="contenido",
    id_column="articulo_id",
    name="blog_search"
)
```

**Parameters:**

| Parameter | Type | Description |
|---|---|---|
| `table_name` | `str` | Table name |
| `db_path` | `str` | Path to SQLite file |
| `text_column` | `str \| list[str]` | Text column(s) to index |
| `id_column` | `str` (optional) | Column for IDs |
| `where_clause` | `str` (optional) | SQL filter without `WHERE` |

### `from_sqlite_query(query, db_path, name, **kwargs)`

Create an instance from an arbitrary `SELECT` SQL.

```python
buscador = Lucis.from_sqlite_query(
    query="SELECT id, titulo || ' ' || cuerpo FROM posts WHERE publicado = 1",
    db_path="foro.db",
    name="posts_publicados"
)
```

- If the query returns **1 column**: it is treated as a list of texts.
- If it returns **2+ columns**: the first is the ID, the second is the text.

### `from_alchemy_table(table_name, url, text_column, ...)`

Create an instance by reading rows from a table via SQLAlchemy. Works with MySQL, PostgreSQL, MariaDB, etc.

```python
buscador = Lucis.from_alchemy_table(
    table_name="articulos",
    url="mysql+pymysql://usuario:clave@localhost/mi_bd",
    text_column="contenido",
    id_column="articulo_id",
    date_column="created_at",  # Activa sharding temporal automático
    name="articulos_idx",
    engine="lite"
)
```

**Additional parameters:**

| Parameter | Type | Default | Description |
|---|---|---|---|
| `text_column` | `str \| list[str]` | — | Column(s) of text. If it is list, they are concatenated (**cross-field search**) |
| `date_column` | `str` | `"auto"` | Column for temporary sharding. `"auto"` detects `created_at`, `updated_at`, `timestamp`. `None` disables sharding |
| `where_clause` | `str` | `None` | SQL Filter |
| `schema` | `str` | `None` | DB Schema (e.g. `"public"` for PostgreSQL) |

**Cross-field search** — indexes multiple columns as a single document:

```python
buscador = Lucis.from_alchemy_table(
    table_name="articulos",
    url="mysql+pymysql://usuario:clave@localhost/mi_bd",
    text_column=["titulo", "contenido", "tags"],  # Cross-field
    id_column="articulo_id",
    name="articulos_idx"
)
```

### `from_alchemy_query(query, url, name, **kwargs)`

Create an instance from a `SELECT` SQL via SQLAlchemy.

```python
buscador = Lucis.from_alchemy_query(
    query="SELECT id, titulo FROM posts WHERE publicado = 1",
    url="mysql+pymysql://usuario:clave@localhost/mi_bd",
    name="posts_publicados"
)
```

---

## Search

### `search(query, top_k=10, since=None, until=None)`

Search the index for relevant documents.

```python
resultados = buscador.search("python desarrollo web", top_k=5)

print(resultados.total_results)       # 5
print(resultados.search_time_ms)      # 0.31
print(resultados.results[0].doc_id)   # "art_001"
print(resultados.results[0].score)    # 0.4512
```

**Parameters:**

| Parameter | Type | Default | Description |
|---|---|---|---|
| `query` | `str \| list[str]` | — | Search as text or pre-processed tokens |
| `top_k` | `int` | `10` | Maximum results |
| `since` | `str` | `None` | Start of time range (inclusive) |
| `until` | `str` | `None` | End of time range (inclusive) |

**Search with temporal filter** (only for indexes with [sharding](sharding-temporal.md)):

```python
# Solo buscar en enero-marzo 2026
resultados = buscador.search("factura", since="2026-01", until="2026-03")
```

The accepted formats for `since`/`until` are:
- Shard key: `"2026_01"`
- ISO date: `"2026-01-15"`
- Year-month: `"2026-01"`

---

## Indexing and modification

### `index(data, persist=True)`

Ingest data and build the index.

```python
buscador = Lucis(name="nuevo", autoload=False)
buscador.index({"doc1": "texto uno", "doc2": "texto dos"})
```

### `add_documents(new_docs, dates=None, persist=True)`

Adds documents incrementally to the existing index (only `LiteEngine` in non-sharded mode, both in sharded mode).

```python
buscador.add_documents({
    "doc_nuevo": "Este es un documento nuevo"
})
```

### `remove_documents(doc_ids, persist=True)`

Delete documents by their original IDs.

```python
buscador.remove_documents(["doc_viejo", "doc_obsoleto"])
```

### `reindex(data, dates=None)`

Rebuild the entire index with fresh data. Create a new version.

```python
datos_actualizados = fetch_datos_frescos()
buscador.reindex(datos_actualizados)
```

### `reindex_streaming(row_iter, batch_size=5000)`

Rebuilds the index from a streaming iterator. Ideal for not loading everything in RAM.

```python
row_iter = storage.stream_table_with_dates(
    "emails", "body", id_column="id", date_column="sent_at"
)
buscador.reindex_streaming(row_iter)
```

---

## Persistence and versioning

### `save(name=None)`

Save the index to storage. Create a versioned version (e.g. `mi_idx__v20260210_143022`).

```python
buscador.save()
```

### `load(name=None)`

Loads a previously saved index. Automatically detects if it is sharded.

```python
buscador = Lucis(name="mi_indice")  # autoload=True por defecto
# Equivalente a:
buscador = Lucis(name="mi_indice", autoload=False)
buscador.load()
```

### `list_versions()`

Lists all physical versions of the index (oldest → newest).

```python
versiones = buscador.list_versions()
# ['articulos__v20260210_143022', 'articulos__v20260210_150545']
```

### `rollback()`

Revert the alias to the previous version.

```python
buscador.rollback()
# El alias ahora apunta a la versión anterior
```

### `purge_old_versions(keep=2)`

Removes old versions, keeping the most recent `keep` ones.

```python
eliminadas = buscador.purge_old_versions(keep=2)
print(f"Se limpiaron {eliminadas} versiones antiguas")
```

---

## Asynchronous reindexing

### `reindex_async(data, on_complete=None, on_error=None, auto_swap=True)`

Rebuilds the index in a background thread. Searches continue to work with the current index (**zero downtime**).

```python
buscador.reindex_async(datos_frescos)

while buscador.is_rebuilding():
    # Las búsquedas siguen usando el índice activo
    resultados = buscador.search("consulta")

buscador.wait_for_reindex()  # Esperar a que termine
```

### `is_rebuilding()`

Returns `True` if a rebuild is in progress.

### `wait_for_reindex(timeout=None)`

Block until the rebuild finishes. Rethrow the exception if it failed.

---

## Automatic Worker

### `create_worker(**kwargs)`

Create a `IndexWorker` linked to this instance. If the index was created from a DB table, `data_fn` and `change_detector` are **auto-generated**.

```python
worker = buscador.create_worker(interval=60)
worker.start()
# El worker monitoreará cambios y reindexará automáticamente
```

See [IndexWorker](worker.md) for complete documentation.

---

## Health monitoring

### `health_check(worker=None, benchmark_query=None)`

Generates a health report: RAM, shards, worker status, benchmark.

```python
reporte = buscador.health_check()
print(reporte)         # Tabla formateada
print(reporte.to_dict())  # JSON-ready
```

### `health_monitor(worker=None, interval=30, ...)`

Creates a continuous monitor that collects periodic snapshots.

```python
monitor = buscador.health_monitor(interval=30)
monitor.start()
# ... la app corre ...
monitor.stop()
monitor.print_summary()
```

See [Health Monitoring](salud.md) for complete documentation.

---

##Lifecycle

### `connect_source(url)`

Connect an `AlchemyReader` so that the worker can synchronize with the production DB.

```python
buscador = Lucis(name="mi_idx", engine="lite")
buscador.connect_source("mysql+pymysql://user:pass@host/db")
worker = buscador.create_worker(interval=60)
```

### `close()`

Release all mmap handles and close connections.

```python
buscador.close()
```

### `generate_lcs()`

Generates `.lcs` (binary) files for all loaded shards. Enable mmap upload in the future.

```python
n = buscador.generate_lcs()
print(f"Generados {n} archivos .lcs")
```

---

## Properties

| Property | Type | Description |
|---|---|---|
| `is_sharded` | `bool` | `True` if using temporary sharding |
| `total_docs` | `int` | Total documents indexed |
| `loaded_memory_mb` | `float` | Approximate RAM used by loaded shards |

```python
print(buscador.total_docs)        # 150000
print(buscador.is_sharded)        # True
print(buscador.loaded_memory_mb)  # 45.3
```