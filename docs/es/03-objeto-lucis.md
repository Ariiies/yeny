# La clase Lucis

`Lucis` es el orquestador principal de la librería. Implementa el **patrón Facade**: conecta motores de búsqueda, almacenamiento y tokenizadores detrás de una API limpia y mínima.

Hay tres formas de crear una instancia:

1. **Desde datos** — `Lucis.from_dict()` o `Lucis.from_list()`
2. **Cargar existente** — `Lucis(name="mi_indice")` (auto-carga si existe)
3. **Vacía** — `Lucis(name="nuevo", autoload=False)` y luego `.index(data)`

---

## Constructor

```python
from lucis import Lucis

buscador = Lucis(
    name="mi_indice",
    engine="core",
    preprocessor=None,
    autoload=True,
)
```

### Parámetros principales

| Parámetro | Tipo | Default | Descripción |
|---|---|---|---|
| `name` | `str` | `"default"` | Nombre del índice, usado para persistencia |
| `engine` | `str` | `"core"` | Motor: `"core"` (TF-IDF) o `"lite"` (TF) |
| `preprocessor` | `Callable` | `None` | Preprocesador de texto personalizado |
| `autoload` | `bool` | `True` | Auto-cargar índice existente al instanciar |
| `storage` | `BaseStorage` | `None` | Storage inyectado; prevalece sobre las opciones declarativas |
| `options` | `LucisOptions` | `None` | Configuración avanzada de storage, binarios y memoria |

El camino simple no necesita objetos de configuración. Para infraestructura
avanzada puedes reutilizar una instancia inmutable:

```python
from lucis import Lucis
from lucis.config import LucisOptions

options = LucisOptions(
    storage_dir="datos_personalizados",
    memory_limit_mb=512,
    max_loaded_shards=6,
)
buscador = Lucis(name="mi_indice", engine="lite", options=options)
```

`binary_dir` tiene tres estados: `"auto"` deriva
`<storage_dir>/lcs`, `None` desactiva la persistencia `.lcs` y cualquier otro
string selecciona un directorio explícito.

Las propiedades de estado de solo lectura incluyen `is_indexed`, `is_sharded`,
`total_docs` y `loaded_memory_mb`.

---

## Factory methods

### `from_dict(data, name, *, engine, preprocessor, options)`

Crea una instancia desde un diccionario `{id: texto}`. Preserva las keys originales como IDs en los resultados.

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

### `from_list(data, name, *, engine, preprocessor, options)`

Crea una instancia desde una lista de textos. Los IDs son secuenciales (0, 1, 2...).

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

Crea una instancia leyendo filas de una tabla SQLite existente.

```python
buscador = Lucis.from_sqlite_table(
    table_name="articulos",
    db_path="blog.db",
    text_column="contenido",
    id_column="articulo_id",
    name="blog_search"
)
```

**Parámetros:**

| Parámetro | Tipo | Descripción |
|---|---|---|
| `table_name` | `str` | Nombre de la tabla |
| `db_path` | `str` | Ruta al archivo SQLite |
| `text_column` | `str \| list[str]` | Columna(s) de texto a indexar |
| `id_column` | `str` (opcional) | Columna para IDs |
| `where_clause` | `str` (opcional) | Filtro SQL sin `WHERE` |

### `from_sqlite_query(query, db_path, name, *, engine, preprocessor, options)`

Crea una instancia desde un `SELECT` SQL arbitrario.

```python
buscador = Lucis.from_sqlite_query(
    query="SELECT id, titulo || ' ' || cuerpo FROM posts WHERE publicado = 1",
    db_path="foro.db",
    name="posts_publicados"
)
```

- Si el query retorna **1 columna**: se trata como lista de textos.
- Si retorna **2+ columnas**: la primera es el ID, la segunda es el texto.

### `from_table(source, name, *, engine, preprocessor, config, options)`

Crea una instancia leyendo filas de una tabla via SQLAlchemy. Funciona con MySQL, PostgreSQL, MariaDB, etc.

