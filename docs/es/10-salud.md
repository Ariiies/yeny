# Monitoreo de salud

Yeny incluye herramientas de diagnóstico para monitorear RAM, latencia de búsqueda y estado de shards en tiempo real, sin modificar el pipeline de indexación o búsqueda.

---

## Health check rápido

```python
from yeny import Yeny
from yeny.config import YenyOptions

yn = Yeny(
    name="mi_idx",
    engine="lite",
    options=YenyOptions(storage_type="sqlite", db_path="app.db"),
)
yn.index(datos)

report = yn.health_check()
print(report)
```

Salida:

```
==============================================================
  YENY HEALTH REPORT
==============================================================
  Timestamp     : 2024-03-15 14:30:22
  Index         : mi_idx
  Engine        : LiteEngine
  Status        : indexed
  Total Docs    : 150,000
--------------------------------------------------------------
  RAM
    Index RAM   : 128.4 MB
    Process RSS : 512.0 MB
--------------------------------------------------------------
  SHARDS
    Loaded      : 12
    Total       : 24
--------------------------------------------------------------
  WORKER
    Running     : Yes
    Cycles      : 42
    Rebuilds    : 15
    Errors      : 0
    Last rebuild: 2.34s
==============================================================
```

### Con benchmark de búsqueda

```python
report = yn.health_check(benchmark_query="prueba de velocidad")
print(f"Latencia de búsqueda: {report.search_benchmark_ms:.1f} ms")
```

---

## HealthReport — Estructura

El reporte es un dataclass con toda la información:

```python
report = yn.health_check()

# Información general
report.timestamp            # "2024-03-15 14:30:22"
report.index_name           # "mi_idx"
report.engine_name          # "LiteEngine"
report.is_indexed           # True
report.is_sharded           # True
report.total_docs           # 150000

# RAM
report.index_ram_bytes      # 134643712
report.index_ram_human      # "128.4 MB"
report.process_rss_bytes    # 536870912
report.process_rss_human    # "512.0 MB"

# Disco (archivos .yny + metadata DB)
report.disk_yny_bytes       # 67108864
report.disk_meta_bytes      # 4194304
report.disk_total_bytes     # 71303168
report.disk_total_human     # "68.0 MB"

# Shards
report.shard_count          # 12
report.shards               # List[ShardHealth]

# Worker (si hay uno activo)
report.worker_running       # True
report.worker_cycles        # 42
report.worker_rebuilds      # 15
report.worker_errors        # 0
report.worker_last_rebuild_time  # 2.34

# Benchmark
report.search_benchmark_ms  # 3.21

# Serialización
report.to_dict()            # Dict JSON-ready
```

---

## ShardHealth — Detalle por shard

Cada shard tiene su propio reporte de RAM:

```python
for shard in report.shards:
    print(f"{shard.shard_key}: {shard.total_docs} docs, {shard.total_size_human}")
```

```
2024_01: 12500 docs, 10.8 MB
2024_02: 14200 docs, 12.1 MB
2024_03: 11800 docs, 9.7 MB
9999_99: 340 docs, 0.3 MB
```

Campos de `ShardHealth`:

| Campo | Tipo | Descripción |
|---|---|---|
| `shard_key` | `str` | Clave del shard (`"YYYY_MM"` o `"9999_99"`) |
| `total_docs` | `int` | Documentos en este shard |
| `index_size_bytes` | `int` | RAM del índice invertido |
| `doc_lengths_size_bytes` | `int` | RAM del mapa de longitudes |
| `id_map_size_bytes` | `int` | RAM del mapa de IDs |
| `doc_norms_size_bytes` | `int` | RAM de normas (CoreEngine; 0 para Lite) |
| `total_size_bytes` | `int` | Suma total |
| `total_size_human` | `str` | Versión legible (ej. `"10.8 MB"`) |

---

## HealthMonitor — Monitoreo continuo

Para supervisión en producción, usa el monitor periódico:

```python
monitor = yn.health_monitor(interval=30)  # cada 30 segundos
monitor.start()

# ... tu aplicación sigue funcionando ...

# Después de un rato:
monitor.stop()
monitor.print_summary()
```

El monitor recolecta snapshots periódicos que puedes analizar para detectar tendencias de consumo de RAM, growth del índice, etc.

---

## Exportar como JSON

```python
import json

report = yn.health_check(benchmark_query="test")
data = report.to_dict()

# Enviar a tu sistema de monitoreo
print(json.dumps(data, indent=2))
```

Estructura del dict:

```json
{
    "timestamp": "2024-03-15 14:30:22",
    "index_name": "mi_idx",
    "engine": "LiteEngine",
    "is_indexed": true,
    "is_sharded": true,
    "total_docs": 150000,
    "ram": {
        "index_ram": "128.4 MB",
        "index_ram_bytes": 134643712,
        "process_rss": "512.0 MB",
        "process_rss_bytes": 536870912
    },
    "disk": {
        "yny_files": "64.0 MB",
        "metadata_db": "4.0 MB",
        "total": "68.0 MB"
    },
    "shards": {
        "count": 12,
        "detail": [...]
    },
    "worker": {
        "running": true,
        "cycles": 42,
        "rebuilds": 15,
        "errors": 0,
        "last_rebuild_time_s": 2.34
    },
    "search_benchmark_ms": 3.21
}
```

---

## Siguiente paso

- [Cómo funciona Yeny](11-como-funciona.md) — Internos del índice invertido
- [Recetas prácticas](14-recetas.md) — Monitoreo en producción
