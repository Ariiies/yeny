# API Reference

Yeny v0.1.0 Public API Comprehensive Reference. For narrative guides, see previous pages.

---

## `Yeny` — Main class

```python
from yeny import Yeny
from yeny.config import YenyOptions, TableConfig, TableSource
```

### Constructor

```python
Yeny(
    name: str = "default",
    engine: str = "core",
    preprocessor: Optional[Callable] = None,
    *,
    autoload: bool = True,
    storage: Optional[BaseStorage] = None,
    options: Optional[YenyOptions] = None,
)
```

| Parameter | Type | Default | Description |
|---|---|---|---|
| `name` | `str` | `"default"` | Logical index name (used for persistence) |
| `engine` | `str` | `"core"` | Search engine |
| `preprocessor` | `Callable \| None` | `None` | Custom preprocessor. `None` uses the engine default |
| `autoload` | `bool` | `True` | If a saved index exists, load it automatically |
| `storage` | `BaseStorage \| None` | `None` | Injected storage; overrides declarative storage options |
| `options` | `YenyOptions \| None` | `None` | Advanced infrastructure; `None` uses the defaults below |

```python
@dataclass(frozen=True)
class YenyOptions:
    storage_dir: str = "yeny_data"
    storage_type: str = "json"
    db_path: Optional[str] = None
    connection_url: Optional[str] = None
    max_loaded_shards: int = 0
    memory_limit_mb: Optional[int] = None
    binary_dir: Optional[str] = "auto"

@dataclass(frozen=True)
class TableSource:
    table: str
    connection_url: str
    text_columns: Union[str, List[str]]
    id_column: Optional[str] = None
    date_column: Optional[str] = "auto"

@dataclass(frozen=True)
class TableConfig:
    where_clause: Optional[str] = None
    schema: Optional[str] = None
    shard_batch_size: int = 20_000
    stream_ordered: bool = False
```

`binary_dir="auto"` derives `<storage_dir>/yny`; `None` disables `.yny`
persistence; any other string is an explicit directory. An injected `storage`
always takes precedence over `YenyOptions.storage_type`, `db_path`, and
`connection_url`.

Read-only properties: `is_indexed`, `is_sharded`, `total_docs`,
`loaded_memory_mb`.

---

### Factory methods

#### `Yeny.from_dict(...)`

```python
@classmethod
def from_dict(
    data: Dict[Any, str],
    name: str = "default",
    *,
    engine: str = "core",
    preprocessor: Optional[Callable] = None,
    options: Optional[YenyOptions] = None,
) -> Yeny
```

Instantiate from a `{id: texto}` dictionary. Preserve the original IDs.

#### `Yeny.from_list(...)`

```python
@classmethod
def from_list(
    data: List[str],
    name: str = "default",
    *,
    engine: str = "core",
    preprocessor: Optional[Callable] = None,
    options: Optional[YenyOptions] = None,
) -> Yeny
```

Create instance from a list of texts. Auto-generated IDs (0, 1, 2...).

#### `Yeny.from_sqlite_table(...)`

```python
@classmethod
def from_sqlite_table(
    table_name: str,
    db_path: str,
    text_column: Union[str, List[str]],
    id_column: Optional[str] = None,
    where_clause: Optional[str] = None,
    name: str = "default",
    *,
    engine: str = "core",
    preprocessor: Optional[Callable] = None,
    options: Optional[YenyOptions] = None,
) -> Yeny
```

Reads rows from an SQLite table and builds the index.

#### `Yeny.from_sqlite_query(...)`

```python
@classmethod
def from_sqlite_query(
    query: str,
    db_path: str,
    name: str = "default",
    *,
    engine: str = "core",
    preprocessor: Optional[Callable] = None,
    options: Optional[YenyOptions] = None,
) -> Yeny
```

Run a SQL query against SQLite and build the index.

#### `Yeny.from_table(...)`

```python
@classmethod
def from_table(
    source: TableSource,
    name: str = "default",
    *,
    engine: str = "core",
    preprocessor: Optional[Callable] = None,
    config: Optional[TableConfig] = None,
    options: Optional[YenyOptions] = None,
) -> Yeny
```

Read from any database supported by SQLAlchemy (MySQL, PostgreSQL, etc.).

#### `Yeny.from_query(...)`

```python
@classmethod
def from_query(
    query: str,
    connection_url: str,
    name: str = "default",
    *,
    engine: str = "core",
    preprocessor: Optional[Callable] = None,
    options: Optional[YenyOptions] = None,
) -> Yeny
```

Run a SQL query against any SQLAlchemy database and build the index.

---

### Indexing

#### `index(data, persist=True)`

```python
def index(
    data: Union[List[str], Dict[Any, str]],
    persist: bool = True,
) -> None
```

Ingest data and build the index. Accept dict or list.

#### `reindex(data, dates=None)`

```python
def reindex(
    data: Union[List[str], Dict[Any, str]],
    dates: Optional[Dict[str, Any]] = None,
) -> None
```

