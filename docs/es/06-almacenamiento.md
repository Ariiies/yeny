# Almacenamiento

Lucis soporta múltiples backends de almacenamiento. Todos implementan la misma interfaz (`BaseStorage`), así que puedes cambiar entre ellos sin modificar tu código de búsqueda.

---

## JSONStorage (default)

Almacena cada índice como un archivo `.json` legible. Ideal para aprendizaje, debug y proyectos pequeños.

```python
from lucis import Lucis

# Se usa por defecto
buscador = Lucis.from_dict(datos, name="mi_indice")
# Los archivos se guardan en lucis_data/mi_indice.json

# Personalizar directorio
buscador = Lucis.from_dict(datos, name="mi_indice", storage_dir="mis_datos")
```

**Ventajas:**
- Archivos legibles (puedes inspeccionarlos manualmente)
- Sin dependencias
- Simple

**Limitaciones:**
- No recomendado para datasets grandes (>50K documentos)
- Sin versionado ni alias
- Serialización/deserialización del índice completo cada vez

---

## SQLiteStorage

Backend de producción usando SQLite. Soporta versionado, alias y shard registry.

```python
from lucis import Lucis

buscador = Lucis.from_dict(
    datos,
    name="mi_indice",
    storage_type="sqlite",
    db_path="mi_app.db"
)
```

O directamente desde una tabla SQLite:

```python
buscador = Lucis.from_sqlite_table(
    table_name="articulos",
    db_path="blog.db",
    text_column="contenido",
    id_column="id",
    name="blog_search"
)
```

**Características:**
- Versionado automático (cada `save()` crea una nueva versión)
- Alias atómico (swap instantáneo entre versiones)
- Shard registry para índices temporales
- Tablas `lucis_*` prefijadas (nunca colisionan con tus tablas)
- `rollback()` y `purge_old_versions()` disponibles

**Tablas creadas:**
- `lucis_metadata` — Metadatos del índice
- `lucis_inverted_index` — Índice invertido serializado
- `lucis_doc_vectors` — Vectores de documentos
- `lucis_id_mapping` — Mapeo ID interno → ID original
- `lucis_aliases` — Alias lógico → nombre físico
- `lucis_shard_registry` — Registro de shards

---

## AlchemyStorage

Backend de producción para MySQL, PostgreSQL, MariaDB, Oracle, SQL Server y cualquier base de datos soportada por SQLAlchemy.

**Instalación:**

```bash
# Base
pip install lucis[alchemy]

# MySQL
pip install lucis[mysql]

# PostgreSQL
pip install lucis[postgresql]
```

**Uso:**

```python
from lucis import Lucis

buscador = Lucis.from_alchemy_table(
    table_name="articulos",
    url="mysql+pymysql://usuario:clave@localhost/mi_bd",
    text_column="contenido",
    id_column="id",
    name="articulos_idx"
)
```

O con storage explícito:

```python
buscador = Lucis(
    name="mi_indice",
    storage_type="alchemy",
    alchemy_url="mysql+pymysql://usuario:clave@localhost/mi_bd"
)
```

**Formato de URLs comunes:**

| Base de datos | URL |
|---|---|
| MySQL | `mysql+pymysql://user:pass@host/db` |
| PostgreSQL | `postgresql+psycopg2://user:pass@host/db` |
| MariaDB | `mariadb+pymysql://user:pass@host/db` |
| SQLite (vía Alchemy) | `sqlite:///path/to/db.sqlite` |

**Características:**
- Todo lo de SQLiteStorage (versionado, alias, shard registry)
- Soporte multi-BD real
- Lazy-loading: `AlchemyStorage` solo se importa si se necesita (no requiere sqlalchemy si no lo usas)

---

## MetadataStorage

Backend optimizado que almacena **solo metadatos** en SQLite (con WAL para acceso concurrente). Los datos pesados del índice viven en archivos `.lcs` binarios.

```python
from lucis import MetadataStorage

storage = MetadataStorage(db_path="lucis_data/lcs/lucis_meta.db")
```

Normalmente no necesitas crear `MetadataStorage` manualmente — se usa automáticamente cuando trabajas con `from_alchemy_table()` y archivos `.lcs`.

**Cuándo se usa:**
- Índices con `binary_dir="auto"` (archivos .lcs)
- Producción con mmap (memory-mapped I/O)
- El esquema más ligero de BD posible

**Tablas creadas:**
- `lucis_metadata` — Metadatos básicos (total_docs, engine_name, etc.)
- `lucis_aliases` — Alias lógico → nombre físico
- `lucis_shard_registry` — Registro de shards

---

## AlchemyReader

Adaptador de **solo lectura** para acceder a tablas de BD del usuario. A diferencia de `AlchemyStorage`, **nunca** crea ni escribe tablas `lucis_*`.

```python
from lucis import AlchemyReader

reader = AlchemyReader(url="mysql+pymysql://user:pass@host/db")
datos = reader.read_table("articulos", text_column="contenido", id_column="id")
```

**Cuándo usarlo:**
- Cuando el worker necesita leer datos frescos de la BD de producción
- Se usa internamente por `from_alchemy_table()` y `create_worker()`
- Lectura read-only = seguro para BD de producción

---

## Creando tu propio storage

Puedes crear backends personalizados extendiendo `BaseStorage`:

```python
from lucis.storage.base import BaseStorage

class MiStorage(BaseStorage):
    def save(self, engine_state: dict, name: str) -> None:
        """Serializar y guardar el estado del engine."""
        ...

    def load(self, name: str) -> dict:
        """Deserializar y retornar el estado del engine."""
        ...

    def exists(self, name: str) -> bool:
        """Verificar si un índice existe."""
        ...
```

Los métodos opcionales (alias, versionado, shard registry) tienen defaults seguros, así que tu backend funciona de inmediato:

```python
# Inyectar tu storage personalizado
buscador = Lucis(name="mi_indice", storage=MiStorage())
```

**Métodos opcionales que puedes override:**

| Método | Default | Descripción |
|---|---|---|
| `resolve_alias(name)` | Retorna `name` | Resolver alias → nombre físico |
| `set_alias(alias, target)` | No-op | Crear/actualizar alias |
| `get_alias(name)` | `None` | Obtener target de un alias |
| `list_versions(name)` | `[]` | Listar versiones del índice |
| `delete(name)` | No-op | Eliminar un índice |
| `save_shard_registry(name, keys)` | No-op | Guardar keys de shards |
| `load_shard_registry(name)` | `[]` | Cargar keys de shards |

---

## Siguiente paso

- [Funciones útiles](funciones-utiles.md) — Toolkit modular para búsqueda
- [Sharding temporal](sharding-temporal.md) — Partición mensual para grandes datasets
