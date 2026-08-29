# IndexWorker — Reindexación automática

El `IndexWorker` es un daemon thread que monitorea tu fuente de datos y reconstruye el índice automáticamente cuando detecta cambios, sin interrumpir las búsquedas en curso (**zero-downtime**).

---

## Inicio rápido

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

## Modos de operación

### Reconstrucción completa (default)

Llama a `data_fn()` para obtener todo el corpus y hace `lucis.reindex(data)`:

```python
worker = IndexWorker(
    lucis=luc,
    data_fn=obtener_datos,
    interval=120,
)
```

Ideal para `CoreEngine` o cuando el dataset completo cabe en memoria.

### Actualización incremental

Solo obtiene documentos nuevos y los agrega con `add_documents()`:

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

> **Nota**: Si el worker detecta que la fuente tiene *menos* documentos que antes (posibles eliminaciones), automáticamente cae en rebuild completo.

### Streaming rebuild

Para datasets grandes con sharding temporal:

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

Cuando `streaming_fn` está configurado, el worker usa `reindex_streaming()` en lugar de cargar todo en memoria.

---

## Detección de cambios

Por defecto, el worker reconstruye en cada ciclo. Puedes optimizar con un detector de cambios:

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

Si `change_detector` retorna `False`, el ciclo se salta sin reconstruir.

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

| Callback | Firma | Cuándo se ejecuta |
|---|---|---|
| `on_rebuild` | `fn(physical_name)` | Después de un rebuild exitoso |
| `on_error` | `fn(exception)` | Cuando un rebuild falla |
| `on_cycle` | `fn(cycle_number, skipped)` | Al final de cada ciclo |

> Los errores en callbacks nunca detienen el worker — se registran y se continúa.

---

## Auto-purge

Las versiones antiguas se eliminan automáticamente:

```python
worker = IndexWorker(
    lucis=luc,
    data_fn=obtener_datos,
    auto_purge=True,      # activado por defecto
    keep_versions=3,      # mantener las 3 más recientes
)
```

Después de cada rebuild exitoso, las versiones más antiguas que `keep_versions` se eliminan del storage.

---

## Estadísticas

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

## Métodos

| Método | Descripción |
|---|---|
| `start()` | Inicia el daemon thread. No-op si ya está corriendo. |
| `stop(timeout=None)` | Señala al worker que se detenga y espera a que termine. |
| `is_running()` | `True` si el thread está activo. |
| `trigger_now()` | Fuerza un rebuild inmediato (síncrono, en el thread actual). |

---

## Acceso rápido desde Lucis

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

## Siguiente paso

- [Monitoreo de salud](10-salud.md) — RAM, timing y diagnósticos
- [Recetas prácticas](14-recetas.md) — Worker con MySQL, monitoreo continuo