```python
from lucis.config import TableSource

buscador = Lucis.from_table(
    TableSource(
        table="articulos",
        connection_url="mysql+pymysql://usuario:clave@localhost/mi_bd",
        text_columns="contenido",
        id_column="articulo_id",
        date_column="created_at",
    ),
    name="articulos_idx",
    engine="lite"
)
```

**Parámetros adicionales:**

| Parámetro | Tipo | Default | Descripción |
|---|---|---|---|
| `source` | `TableSource` | — | Tabla, URL de conexión, columnas de texto, ID y columna temporal |
| `config` | `TableConfig` | `None` | Filtros, schema y streaming avanzados |
| `options` | `LucisOptions` | `None` | Configuración avanzada de storage, binarios y memoria |

Los controles de filtrado y streaming viven en `TableConfig`:

```python
from lucis.config import TableConfig

config = TableConfig(
    where_clause="publicado = 1",
    schema="public",
    shard_batch_size=10_000,
    stream_ordered=False,
)
```

**Búsqueda cross-field** — indexa múltiples columnas como un solo documento:

```python
buscador = Lucis.from_table(
    TableSource(
        table="articulos",
        connection_url="mysql+pymysql://usuario:clave@localhost/mi_bd",
        text_columns=["titulo", "contenido", "tags"],
        id_column="articulo_id",
    ),
    name="articulos_idx"
)
```

### `from_query(query, connection_url, name, *, engine, preprocessor, options)`

Crea una instancia desde un `SELECT` SQL via SQLAlchemy.

```python
buscador = Lucis.from_query(
    query="SELECT id, titulo FROM posts WHERE publicado = 1",
    connection_url="mysql+pymysql://usuario:clave@localhost/mi_bd",
    name="posts_publicados"
)
```

---

## Búsqueda

### `search(query, top_k=10, since=None, until=None)`

Busca documentos relevantes en el índice.

```python
resultados = buscador.search("python desarrollo web", top_k=5)

print(resultados.total_results)       # 5
print(resultados.search_time_ms)      # 0.31
print(resultados.results[0].doc_id)   # "art_001"
print(resultados.results[0].score)    # 0.4512
```

**Parámetros:**

| Parámetro | Tipo | Default | Descripción |
|---|---|---|---|
| `query` | `str \| list[str]` | — | Búsqueda como texto o tokens pre-procesados |
| `top_k` | `int` | `10` | Máximo de resultados |
| `since` | `str` | `None` | Inicio del rango temporal (inclusive) |
| `until` | `str` | `None` | Fin del rango temporal (inclusive) |

**Búsqueda con filtro temporal** (solo para índices con [sharding](sharding-temporal.md)):

```python
# Solo buscar en enero-marzo 2026
resultados = buscador.search("factura", since="2026-01", until="2026-03")
```

Los formatos aceptados para `since`/`until` son:
- Shard key: `"2026_01"`
- ISO date: `"2026-01-15"`
- Year-month: `"2026-01"`

---

## Indexación y modificación

### `index(data, persist=True)`

Ingesta datos y construye el índice.

```python
buscador = Lucis(name="nuevo", autoload=False)
buscador.index({"doc1": "texto uno", "doc2": "texto dos"})
```

### `add_documents(new_docs, dates=None, persist=True)`

Añade documentos incrementalmente al índice existente (solo `LiteEngine` en modo no-sharded, ambos en modo sharded).

```python
buscador.add_documents({
    "doc_nuevo": "Este es un documento nuevo"
})
```

### `remove_documents(doc_ids, persist=True)`

Elimina documentos por sus IDs originales.

```python
buscador.remove_documents(["doc_viejo", "doc_obsoleto"])
```

### `reindex(data, dates=None)`

Reconstruye el índice completo con datos frescos. Crea una nueva versión.

```python
datos_actualizados = fetch_datos_frescos()
buscador.reindex(datos_actualizados)
```

### `reindex_streaming(row_iter, batch_size=5000)`

Reconstruye el índice desde un iterador streaming. Ideal para no cargar todo en RAM.

