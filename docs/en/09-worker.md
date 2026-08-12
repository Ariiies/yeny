# IndexWorker — Automatic reindexing

The `IndexWorker` is a daemon thread that monitors your data source and rebuilds the index automatically when it detects changes, without interrupting ongoing searches (**zero-downtime**).

---

## Quick start

```python
import sqlite3
from lucis import Lucis, IndexWorker

luc = Lucis.from_sqlite_table(
    db_path="app.db",
    table_name="articulos",
    text_column="contenido",
    id_column="id",
    name="mi_idx",
)

def obtener_datos():
    """Función que retorna los datos frescos."""
    with sqlite3.connect("app.db") as conn:
        return {str(row[0]): row[1] for row in conn.execute(
            "SELECT id, contenido FROM articulos"
        )}

worker = IndexWorker(
    lucis=luc,
    data_fn=obtener_datos,
    interval=60,          # cada 60 segundos
    auto_purge=True,      # limpieza de versiones antiguas
    keep_versions=3,      # mantener últimas 3 versiones
)
worker.start()

# ... tu aplicación sigue funcionando, las búsquedas no se interrumpen ...

worker.stop()  # apagado limpio
```

---

## Modes of operation

### Full rebuild (default)

Call `data_fn()` to get the entire corpus and do `lucis.reindex(data)`:

```python
worker = IndexWorker(
    lucis=luc,
    data_fn=obtener_datos,
    interval=120,
)
```

Ideal for `CoreEngine` or when the entire dataset fits in memory.

### Incremental update

It just gets new documents and adds them with `add_documents()`:

```python
def obtener_nuevos():
    """Retorna solo documentos agregados desde el último ciclo."""
    # Tu lógica aquí
    return {"doc_nuevo_1": "texto...", "doc_nuevo_2": "texto..."}

worker = IndexWorker(
    lucis=luc,
    data_fn=obtener_datos,        # fallback para rebuild completo
    delta_fn=obtener_nuevos,      # documentos incrementales
    incremental=True,
    interval=30,
)
```

> **Note**: If the worker detects that the source has *fewer* documents than before (possible deletions), it automatically falls into a full rebuild.

### Streaming rebuild

For large datasets with temporal sharding:

```python
def stream_filas():
    return storage.stream_table_with_dates(
        "articulos", text_column="contenido", date_column="fecha"
    )

worker = IndexWorker(
    lucis=luc,
    data_fn=obtener_datos,
    streaming_fn=stream_filas,    # ← preferido sobre data_fn cuando existe
    interval=300,
)
```

When `streaming_fn` is set, the worker uses `reindex_streaming()` instead of loading everything into memory.

---

## Change detection

By default, the worker rebuilds every cycle. You can optimize with a change detector:

```python
ultimo_check = None

def hay_cambios():
    global ultimo_check
    resultado = db.execute("SELECT MAX(updated_at) FROM articulos").fetchone()[0]
    cambio = resultado != ultimo_check
    ultimo_check = resultado
    return cambio

worker = IndexWorker(
    lucis=luc,
    data_fn=obtener_datos,
    change_detector=hay_cambios,    # ← solo rebuild cuando retorna True
    interval=30,
)
```

If `change_detector` returns `False`, the loop is skipped without rebuilding.

---

## Callbacks

```python
worker = IndexWorker(
    lucis=luc,
    data_fn=obtener_datos,
    interval=60,
    on_rebuild=lambda name: print(f"Rebuild exitoso: {name}"),
    on_error=lambda exc: alertar_equipo(str(exc)),
    on_cycle=lambda n, saltado: log.info(f"Ciclo {n}, saltado={saltado}"),
)
```

| Callback | Signature | When is it executed |
|---|---|---|
| `on_rebuild` | `fn(physical_name)` | After a successful rebuild |
| `on_error` | `fn(exception)` | When a rebuild fails |
| `on_cycle` | `fn(cycle_number, skipped)` | At the end of each cycle |

> Errors in callbacks never stop the worker — they are logged and continued.

---

## Auto-purge

Old versions are removed automatically:

```python
worker = IndexWorker(
    lucis=luc,
    data_fn=obtener_datos,
    auto_purge=True,      # activado por defecto
    keep_versions=3,      # mantener las 3 más recientes
)
```

After each successful rebuild, versions older than `keep_versions` are removed from storage.

---

## Statistics

```python
print(worker.stats)
# {
#     "running": True,
#     "interval": 60,
#     "cycles": 42,
#     "rebuilds": 15,
#     "errors": 0,
#     "last_rebuild_time": 2.34,
#     "index_name": "mi_idx",
#     "auto_purge": True,
#     "keep_versions": 3,
# }

# También accesibles individualmente:
print(worker.cycles)              # 42
print(worker.rebuilds)            # 15
print(worker.errors)              # 0
print(worker.last_rebuild_time)   # 2.34 (segundos)
```

---

## Methods

| Method | Description |
|---|---|
| `start()` | Start the daemon thread. No-op if it is already running. |
| `stop(timeout=None)` | Signal the worker to stop and wait for him to finish. |
| `is_running()` | `True` if the thread is active. |
| `trigger_now()` | Force an immediate rebuild (synchronous, in the current thread). |

---

## Quick access from Lucis

```python
# Crear worker directamente desde la instancia Lucis
worker = luc.create_worker(
    data_fn=obtener_datos,
    interval=60,
    auto_purge=True,
)
worker.start()
```

---

## Next step

- [Health Monitoring](10-health.md) — RAM, timing and diagnostics
- [Practical Recipes](14-recipes.md) — Worker with MySQL, continuous monitoring