Rebuild the index with fresh data. Create new version, swap aliases, keep the previous one for rollback.

#### `reindex_streaming(row_iter, batch_size=5000)`

```python
def reindex_streaming(
    row_iter,                    # Iterable[(doc_id, text, date)]
    batch_size: int = 5_000,
) -> None
```

Rebuild from a streaming iterator, without materializing everything in RAM. Only for sharded indexes.

#### `add_documents(new_docs, dates=None, persist=True)`

```python
def add_documents(
    new_docs: Union[List[str], Dict[Any, str]],
    dates: Optional[Dict[str, Any]] = None,
    persist: bool = True,
) -> None
```

Incrementally adds documents to the existing index.

#### `remove_documents(doc_ids, persist=True, fallback_rebuild=True)`

```python
def remove_documents(
    doc_ids: List[Any],
    persist: bool = True,
    fallback_rebuild: bool = True,
) -> int
```

Delete documents by ID. Returns deleted amount.

---

### Search

#### `search(query, top_k=10, since=None, until=None)`

```python
def search(
    query: Union[str, List[str]],
    top_k: int = 10,
    since: Optional[str] = None,
    until: Optional[str] = None,
) -> SearchResponse
```

Search the index. Returns `SearchResponse` with ranked results.

| Parameter | Description |
|---|---|
| `query` | Search text or list of pre-processed tokens |
| `top_k` | Maximum results |
| `since` | Start of time range (inclusive) — sharded only |
| `until` | End of time range (inclusive) — sharded only |

---

### Persistence

#### `save(name=None)`

```python
def save(self, name: Optional[str] = None) -> None
```

Save the index to storage. With automatic versioning.

#### `load(name=None)`

```python
def load(self, name: Optional[str] = None) -> None
```

Load the index from storage. If `name=None`, resolves the alias.

#### `list_versions()`

```python
def list_versions(self) -> List[str]
```

Lists all available physical versions of the index.

#### `generate_yny()`

Generates binary `.yny` files for all shards.

---

### Worker and health

#### `create_worker(...)`

```python
def create_worker(
    data_fn: Optional[Callable] = None,
    interval: float = 60,
    change_detector: Optional[Callable[[], bool]] = None,
    incremental: Optional[bool] = None,
    delta_fn: Optional[Callable] = None,
    auto_purge: bool = True,
    keep_versions: int = 2,
    on_rebuild: Optional[Callable] = None,
    on_error: Optional[Callable] = None,
    on_cycle: Optional[Callable] = None,
    streaming: bool = True,
    connection_url: Optional[str] = None,
) -> IndexWorker
```

Create a `IndexWorker` linked to this instance. If it was created from DB, it auto-generates `data_fn` and `change_detector`.

#### `health_check(benchmark_query=None)`

```python
def health_check(
    benchmark_query: Optional[str] = None,
) -> HealthReport
```

Returns a full health snapshot (RAM, docs, shards, worker, timing).

#### `health_monitor(interval=30)`

```python
def health_monitor(interval: float = 30) -> HealthMonitor
```

Create a periodic monitor. Call `.start()` / `.stop()`.

#### `connect_source(connection_url)`

```python
def connect_source(self, connection_url: str) -> None
```

Connects to the source database to auto-generate `data_fn` of the worker.

---

### Properties

| Property | Type | Description |
|---|---|---|
| `name` | `str` | Logical index name |
| `is_sharded` | `bool` | If you use temporary sharding |
| `total_docs` | `int` | Total documents indexed |
| `loaded_memory_mb` | `float` | RAM used by loaded shards (MB) |
| `preprocessor` | `Callable` | Active preprocessor |
| `engine` | `BaseEngine` | Engine instance |
| `storage` | `BaseStorage` | Storage instance |

---

## `IndexWorker`

```python
from yeny.core.worker import IndexWorker
```

| Method | Description |
|---|---|
| `start()` | Start the daemon thread |
| `stop(timeout=None)` | Stop the thread and wait |
| `is_running()` | `True` if the thread is active |
| `trigger_now()` | Immediate rebuild force (synchronous) |

| Attribute | Type | Description |
|---|---|---|
| `cycles` | `int` | Completed cycles |
| `rebuilds` | `int` | Successful rebuilds |
| `errors` | `int` | Failed rebuilds |
| `last_rebuild_time` | `float \| None` | Duration of last rebuild(s) |
| `stats` | `dict` | Statistics Snapshot |

---

## Engines

### `CoreEngine`

TF-IDF engine with cosine similarity. Default tokenizer: `WordTokenizer`.

```python
from yeny.engines.core import CoreEngine
```

### `LiteEngine`

Standardized TF engine. Default tokenizer: `CharNgramTokenizer(3)`.

```python
from yeny.engines.lite import LiteEngine
```

Both engines exhibit:

| Method | Description |
|---|---|
| `build_index(data)` | Build index from dict or list |
| `add_documents(data)` | Add documents (LiteEngine only) |
| `remove_documents(doc_ids)` | Delete documents (LiteEngine only) |
| `search(query, top_k)` | Search, return `List[Tuple[DocId, float]]` |
| `persist(name)` | Save to storage |
| `load_engine(name)` | Load from storage |

---

## Preprocessors

```python
from yeny.utils.nlp import (
    # Tokenizer classes (callable)
    SimpleTokenizer,        # split by spaces
    WordTokenizer,          # regex words, lowercase
    NgramTokenizer,         # word n-grams: NgramTokenizer(n)
    CharNgramTokenizer,     # character n-grams: CharNgramTokenizer(n)
    # Text cleaners
    lowercase,              # convert to lowercase
    uppercase,              # convert to uppercase
    strip_whitespace,       # trim and normalize spaces
    remove_extra_spaces,    # collapse repeated whitespace
    remove_punctuation,     # remove punctuation marks
    remove_numbers,         # remove digits
    remove_urls,            # remove URLs
    remove_emails,          # remove email addresses
    remove_html_tags,       # remove HTML tags
    normalize_unicode,      # strip diacritics
    remove_accents,         # alias of normalize_unicode
)
```

---

## Index functions

```python
from yeny.utils.index import (
    build_index,            # corpus → índice invertido
    get_bow,                # tokens → bag of words
    get_corpus_bows,        # corpus → lista de BOWs
    get_vocabulary,         # corpus → vocabulario ordenado
    get_tf_count,           # TF raw
    get_df_count,           # Document Frequency
    get_cf_count,           # Collection Frequency
    compute_tf,             # TF normalizado
    compute_idf,            # IDF (smoothed)
    compute_tfidf,          # TF × IDF
    get_doc_len,            # longitudes de documento
    compute_document_vector, # vector TF-IDF sparse
)
```

---

## Mathematical functions

```python
from yeny.utils.math.core import (
    dot_product,                    # producto punto denso
    vector_norm,                    # norma L2
    cosine_similarity,              # similitud coseno densa
    batch_cosine_similarity,        # batch de similitudes
    argsort_descending,             # índices ordenados desc
    sparse_dot_product,             # producto punto sparse
    sparse_vector_norm,             # norma L2 sparse
    sparse_cosine_similarity,       # similitud coseno sparse
    sort_results,                   # ordenar scores {id: score}
)
```

---

## Decorators

```python
from yeny.utils.decorators import (
    corpus_input,   # auto-tokeniza corpus si recibe strings
    doc_input,      # auto-tokeniza documento si recibe string
)
```

---

## Serialization

```python
from yeny.utils.serialization import dumps, loads, BACKEND
```

| Function | Description |
|---|---|
| `dumps(obj)` | Serializes to JSON string |
| `loads(text)` | Deserialize from JSON string |
| `BACKEND` | `"orjson"` if available, `"json"` if not |

---

## Storage backends

```python
from yeny.storage.json_storage import JSONStorage
from yeny.storage.sqlite_storage import SQLiteStorage
from yeny.storage.alchemy_storage import AlchemyStorage      # requiere sqlalchemy
from yeny.storage.metadata_storage import MetadataStorage
from yeny.storage import DatabaseReader                       # requires sqlalchemy
```

They all implement `BaseStorage`:

| Method | Description |
|---|---|
| `save_engine(name, data)` | Engine data persists |
| `load_engine(name)` | Load engine data |
| `exists(name)` | Check if an index exists |
| `delete(name)` | Delete an index |
| `list_all()` | List all indexes |
| `save_alias(alias, target)` | Create/update aliases |
| `resolve_alias(alias)` | Resolve alias to physical name |

---

## Data models

```python
from yeny.models.search import SearchResult, SearchResponse
from yeny.core.health import HealthReport, ShardHealth
```

Detailed in [Data models](12-data-models.md).

---

## Exceptions

```python
from yeny.exceptions import (
    YenyError,                 # base
    YenyEmptyCorpusError,      # corpus vacío
    YenyInvalidDocumentError,  # documento inválido
    YenyEngineError,           # error del motor
    YenySearchError,           # error en búsqueda
    YenyTokenizationError,     # error en tokenización
)
```

Detailed in [Exceptions](13-exceptions.md).

---

## Sharding

```python
from yeny.core.shard import (
    ShardManager,
    date_to_shard_key,
    normalize_to_shard_key,
    shard_key_in_range,
    YENY_GLOBAL_SHARD,              # "9999_99"
    YENY_DEFAULT_DATE_COLUMNS,      # ("created_at", "updated_at", "timestamp")
)
```

Detailed in [Temporary Sharding](08-temporary-sharding.md).

---

##Compact data structures

```python
from yeny.utils.compact import CompactPostings, CompactDocLengths
```

| Class | Description |
|---|---|
| `CompactPostings` | Posting list with parallel arrays. ~12× less RAM than dict. |
| `CompactDocLengths` | Document lengths in continuous array. O(1) lookup. |

Interface compatible with `dict` read-only (`.get()`, `.keys()`, `.items()`, `in`).