```python
row_iter = storage.stream_table_with_dates(
    "emails", "body", id_column="id", date_column="sent_at"
)
buscador.reindex_streaming(row_iter)
```

---

## Persistencia y versionado

### `save(name=None)`

Guarda el índice a storage. Crea una versión versionada (ej. `mi_idx__v20260210_143022`).

```python
buscador.save()
```

### `load(name=None)`

Carga un índice previamente guardado. Detecta automáticamente si es sharded.

```python
buscador = Lucis(name="mi_indice")  # autoload=True por defecto
# Equivalente a:
buscador = Lucis(name="mi_indice", autoload=False)
buscador.load()
```

### `list_versions()`

Lista todas las versiones físicas del índice (más antigua → más nueva).

```python
versiones = buscador.list_versions()
# ['articulos__v20260210_143022', 'articulos__v20260210_150545']
```

### `rollback()`

Revierte el alias a la versión anterior.

```python
buscador.rollback()
# El alias ahora apunta a la versión anterior
```

### `purge_old_versions(keep=2)`

Elimina versiones antiguas, conservando las `keep` más recientes.

```python
eliminadas = buscador.purge_old_versions(keep=2)
print(f"Se limpiaron {eliminadas} versiones antiguas")
```

---

## Reindexación asíncrona

### `reindex_async(data, on_complete=None, on_error=None, auto_swap=True)`

Reconstruye el índice en un hilo de background. Las búsquedas siguen funcionando con el índice actual (**zero downtime**).

```python
buscador.reindex_async(datos_frescos)

while buscador.is_rebuilding():
    # Las búsquedas siguen usando el índice activo
    resultados = buscador.search("consulta")

buscador.wait_for_reindex()  # Esperar a que termine
```

### `is_rebuilding()`

Devuelve `True` si hay una reconstrucción en progreso.

### `wait_for_reindex(timeout=None)`

Bloquea hasta que la reconstrucción termine. Re-lanza la excepción si falló.

---

## Worker automático

### `create_worker(**kwargs)`

Crea un `IndexWorker` vinculado a esta instancia. Si el índice fue creado desde una tabla de BD, `data_fn` y `change_detector` se **auto-generan**.

```python
worker = buscador.create_worker(interval=60)
worker.start()
# El worker monitoreará cambios y reindexará automáticamente
```

Consulta [IndexWorker](09-worker.md) para documentación completa.

---

## Health monitoring

### `health_check(worker=None, benchmark_query=None)`

Genera un reporte de salud: RAM, shards, worker status, benchmark.

```python
reporte = buscador.health_check()
print(reporte)         # Tabla formateada
print(reporte.to_dict())  # JSON-ready
```

### `health_monitor(worker=None, interval=30, ...)`

Crea un monitor continuo que recolecta snapshots periódicos.

```python
monitor = buscador.health_monitor(interval=30)
monitor.start()
# ... la app corre ...
monitor.stop()
monitor.print_summary()
```

Consulta [Health Monitoring](10-salud.md) para documentación completa.

---

## Lifecycle

### `connect_source(connection_url)`

Conecta un `DatabaseReader` para que el worker pueda sincronizar con la BD de producción.

```python
buscador = Lucis(name="mi_idx", engine="lite")
buscador.connect_source("mysql+pymysql://user:pass@host/db")
worker = buscador.create_worker(interval=60)
```

### `close()`

Libera todos los handles de mmap y cierra conexiones.

```python
buscador.close()
```

### `generate_lcs()`

Genera archivos `.lcs` (binarios) para todos los shards cargados. Habilita carga por mmap en el futuro.

```python
n = buscador.generate_lcs()
print(f"Generados {n} archivos .lcs")
```

---

## Propiedades

| Propiedad | Tipo | Descripción |
|---|---|---|
| `is_sharded` | `bool` | `True` si usa sharding temporal |
| `total_docs` | `int` | Total de documentos indexados |
| `loaded_memory_mb` | `float` | RAM aproximada usada por shards cargados |

```python
print(buscador.total_docs)        # 150000
print(buscador.is_sharded)        # True
print(buscador.loaded_memory_mb)  # 45.3
```
