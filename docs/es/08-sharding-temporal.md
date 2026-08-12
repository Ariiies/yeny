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

El sharding se activa automáticamente cuando `from_table` resuelve una
columna de fecha:

```python
from lucis import Lucis
from lucis.config import TableSource

luc = Lucis.from_table(
    TableSource(
        table="noticias",
        connection_url=DB_URL,
        text_columns="contenido",
        id_column="id",
        date_column="fecha_publicacion",
    ),
    name="noticias",
    engine="lite",
)
```

Las filas se enrutan a shards mensuales; las fechas nulas o no parseables usan
el shard global `9999_99`.

### Auto-detección de columna de fecha

`from_table` detecta automáticamente una columna de fecha buscando:

1. `created_at`
2. `updated_at`
3. `timestamp`

```python
# Auto-detección: busca "created_at", "updated_at", "timestamp"
luc = Lucis.from_table(
    TableSource("articulos", DB_URL, "contenido", date_column="auto")
)
```

Si prefieres especificar la columna:

```python
luc = Lucis.from_table(
    TableSource(
        "articulos", DB_URL, "contenido", date_column="fecha_publicacion"
    )
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
from lucis import Lucis
from lucis.config import LucisOptions

luc = Lucis(
    name="logs_idx",
    engine="lite",
    options=LucisOptions(max_loaded_shards=6),
)
```

Cuando se necesita un shard nuevo y ya hay 6 cargados, el más antiguo (LRU) se desaloja automáticamente.

### Límite por RAM

```python
luc = Lucis(
    name="logs_idx",
    engine="lite",
    options=LucisOptions(memory_limit_mb=2048),
)
```

Los shards se desalojan cuando la suma de su RAM estimada supera el límite.

### Combinación

Puedes usar ambos límites — el que se alcance primero activa el desalojo:

```python
luc = Lucis(
    name="logs_idx",
    engine="lite",
    options=LucisOptions(max_loaded_shards=12, memory_limit_mb=4096),
)
```

### TTL de shards temporales

Los shards cargados por un filtro `since`/`until` reciben un TTL fijo de 30
segundos. Se desalojan automáticamente cuando vence.

---

## Indexación streaming

Para datasets de más de 100K filas, usa `reindex_streaming` para evitar cargar todo en RAM:

```python
from lucis import Lucis
from lucis.config import LucisOptions, TableConfig, TableSource

luc = Lucis.from_table(
    TableSource(
        "articulos",
        "mysql+pymysql://user:pass@host/db",
        "contenido",
        date_column="fecha",
    ),
    engine="lite",
    options=LucisOptions(max_loaded_shards=6, memory_limit_mb=2048),
)

# Streaming: consume filas en lotes, indexa shard por shard
def row_stream():
    return storage.stream_table_with_dates(
        "articulos", text_column="contenido", date_column="fecha"
    )

luc.reindex_streaming(row_stream())
```

Si la lectura inicial de la tabla está garantizada **en orden cronológico**,
habilita el streaming ordenado en la configuración del factory:

```python
luc = Lucis.from_table(
    TableSource(
        "articulos",
        "mysql+pymysql://user:pass@host/db",
        "contenido",
        date_column="fecha",
    ),
    engine="lite",
    config=TableConfig(stream_ordered=True),
    options=LucisOptions(memory_limit_mb=2048),
)
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
