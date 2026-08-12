# Storage

Lucis supports multiple storage backends, all implementing the same interface (`BaseStorage`). The recommended production setup uses **binary `.lcs` files** for index data plus **SQLite WAL** for lightweight metadata — giving you near-zero RAM loading via memory-mapped I/O and concurrent reader/writer access.

---

## Storage backends at a glance

| Backend | Index data | Metadata | Use case |
|---|---|---|---|
| **MetadataStorage** | `.lcs` binaries (mmap) | SQLite (WAL) | **Production default.** Used automatically by `from_table` and when reloading an existing index. |
| **JSONStorage** | `.json` files | `.json` files | Simple / debugging / small datasets. |
| **SQLiteStorage** | `lucis_*` tables in your DB | `lucis_*` tables | Full SQLite persistence, with versioning and rollback. |
| **AlchemyStorage** | `lucis_*` tables via SQLAlchemy | `lucis_*` tables | Full remote-DB persistence (MySQL, PostgreSQL, etc.). |
| **DatabaseReader** | *Read-only* (no writes) | *None* | Ingest data from your DB without creating any `lucis_*` tables. |

---

## MetadataStorage + `.lcs` (recommended)

This is the storage architecture used when ingesting from a database via `from_table()` or `from_query()`. It is also auto-discovered when reloading an index that was previously created this way.

### How it works

```
┌──────────────────────────────────────────────────┐
│                 lucis_data/lcs/                   │
│                                                   │
│  lucis_meta.db  ←── SQLite WAL                    │
│  ├─ lucis_metadata     (doc counts, engine name)  │
│  ├─ lucis_aliases      (alias → physical name)    │
│  ├─ lucis_shard_registry (shard keys)             │
│  └─ lucis_metadata.source_* (table/column info)   │
│                                                   │
│  *.lcs files     ←── mmap binaries                │
│  ├─ inverted index (CompactPostings)              │
│  ├─ doc lengths   (CompactDocLengths)             │
│  └─ id mapping    (internal → original)           │
└──────────────────────────────────────────────────┘
```

**Key points:**

- `.lcs` files contain the **actual index data** (inverted index, doc lengths, ID mapping). They are loaded via memory-mapped I/O: the OS maps the file without copying it into Python's heap, giving you near-zero RAM overhead.
- `lucis_meta.db` stores **only lightweight metadata**: document counts, aliases, shard registry, and source table information (so the worker knows what to monitor). It uses WAL mode for concurrent reads/writes.
- **Your production database is never touched** beyond the initial ingestion. `DatabaseReader` is read-only — it connects, reads rows, and disconnects. Zero `lucis_*` tables are created in your DB.

### When it's used automatically

```python
# Case 1: Ingestion from a database table
from lucis.config import TableSource

luc = Lucis.from_table(
    TableSource(
        table="articles",
        connection_url="mysql+pymysql://user:pass@host/db",
        text_columns="content",
        id_column="id",
    ),
    name="articles_idx",
)
# → MetadataStorage is created automatically
# → Index data goes to .lcs files
# → Metadata goes to lucis_data/lcs/lucis_meta.db
# → Your MySQL DB is untouched

# Case 2: Reloading an existing index (no explicit storage)
luc = Lucis(name="articles_idx", engine="lite")
# → Lucis auto-discovers lucis_data/lcs/lucis_meta.db
# → MetadataStorage is used transparently
# → .lcs files are loaded via mmap
```

### Manual creation

```python
from lucis import Lucis, MetadataStorage
from lucis.config import LucisOptions

storage = MetadataStorage(db_path="lucis_data/lcs/lucis_meta.db")
luc = Lucis(
    name="my_idx",
    storage=storage,
    options=LucisOptions(binary_dir="lucis_data/lcs"),
)
```

---

## JSONStorage

Stores each index as a readable `.json` file. **This is the default when no other storage is configured and no existing `lucis_meta.db` is found.**

> **Note:** `from_dict()` and `from_list()` auto-persist to `lucis_data/my_index.json` by default. The file is created immediately — no `.save()` call needed.

```python
from lucis import Lucis
from lucis.config import LucisOptions

luc = Lucis.from_dict(data, name="my_index")
# → JSONStorage is used by default
# → File is saved automatically at lucis_data/my_index.json

# Custom directory
luc = Lucis.from_dict(
    data,
    name="my_index",
    options=LucisOptions(storage_dir="my_data"),
)
```

**Advantages:**
- Human-readable files (inspect them manually)
- Zero extra dependencies
- Simple

**Limitations:**
- Not recommended for large datasets (>50K documents)
- No versioning or rollback
- Serializes/deserializes the **entire** index every time

---

## SQLiteStorage

Full-featured persistence backend using SQLite. Stores the complete index (inverted index, doc vectors, ID mapping) in `lucis_*` tables alongside your existing tables.

```python
from lucis import Lucis
from lucis.config import LucisOptions

luc = Lucis.from_dict(
    data,
    name="my_index",
    options=LucisOptions(storage_type="sqlite", db_path="my_app.db"),
)
```

Or directly from a SQLite table:

```python
luc = Lucis.from_sqlite_table(
    table_name="articles",
    db_path="blog.db",
    text_column="content",
    id_column="id",
    name="blog_search",
)
# → Creates lucis_* tables in blog.db
```

**Tables created:**
- `lucis_inverted_index` — Serialized inverted index
- `lucis_doc_vectors` — Document vectors
- `lucis_id_mapping` — Mapping internal → original ID
- `lucis_metadata` — Index metadata
- `lucis_aliases` — Logical alias → physical name
- `lucis_shard_registry` — Shard registration

**Features:**
- Automatic versioning (`save()` creates a new version)
- Atomic alias swaps (instant version switching)
- `rollback()` and `purge_old_versions()` available

---

## AlchemyStorage

Full-index persistence via SQLAlchemy for MySQL, PostgreSQL, MariaDB, and any SQLAlchemy-compatible database. Creates `lucis_*` tables in the target database.

**Installation:**

```bash
# Base
pip install lucis[alchemy]

# MySQL
pip install lucis[mysql]

# PostgreSQL
pip install lucis[postgresql]
```

**Usage:**

```python
luc = Lucis(
    name="my_index",
    options=LucisOptions(
        storage_type="alchemy",
        connection_url="mysql+pymysql://user:pass@localhost/mydb",
    ),
)
luc.index(data)
luc.save()
# → Creates lucis_* tables in mydb
```

**Common URL formats:**

| Database | URL |
|---|---|
| MySQL | `mysql+pymysql://user:pass@host/db` |
| PostgreSQL | `postgresql+psycopg2://user:pass@host/db` |
| MariaDB | `mariadb+pymysql://user:pass@host/db` |
| SQLite (via Alchemy) | `sqlite:///path/to/db.sqlite` |

> **Note:** `AlchemyStorage` is lazy-loaded — it does not require `sqlalchemy` unless you explicitly use `LucisOptions(storage_type="alchemy", ...)`.

---

## DatabaseReader (read-only adapter)

**Read-only** adapter that connects to your production database to **ingest data**. It **never** creates or modifies any `lucis_*` tables — it only reads from your existing tables.

```python
from lucis.storage import DatabaseReader

reader = DatabaseReader(
    connection_url="mysql+pymysql://user:pass@host/db"
)
data = reader.read_table("articles", text_columns="content", id_column="id")
```

**When it's used:**
- Internally by `from_table()` and `from_query()` during the initial ingestion.
- By the `IndexWorker` when it needs to re-read fresh data from the production database to detect changes and trigger reindexing.
- **Safe for production** — it only executes `SELECT` queries.

---

## Auto-discovery: how Lucis picks the storage

When you create a `Lucis` instance without explicitly providing a `storage` parameter, the constructor follows this logic:

```
1. `options.storage_type="alchemy"` → AlchemyStorage (requires `connection_url`)
2. `options.storage_type="sqlite"` → SQLiteStorage (requires `db_path`)
3. `options.storage_type="json"` → JSONStorage (default)

BUT — after choosing the "default" storage, it checks:
4. If lucis_data/lcs/lucis_meta.db exists → auto-switch to MetadataStorage
```

This means you can reload an index created by `from_table()` with just:

```python
# No need to specify storage — auto-discovery handles it
luc = Lucis(name="articles_idx", engine="lite")
response = luc.search("python")
```

`LucisOptions.binary_dir` is tri-state: `"auto"` (the default) derives
`<storage_dir>/lcs`, `None` disables binary persistence, and an explicit path
stores `.lcs` and metadata there. SQLAlchemy factories use metadata-only
storage, so their indexes need `"auto"` or an explicit binary directory to be
reloadable; `None` is appropriate only when persistence is intentionally
disabled for that run.

---

## Creating your own storage

You can create custom backends by extending `BaseStorage`:

```python
from lucis.storage.base import BaseStorage

class MyStorage(BaseStorage):
    def save(self, engine_state: dict, name: str) -> None:
        """Serialize and save engine state."""
        ...

    def load(self, name: str) -> dict:
        """Deserialize and return engine state."""
        ...

    def exists(self, name: str) -> bool:
        """Check if an index exists."""
        ...
```

**Optional methods** (safe defaults provided):

| Method | Default | Description |
|---|---|---|
| `resolve_alias(name)` | Returns `name` | Resolve alias → physical name |
| `set_alias(alias, target)` | No-op | Create/update alias |
| `get_alias(name)` | `None` | Get target of an alias |
| `list_versions(name)` | `[]` | List index versions |
| `delete(name)` | No-op | Delete an index |
| `save_shard_registry(name, keys)` | No-op | Save shard keys |
| `load_shard_registry(name)` | `[]` | Load shard keys |
| `save_source_info(name, info)` | No-op | Save source table/column info |
| `load_source_info(name)` | `None` | Load source table/column info |

```python
# Inject your custom storage
luc = Lucis(name="my_index", storage=MyStorage())
```

---

## Next step

- [Utility Functions](07-utility-functions.md) — Modular search toolkit
- [Temporal Sharding](08-temporary-sharding.md) — Monthly partitioning for large datasets
