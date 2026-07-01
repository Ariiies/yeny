# Storage

Lucis supports multiple storage backends. They all implement the same interface (`BaseStorage`), so you can switch between them without modifying your search code.

---

## JSONStorage (default)

Stores each index as a readable `.json` file. Ideal for learning, debugging and small projects.

```python
from lucis import Lucis

# Se usa por defecto
buscador = Lucis.from_dict(datos, name="mi_indice")
# Los archivos se guardan en lucis_data/mi_indice.json

# Personalizar directorio
buscador = Lucis.from_dict(datos, name="mi_indice", storage_dir="mis_datos")
```

**Advantages:**
- Readable files (you can inspect them manually)
- No dependencies
- Simple

**Limitations:**
- Not recommended for large datasets (>50K documents)
- No versioning or aliasing
- Serialize/deserialize the entire index every time

---

## SQLiteStorage

Production backend using SQLite. Supports versioning, aliases and shard registry.

```python
from lucis import Lucis

buscador = Lucis.from_dict(
    datos,
    name="mi_indice",
    storage_type="sqlite",
    db_path="mi_app.db"
)
```

Or directly from a SQLite table:

```python
buscador = Lucis.from_sqlite_table(
    table_name="articulos",
    db_path="blog.db",
    text_column="contenido",
    id_column="id",
    name="blog_search"
)
```

**Features:**
- Automatic versioning (every `save()` creates a new version)
- Atomic alias (instant swap between versions)
- Shard registry for temporary indexes
- Prefixed `lucis_*` tables (they never collide with your tables)
- `rollback()` and `purge_old_versions()` available

**Tables created:**
- `lucis_metadata` — Index metadata
- `lucis_inverted_index` — Serialized inverted index
- `lucis_doc_vectors` — Document Vectors
- `lucis_id_mapping` — Mapping internal ID → original ID
- `lucis_aliases` — Logical alias → physical name
- `lucis_shard_registry` — Shard registration

---

##AlchemyStorage

Production backend for MySQL, PostgreSQL, MariaDB, Oracle, SQL Server and any database supported by SQLAlchemy.

**Installation:**

```bash
# Base
pip install lucis[alchemy]

# MySQL
pip install lucis[mysql]

# PostgreSQL
pip install lucis[postgresql]
```

**Use:**

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

Or with explicit storage:

```python
buscador = Lucis(
    name="mi_indice",
    storage_type="alchemy",
    alchemy_url="mysql+pymysql://usuario:clave@localhost/mi_bd"
)
```

**Common URL format:**

| Database | URL |
|---|---|
| MySQL | `mysql+pymysql://user:pass@host/db` |
| PostgreSQL | `postgresql+psycopg2://user:pass@host/db` |
| MariaDB | `mariadb+pymysql://user:pass@host/db` |
| SQLite (via Alchemy) | `sqlite:///path/to/db.sqlite` |

**Features:**
- Everything about SQLiteStorage (versioning, aliases, shard registry)
- Real multi-BD support
- Lazy-loading: `AlchemyStorage` is only imported if needed (does not require sqlalchemy if you don't use it)

---

## MetadataStorage

Optimized backend that stores **metadata only** in SQLite (with WAL for concurrent access). Heavy index data lives in binary `.lcs` files.

```python
from lucis import MetadataStorage

storage = MetadataStorage(db_path="lucis_data/lcs/lucis_meta.db")
```

Normally you don't need to create `MetadataStorage` manually — it is used automatically when you work with `from_alchemy_table()` and `.lcs` files.

**When to use:**
- Indexes with `binary_dir="auto"` (.lcs files)
- Production with mmap (memory-mapped I/O)
- The lightest DB scheme possible

**Tables created:**
- `lucis_metadata` — Basic metadata (total_docs, engine_name, etc.)
- `lucis_aliases` — Logical alias → physical name
- `lucis_shard_registry` — Shard registration

---

##AlchemyReader

**Read-only** adapter to access user database tables. Unlike `AlchemyStorage`, it **never** creates or writes `lucis_*` tables.

```python
from lucis import AlchemyReader

reader = AlchemyReader(url="mysql+pymysql://user:pass@host/db")
datos = reader.read_table("articulos", text_column="contenido", id_column="id")
```

**When to use:**
- When the worker needs to read fresh data from the production database
- Used internally by `from_alchemy_table()` and `create_worker()`
- Read-only reading = safe for production DB

---

## Creating your own storage

You can create custom backends by extending `BaseStorage`:

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

The optional methods (alias, versioned, shard registry) have safe defaults, so your backend works out of the box:

```python
# Inyectar tu storage personalizado
buscador = Lucis(name="mi_indice", storage=MiStorage())
```

**Optional methods you can override:**

| Method | Default | Description |
|---|---|---|
| `resolve_alias(name)` | Returns `name` | Resolve alias → physical name |
| `set_alias(alias, target)` | No-op | Create/update aliases |
| `get_alias(name)` | `None` | Get target from an alias |
| `list_versions(name)` | `[]` | List index versions |
| `delete(name)` | No-op | Delete an index |
| `save_shard_registry(name, keys)` | No-op | Save shard keys |
| `load_shard_registry(name)` | `[]` | Load shard keys |

---

## Next step

- [Useful Features](funciones-utiles.md) — Modular Search Toolkit
- [Temporary Sharding](sharding-temporal.md) — Monthly partitioning for large datasets