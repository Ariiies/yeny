# Almacenamiento

Lucis soporta múltiples backends de almacenamiento, todos implementando la misma interfaz (`BaseStorage`). La configuración recomendada para producción usa **archivos binarios `.lcs`** para los datos del índice más **SQLite WAL** para metadatos ligeros — ofreciendo carga con RAM casi nula mediante memory-mapped I/O y acceso concurrente de lectura/escritura.

---

## Backends de un vistazo

| Backend | Datos del índice | Metadatos | Caso de uso |
|---|---|---|---|
| **MetadataStorage** | Binarios `.lcs` (mmap) | SQLite (WAL) | **Por defecto en producción.** Usado automáticamente por `from_alchemy_table` y al recargar un índice existente. |
| **JSONStorage** | Archivos `.json` | `.json` | Simple / debugging / datasets pequeños. |
| **SQLiteStorage** | Tablas `lucis_*` en tu BD | Tablas `lucis_*` | Persistencia completa en SQLite, con versionado y rollback. |
| **AlchemyStorage** | Tablas `lucis_*` vía SQLAlchemy | Tablas `lucis_*` | Persistencia completa en BD remota (MySQL, PostgreSQL, etc.). |
| **AlchemyReader** | *Solo lectura* (sin escritura) | *Ninguno* | Ingesta datos desde tu BD sin crear tablas `lucis_*`. |

---

## MetadataStorage + `.lcs` (recomendado)

Esta es la arquitectura de almacenamiento usada al ingerir desde una base de datos vía `from_alchemy_table()` o `from_alchemy_query()`. También se auto-descubre al recargar un índice creado previamente de esta forma.

> **Importante:** La persistencia es **automática** con `from_alchemy_table()` y `from_alchemy_query()`. El directorio `lucis_data/lcs/`, `lucis_meta.db` y los binarios `.lcs` se crean inmediatamente durante la ingesta — **no** necesitas llamar a `.save()` manualmente ni pasar `binary_dir` explícitamente (por defecto es `"auto"`). Lo mismo aplica para `from_dict()`, `from_list()` y `.index()` — todos persisten por defecto.

### Cómo funciona

```
┌──────────────────────────────────────────────────┐
│                 lucis_data/lcs/                   │
│                                                   │
│  lucis_meta.db  ←── SQLite WAL                    │
│  ├─ lucis_metadata     (doc counts, engine name)  │
│  ├─ lucis_aliases      (alias → nombre físico)    │
│  ├─ lucis_shard_registry (keys de shards)         │
│  └─ lucis_metadata.source_* (info de tabla/col)   │
│                                                   │
│  *.lcs files     ←── binarios mmap                │
│  ├─ índice invertido (CompactPostings)            │
│  ├─ longitudes de docs (CompactDocLengths)        │
│  └─ mapeo de IDs (interno → original)             │
└──────────────────────────────────────────────────┘
```

**Puntos clave:**

- Los archivos `.lcs` contienen los **datos reales del índice** (índice invertido, longitudes de documentos, mapeo de IDs). Se cargan vía memory-mapped I/O: el SO mapea el archivo sin copiarlo al heap de Python, dando un overhead de RAM casi nulo.
- `lucis_meta.db` almacena **solo metadatos ligeros**: conteo de documentos, aliases, registro de shards e información de la tabla fuente (para que el worker sepa qué monitorear). Usa modo WAL para lecturas/escrituras concurrentes.
- **Tu base de datos de producción nunca se toca** más allá de la ingesta inicial. `AlchemyReader` es de solo lectura — se conecta, lee filas y se desconecta. Cero tablas `lucis_*` creadas en tu BD.

### Cuándo se usa automáticamente

```python
# Caso 1: Ingesta desde una tabla de base de datos
# (auto-persiste — no necesita .save())
luc = Lucis.from_alchemy_table(
    table_name="articulos",
    url="mysql+pymysql://usuario:pass@host/bd",
    text_column="contenido",
    id_column="id",
    name="articulos_idx",
    # binary_dir="auto" es el default — lucis_data/lcs/ se crea automáticamente
)
# → MetadataStorage se crea automáticamente
# → Los datos del índice van a archivos .lcs inmediatamente
# → Los metadatos van a lucis_data/lcs/lucis_meta.db
# → Tu BD MySQL no se toca

# Caso 2: Recargar un índice existente (sin storage explícito)
luc = Lucis(name="articulos_idx", engine="lite", binary_dir="auto")
# → Lucis auto-descubre lucis_data/lcs/lucis_meta.db
# → MetadataStorage se usa transparentemente
# → Los archivos .lcs se cargan vía mmap
```

### Creación manual

```python
from lucis.storage.metadata_storage import MetadataStorage

storage = MetadataStorage(db_path="lucis_data/lcs/lucis_meta.db")
luc = Lucis(name="mi_idx", storage=storage, binary_dir="lucis_data/lcs")
```

---

## JSONStorage

Almacena cada índice como un archivo `.json` legible. **Este es el default cuando no se configura otro storage y no existe `lucis_meta.db`.**

> **Nota:** `from_dict()` y `from_list()` auto-persisten a `lucis_data/mi_indice.json` por defecto. El archivo se crea inmediatamente — no requiere llamar a `.save()`.

```python
from lucis import Lucis

luc = Lucis.from_dict(datos, name="mi_indice")
# → JSONStorage se usa por defecto
# → El archivo se guarda automáticamente en lucis_data/mi_indice.json

# Directorio personalizado
luc = Lucis.from_dict(datos, name="mi_indice", storage_dir="mis_datos")
```

