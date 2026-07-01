# Health monitoring

Lucis includes diagnostic tools to monitor RAM, seek latency and shard status in real time, without modifying the indexing or search pipeline.

---

## Quick health check

```python
from lucis import Lucis

luc = Lucis(name="mi_idx", engine="lite", storage_type="sqlite", db_path="app.db")
luc.index(datos)

report = luc.health_check()
print(report)
```

Output:

```
==============================================================
  LUCIS HEALTH REPORT
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

### With search benchmark

```python
report = luc.health_check(benchmark_query="prueba de velocidad")
print(f"Latencia de búsqueda: {report.search_benchmark_ms:.1f} ms")
```

---

## HealthReport — Structure

The report is a dataclass with all the information:

```python
report = luc.health_check()

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

# Disco (archivos .lcs + metadata DB)
report.disk_lcs_bytes       # 67108864
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

## ShardHealth — Detail by shard

Each shard has its own RAM report:

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

`ShardHealth` fields:

| Field | Type | Description |
|---|---|---|
| `shard_key` | `str` | Shard key (`"YYYY_MM"` or `"9999_99"`) |
| `total_docs` | `int` | Documents in this shard |
| `index_size_bytes` | `int` | Inverted Index RAM |
| `doc_lengths_size_bytes` | `int` | Length Map RAM |
| `id_map_size_bytes` | `int` | ID Map RAM |
| `doc_norms_size_bytes` | `int` | Standards RAM (CoreEngine; 0 for Lite) |
| `total_size_bytes` | `int` | Total sum |
| `total_size_human` | `str` | Readable version (e.g. `"10.8 MB"`) |

---

## HealthMonitor — Continuous monitoring

For production monitoring, use the periodic monitor:

```python
monitor = luc.health_monitor(interval=30)  # cada 30 segundos
monitor.start()

# ... tu aplicación sigue funcionando ...

# Después de un rato:
monitor.stop()
monitor.print_summary()
```

The monitor collects periodic snapshots that you can analyze to detect RAM consumption trends, index growth, etc.

---

## Export as JSON

```python
import json

report = luc.health_check(benchmark_query="test")
data = report.to_dict()

# Enviar a tu sistema de monitoreo
print(json.dumps(data, indent=2))
```

Dict structure:

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
        "lcs_files": "64.0 MB",
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

## Next step

- [How Lucis works](como-funciona.md) — Inverted index internals
- [Practical recipes](recetas.md) — Production monitoring