# Sharding temporal

Cuando tu dataset contiene millones de documentos con fechas, cargar todo en RAM no es viable. El **sharding temporal** de Lucis particiona automáticamente los documentos en shards mensuales (`YYYY_MM`), de modo que solo los shards relevantes para una consulta se cargan en memoria.

---

## Arquitectura

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

Cada shard es una instancia independiente del motor (CoreEngine o LiteEngine) con su propio índice invertido. El shard `9999_99` es el **shard global**: contiene documentos sin fecha o cuya fecha no se pudo parsear.

---

## Activar sharding

El sharding se activa automáticamente cuando proporcionas fechas en tus datos:

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

Esto creará tres shards: `2024_01`, `2024_03`, y `9999_99` (vacío en este caso).

### Auto-detección de columna de fecha

Cuando usas `from_sqlite_table`, `from_alchemy_table`, o los métodos `from_*_query`, Lucis intenta detectar la columna de fecha automáticamente buscando columnas llamadas:

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

Si prefieres especificar la columna:

```python
luc = Lucis.from_sqlite_table(
    db_path="app.db",
    table_name="articulos",
    text_column="contenido",
    date_column="fecha_publicacion",    # ← columna explícita
)
```

---

## Búsqueda con filtros temporales

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

Los filtros `since` y `until` aceptan:
- Claves de shard directas: `"2024_01"`
- Año-mes ISO: `"2024-01"`
- Fechas completas: `"2024-01-15"` (se trunca al mes: `2024_01`)
- Objetos `datetime` y `date`

> El shard global (`9999_99`) **siempre** se incluye en la búsqueda, sin importar los filtros, porque contiene documentos sin fecha que podrían ser relevantes.

---

## Gestión de memoria

Para datasets muy grandes, puedes limitar cuántos shards se mantienen cargados simultáneamente:

### Límite por cantidad

```python
luc = Lucis(
    name="logs_idx",
    engine="lite",
    max_loaded_shards=6,    # ← máximo 6 shards en RAM
)
```

Cuando se necesita un shard nuevo y ya hay 6 cargados, el más antiguo (LRU) se desaloja automáticamente.

### Límite por RAM

```python
luc = Lucis(
    name="logs_idx",
    engine="lite",
    memory_limit_mb=2048,   # ← máximo 2 GB para shards
)
```

Los shards se desalojan cuando la suma de su RAM estimada supera el límite.

### Combinación

Puedes usar ambos límites — el que se alcance primero activa el desalojo:

```python
luc = Lucis(
    name="logs_idx",
    engine="lite",
    max_loaded_shards=12,
    memory_limit_mb=4096,
)
```

### TTL de shards temporales

Los shards cargados por un filtro `since`/`until` reciben un TTL (por defecto 30 segundos). Pasado ese tiempo, se desalojan automáticamente:

```python
luc = Lucis(
    name="logs_idx",
    engine="lite",
    max_loaded_shards=6,
    temp_ttl_seconds=60,    # ← mantener shards filtrados 60s
)
```

---

## Indexación streaming

Para datasets de más de 100K filas, usa `reindex_streaming` para evitar cargar todo en RAM:

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

Si tus datos llegan **ordenados cronológicamente**, habilita `stream_ordered=True` para desalojar shards completados durante la ingesta:

```python
luc.reindex_streaming(row_stream(), stream_ordered=True)
```

> **⚠️ Precaución**: Solo usa `stream_ordered=True` si estás seguro de que los datos llegan ordenados por fecha. Con datos desordenados, los shards se cerrarán prematuramente y perderán documentos.

---

## Funciones utilitarias

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

## Persistencia de shards

Al guardar un índice sharded, cada shard se persiste independientemente:

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

Con almacenamiento binario `.lcs`, cada shard genera su propio archivo:

```
lucis_data/lcs/
  mi_idx__v20240315_120000__shard__2024_01.lcs
  mi_idx__v20240315_120000__shard__2024_02.lcs
  ...
```

Los archivos `.lcs` se cargan por **memory-mapped I/O** (mmap): el sistema operativo los carga bajo demanda, sin consumir RAM adicional del heap Python.

---

## Siguiente paso

- [IndexWorker](09-worker.md) — Reindexación automática en segundo plano
- [Monitoreo de salud](10-salud.md) — RAM y diagnósticos por shard
