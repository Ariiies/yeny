# Modelos de datos

Lucis usa dataclasses inmutables (`frozen=True`) para representar los resultados de búsqueda. Esto garantiza integridad después de la creación, autocompletado en el IDE, y serialización JSON directa.

---

## SearchResult

Representa un único documento encontrado en una búsqueda.

```python
from lucis.models.search import SearchResult
```

| Campo | Tipo | Descripción |
|---|---|---|
| `doc_id` | `DocId` | Identificador original del documento (preserva el tipo de input: `str`, `int`, etc.) |
| `score` | `float` | Puntuación de similitud entre query y documento (0.0 a 1.0 para CoreEngine) |
| `rank` | `int` | Posición en la lista de resultados (1-based, más relevante primero) |
| `shard_key` | `Optional[str]` | Clave del shard temporal (ej. `"2024_02"`). `None` para índices sin sharding. |

### Ejemplo

```python
resultado = response.results[0]

print(resultado.doc_id)      # "articulo_42"
print(resultado.score)       # 0.8734
print(resultado.rank)        # 1
print(resultado.shard_key)   # "2024_03" o None
```

> `SearchResult` es inmutable (frozen). No puedes modificar sus campos después de la creación.

---

## SearchResponse

Respuesta completa de una búsqueda, con contexto sobre la query, el motor, tiempos y resultados.

```python
from lucis.models.search import SearchResponse
```

| Campo | Tipo | Descripción |
|---|---|---|
| `query` | `Union[str, List[str]]` | La query tal como fue recibida |
| `tokens` | `List[str]` | Tokens efectivamente usados para la búsqueda (después del preprocesamiento) |
| `engine` | `str` | Nombre del motor (`"CoreEngine"` o `"LiteEngine"`) |
| `total_results` | `int` | Cantidad de documentos encontrados |
| `search_time_ms` | `float` | Tiempo de búsqueda en milisegundos |
| `results` | `List[SearchResult]` | Lista ordenada de resultados |
| `shards_searched` | `int` | Cantidad de shards consultados (0 = sin sharding) |
| `total_shards` | `int` | Total de shards en el índice (0 = sin sharding) |

### Ejemplo

```python
from lucis import Lucis

luc = Lucis(name="demo", engine="core")
luc.index({"a": "python web framework", "b": "java enterprise"})

response = luc.search("python")

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

Snapshot de salud de una instancia Lucis. Documentado en detalle en [Monitoreo de salud](10-salud.md).

```python
from lucis.core.health import HealthReport
```

| Campo | Tipo | Descripción |
|---|---|---|
| `timestamp` | `str` | Fecha/hora del reporte |
| `index_name` | `str` | Nombre lógico del índice |
| `engine_name` | `str` | Motor en uso |
| `is_indexed` | `bool` | Si el índice está construido |
| `is_sharded` | `bool` | Si usa sharding temporal |
| `total_docs` | `int` | Total de documentos |
| `index_ram_bytes` | `int` | RAM del índice en bytes |
| `process_rss_bytes` | `Optional[int]` | RSS del proceso |
| `disk_lcs_bytes` | `int` | Tamaño de archivos .lcs |
| `disk_meta_bytes` | `int` | Tamaño de metadata DB |
| `shard_count` | `int` | Shards cargados |
| `shards` | `List[ShardHealth]` | Detalle por shard |
| `worker_running` | `bool` | Si el worker está activo |
| `worker_cycles` | `int` | Ciclos completados |
| `worker_rebuilds` | `int` | Rebuilds exitosos |
| `worker_errors` | `int` | Rebuilds fallidos |
| `worker_last_rebuild_time` | `Optional[float]` | Duración del último rebuild (s) |
| `search_benchmark_ms` | `Optional[float]` | Latencia del benchmark |

Propiedades derivadas: `index_ram_human`, `process_rss_human`, `disk_total_bytes`, `disk_total_human`.

---

## ShardHealth

Estadísticas de RAM para un shard individual. Documentado en [Monitoreo de salud](10-salud.md#shardhealth--detalle-por-shard).

```python
from lucis.core.health import ShardHealth
```

| Campo | Tipo | Descripción |
|---|---|---|
| `shard_key` | `str` | Clave temporal del shard |
| `total_docs` | `int` | Documentos en el shard |
| `index_size_bytes` | `int` | RAM del índice invertido |
| `doc_lengths_size_bytes` | `int` | RAM de longitudes de documento |
| `id_map_size_bytes` | `int` | RAM del mapa de IDs |
| `doc_norms_size_bytes` | `int` | RAM de normas (CoreEngine; 0 para Lite) |
| `total_size_bytes` | `int` | Suma total |

---

## Siguiente paso

- [Excepciones](13-excepciones.md) — Jerarquía de errores
- [Referencia API](15-api-referencia.md) — Firmas completas