**Ventajas:**
- Archivos legibles (puedes inspeccionarlos manualmente)
- Sin dependencias extra
- Simple

**Limitaciones:**
- No recomendado para datasets grandes (>50K documentos)
- Sin versionado ni rollback
- Serializa/deserializa el índice **completo** cada vez

---

## SQLiteStorage

Backend de persistencia completo usando SQLite. Almacena el índice completo (índice invertido, vectores de documentos, mapeo de IDs) en tablas `lucis_*` junto a tus tablas existentes.

```python
from lucis import Lucis

luc = Lucis.from_dict(
    datos,
    name="mi_indice",
    storage_type="sqlite",
    db_path="mi_app.db",
)
```

O directamente desde una tabla SQLite:

```python
luc = Lucis.from_sqlite_table(
    table_name="articulos",
    db_path="blog.db",
    text_column="contenido",
    id_column="id",
    name="blog_search",
)
# → Crea tablas lucis_* en blog.db
```

**Tablas creadas:**
- `lucis_inverted_index` — Índice invertido serializado
- `lucis_doc_vectors` — Vectores de documentos
- `lucis_id_mapping` — Mapeo ID interno → original
- `lucis_metadata` — Metadatos del índice
- `lucis_aliases` — Alias lógico → nombre físico
- `lucis_shard_registry` — Registro de shards

**Características:**
- Versionado automático (`save()` crea una nueva versión)
- Swaps atómicos de alias (cambio instantáneo de versión)
- `rollback()` y `purge_old_versions()` disponibles

---

## AlchemyStorage

Persistencia completa del índice vía SQLAlchemy para MySQL, PostgreSQL, MariaDB y cualquier base de datos compatible con SQLAlchemy. Crea tablas `lucis_*` en la base de datos destino.

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
luc = Lucis(
    name="mi_indice",
    storage_type="alchemy",
    alchemy_url="mysql+pymysql://usuario:pass@localhost/mi_bd",
)
luc.index(datos)
luc.save()
# → Crea tablas lucis_* en mi_bd
```

**Formatos de URL comunes:**

| Base de datos | URL |
|---|---|
| MySQL | `mysql+pymysql://user:pass@host/db` |
| PostgreSQL | `postgresql+psycopg2://user:pass@host/db` |
| MariaDB | `mariadb+pymysql://user:pass@host/db` |
| SQLite (vía Alchemy) | `sqlite:///path/to/db.sqlite` |

> **Nota:** `AlchemyStorage` tiene carga lazy — no requiere `sqlalchemy` a menos que uses explícitamente `storage_type="alchemy"`.

---

## AlchemyReader (adaptador de solo lectura)

Adaptador de **solo lectura** que se conecta a tu base de datos de producción para **ingerir datos**. **Nunca** crea ni modifica tablas `lucis_*` — solo lee de tus tablas existentes.

```python
from lucis.storage.alchemy_reader import AlchemyReader

reader = AlchemyReader(url="mysql+pymysql://user:pass@host/db")
datos = reader.read_table("articulos", text_column="contenido", id_column="id")
```

**Cuándo se usa:**
- Internamente por `from_alchemy_table()` y `from_alchemy_query()` durante la ingesta inicial.
- Por el `IndexWorker` cuando necesita re-leer datos frescos de la base de datos de producción para detectar cambios y disparar reindexaciones.
- **Seguro para producción** — solo ejecuta consultas `SELECT`.

---

## Auto-descubrimiento: cómo Lucis elige el storage

Cuando creas una instancia `Lucis` sin proporcionar explícitamente un parámetro `storage`, el constructor sigue esta lógica:

```
1. storage_type="alchemy" → AlchemyStorage (requiere alchemy_url)
2. storage_type="sqlite"  → SQLiteStorage (requiere db_path)
3. storage_type="json"    → JSONStorage (default)

PERO — después de elegir el storage "por defecto", verifica:
4. Si lucis_data/lcs/lucis_meta.db existe → cambia automáticamente a MetadataStorage
```

Esto significa que puedes recargar un índice creado por `from_alchemy_table()` simplemente con:

```python
# Sin necesidad de especificar storage — el auto-descubrimiento lo maneja
luc = Lucis(name="articulos_idx", engine="lite", binary_dir="auto")
resultados = luc.search("python")
```

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

**Métodos opcionales** (con defaults seguros):

| Método | Default | Descripción |
|---|---|---|
| `resolve_alias(name)` | Retorna `name` | Resolver alias → nombre físico |
| `set_alias(alias, target)` | No-op | Crear/actualizar alias |
| `get_alias(name)` | `None` | Obtener target de un alias |
| `list_versions(name)` | `[]` | Listar versiones del índice |
| `delete(name)` | No-op | Eliminar un índice |
| `save_shard_registry(name, keys)` | No-op | Guardar keys de shards |
| `load_shard_registry(name)` | `[]` | Cargar keys de shards |
| `save_source_info(name, info)` | No-op | Guardar info de tabla/columna fuente |
| `load_source_info(name)` | `None` | Cargar info de tabla/columna fuente |

```python
# Inyectar tu storage personalizado
luc = Lucis(name="mi_indice", storage=MiStorage())
```

---

## Siguiente paso

- [Funciones útiles](07-funciones-utiles.md) — Toolkit modular para búsqueda
- [Sharding temporal](08-sharding-temporal.md) — Partición mensual para grandes datasets