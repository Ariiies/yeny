# Referencia API

Referencia exhaustiva de la API pública de Lucis v0.1.0. Para guías narrativas, consulta las páginas anteriores.

---

## `Lucis` — Clase principal

```python
from lucis import Lucis
```

### Constructor

```python
Lucis(
    name: str = "default",
    storage_dir: str = "lucis_data",
    storage_type: str = "json",          # "json" | "sqlite" | "alchemy"
    db_path: Optional[str] = None,
    alchemy_url: Optional[str] = None,
    storage: Optional[BaseStorage] = None,
    engine: str = "core",                # "core" | "lite"
    preprocessor: Optional[Callable] = None,
    autoload: bool = True,
    max_loaded_shards: int = 0,
    memory_limit_mb: Optional[int] = None,
    binary_dir: Optional[str] = "auto",
)
```

| Parámetro | Tipo | Default | Descripción |
|---|---|---|---|
| `name` | `str` | `"default"` | Nombre lógico del índice (usado para persistencia) |
| `storage_dir` | `str` | `"lucis_data"` | Directorio para archivos JSON |
| `storage_type` | `str` | `"json"` | Backend de almacenamiento |
| `db_path` | `str \| None` | `None` | Ruta a SQLite (requerido si `storage_type="sqlite"`) |
| `alchemy_url` | `str \| None` | `None` | URL SQLAlchemy (requerido si `storage_type="alchemy"`) |
| `storage` | `BaseStorage \| None` | `None` | Instancia de storage personalizada (sobreescribe `storage_type`) |
| `engine` | `str` | `"core"` | Motor de búsqueda |
| `preprocessor` | `Callable \| None` | `None` | Preprocesador personalizado. `None` usa el default del motor |
| `autoload` | `bool` | `True` | Si existe un índice guardado, cargarlo automáticamente |
| `max_loaded_shards` | `int` | `0` | Máximo de shards en RAM (0 = sin límite) |
| `memory_limit_mb` | `int \| None` | `None` | Presupuesto de RAM para shards en MB |
| `binary_dir` | `str \| None` | `"auto"` | Directorio para archivos `.lcs`. `"auto"` lo deriva del storage |

---

### Factory methods

#### `Lucis.from_dict(data, name, **kwargs)`

```python
@classmethod
def from_dict(
    data: Dict[Any, str],
    name: str = "default",
    **kwargs,
) -> Lucis
```

Crea instancia desde un diccionario `{id: texto}`. Preserva los IDs originales.

#### `Lucis.from_list(data, name, **kwargs)`

```python
@classmethod
def from_list(
    data: List[str],
    name: str = "default",
    **kwargs,
) -> Lucis
```

Crea instancia desde una lista de textos. IDs auto-generados (0, 1, 2...).

#### `Lucis.from_sqlite_table(...)`

```python
@classmethod
def from_sqlite_table(
    table_name: str,
    db_path: str,
    text_column: Union[str, List[str]],
    id_column: Optional[str] = None,
    where_clause: Optional[str] = None,
    name: str = "default",
    **kwargs,
) -> Lucis
```

Lee filas de una tabla SQLite y construye el índice.

#### `Lucis.from_sqlite_query(...)`

```python
@classmethod
def from_sqlite_query(
    query: str,
    db_path: str,
    text_column: Union[str, List[str]],
    id_column: Optional[str] = None,
    name: str = "default",
    **kwargs,
) -> Lucis
```

Ejecuta una query SQL contra SQLite y construye el índice.

#### `Lucis.from_alchemy_table(...)`

```python
@classmethod
def from_alchemy_table(
    alchemy_url: str,
    table_name: str,
    text_column: Union[str, List[str]],
    id_column: Optional[str] = None,
    date_column: Optional[str] = None,   # "auto" para auto-detección
    name: str = "default",
    **kwargs,
) -> Lucis
```

Lee desde cualquier base de datos soportada por SQLAlchemy (MySQL, PostgreSQL, etc.).

#### `Lucis.from_alchemy_query(...)`

```python
@classmethod
def from_alchemy_query(
    alchemy_url: str,
    query: str,
    text_column: Union[str, List[str]],
    id_column: Optional[str] = None,
    date_column: Optional[str] = None,
    name: str = "default",
    **kwargs,
) -> Lucis
```

Ejecuta una query SQL contra cualquier BD SQLAlchemy y construye el índice.

---

### Indexación

#### `index(data, persist=True)`

```python
def index(
    data: Union[List[str], Dict[Any, str]],
    persist: bool = True,
) -> None
```

Ingesta datos y construye el índice. Acepta dict o lista.

#### `reindex(data, dates=None)`

```python
def reindex(
    data: Union[List[str], Dict[Any, str]],
    dates: Optional[Dict[str, Any]] = None,
) -> None
```

Reconstruye el índice con datos frescos. Crea nueva versión, swapea alias, mantiene la anterior para rollback.

#### `reindex_streaming(row_iter, batch_size=5000)`

```python
def reindex_streaming(
    row_iter,                    # Iterable[(doc_id, text, date)]
    batch_size: int = 5_000,
) -> None
```

Reconstruye desde un iterador streaming, sin materializar todo en RAM. Solo para índices sharded.

#### `add_documents(new_docs, dates=None, persist=True)`

```python
def add_documents(
    new_docs: Union[List[str], Dict[Any, str]],
    dates: Optional[Dict[str, Any]] = None,
    persist: bool = True,
) -> None
```

Agrega documentos incrementalmente al índice existente.

#### `remove_documents(doc_ids, persist=True, fallback_rebuild=True)`

```python
def remove_documents(
    doc_ids: List[Any],
    persist: bool = True,
    fallback_rebuild: bool = True,
) -> int
```

Elimina documentos por ID. Retorna cantidad eliminada.

---

### Búsqueda

#### `search(query, top_k=10, since=None, until=None)`

```python
def search(
    query: Union[str, List[str]],
    top_k: int = 10,
    since: Optional[str] = None,
    until: Optional[str] = None,
) -> SearchResponse
```

Busca en el índice. Retorna `SearchResponse` con resultados rankeados.

| Parámetro | Descripción |
|---|---|
| `query` | Texto de búsqueda o lista de tokens pre-procesados |
| `top_k` | Máximo de resultados |
| `since` | Inicio del rango temporal (inclusive) — solo sharded |
| `until` | Fin del rango temporal (inclusive) — solo sharded |

---

### Persistencia

#### `save(name=None)`

```python
def save(self, name: Optional[str] = None) -> None
```

Guarda el índice al storage. Con versionamiento automático.

#### `load(name=None)`

```python
def load(self, name: Optional[str] = None) -> None
```

Carga el índice desde storage. Si `name=None`, resuelve el alias.

#### `list_versions()`

```python
def list_versions(self) -> List[str]
```

Lista todas las versiones físicas disponibles del índice.

#### `generate_lcs()`

Genera archivos `.lcs` binarios para todos los shards.

---

### Worker y salud

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
    source_url: Optional[str] = None,
) -> IndexWorker
```

Crea un `IndexWorker` vinculado a esta instancia. Si se creó desde BD, auto-genera `data_fn` y `change_detector`.

#### `health_check(benchmark_query=None)`

```python
def health_check(
    benchmark_query: Optional[str] = None,
) -> HealthReport
```

Retorna un snapshot completo de salud (RAM, docs, shards, worker, timing).

#### `health_monitor(interval=30)`

```python
def health_monitor(interval: float = 30) -> HealthMonitor
```

Crea un monitor periódico. Llamar `.start()` / `.stop()`.

#### `connect_source(url)`

```python
def connect_source(self, url: str) -> None
```

Conecta con la base de datos fuente para auto-generar `data_fn` del worker.

---

### Propiedades

| Propiedad | Tipo | Descripción |
|---|---|---|
| `name` | `str` | Nombre lógico del índice |
| `is_sharded` | `bool` | Si usa sharding temporal |
| `total_docs` | `int` | Total de documentos indexados |
| `loaded_memory_mb` | `float` | RAM usada por shards cargados (MB) |
| `preprocessor` | `Callable` | Preprocesador activo |
| `engine` | `BaseEngine` | Instancia del motor |
| `storage` | `BaseStorage` | Instancia del storage |

---

## `IndexWorker`

```python
from lucis.core.worker import IndexWorker
```

| Método | Descripción |
|---|---|
| `start()` | Inicia el daemon thread |
| `stop(timeout=None)` | Detiene el thread y espera |
| `is_running()` | `True` si el thread está activo |
| `trigger_now()` | Fuerza rebuild inmediato (síncrono) |

| Atributo | Tipo | Descripción |
|---|---|---|
| `cycles` | `int` | Ciclos completados |
| `rebuilds` | `int` | Rebuilds exitosos |
| `errors` | `int` | Rebuilds fallidos |
| `last_rebuild_time` | `float \| None` | Duración del último rebuild (s) |
| `stats` | `dict` | Snapshot de estadísticas |

---

## Motores

### `CoreEngine`

Motor TF-IDF con similitud coseno. Tokenizador default: `word_tokenizer`.

```python
from lucis.engines.core import CoreEngine
```

### `LiteEngine`

Motor TF normalizado. Tokenizador default: `char_ngram_tokenizer(3)`.

```python
from lucis.engines.lite import LiteEngine
```

Ambos motores exponen:

| Método | Descripción |
|---|---|
| `build_index(data)` | Construye índice desde dict o lista |
| `add_documents(data)` | Agrega documentos (solo LiteEngine) |
| `remove_documents(doc_ids)` | Elimina documentos (solo LiteEngine) |
| `search(query, top_k)` | Busca, retorna `List[Tuple[DocId, float]]` |
| `persist(name)` | Guarda al storage |
| `load_engine(name)` | Carga desde storage |

---

## Preprocesadores

```python
from lucis.utils.nlp import (
    simple_tokenizer,       # split por espacios
    word_tokenizer,         # regex \w+, lowercase
    ngram_tokenizer,        # n-gramas de palabras
    char_ngram_tokenizer,   # n-gramas de caracteres
    clean_whitespace,       # normalizar espacios
    clean_html,             # eliminar tags HTML
    clean_urls,             # eliminar URLs
    clean_emails,           # eliminar emails
    clean_numbers,          # eliminar números
    clean_special_chars,    # eliminar caracteres especiales
    clean_accents,          # eliminar acentos
    clean_repeated_chars,   # eliminar chars repetidos
    lowercase,              # convertir a minúsculas
    truncate,               # truncar a N caracteres
)
```

---

## Funciones de índice

```python
from lucis.utils.index import (
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

## Funciones matemáticas

```python
from lucis.utils.math.core import (
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

## Decoradores

```python
from lucis.utils.decorators import (
    corpus_input,   # auto-tokeniza corpus si recibe strings
    doc_input,      # auto-tokeniza documento si recibe string
)
```

---

## Serialización

```python
from lucis.utils.serialization import dumps, loads, BACKEND
```

| Función | Descripción |
|---|---|
| `dumps(obj)` | Serializa a JSON string |
| `loads(text)` | Deserializa desde JSON string |
| `BACKEND` | `"orjson"` si disponible, `"json"` si no |

---

## Storage backends

```python
from lucis.storage.json_storage import JSONStorage
from lucis.storage.sqlite_storage import SQLiteStorage
from lucis.storage.alchemy_storage import AlchemyStorage      # requiere sqlalchemy
from lucis.storage.metadata_storage import MetadataStorage
from lucis.storage.alchemy_reader import AlchemyReader         # requiere sqlalchemy
```

Todos implementan `BaseStorage`:

| Método | Descripción |
|---|---|
| `save_engine(name, data)` | Persiste datos del motor |
| `load_engine(name)` | Carga datos del motor |
| `exists(name)` | Verifica si un índice existe |
| `delete(name)` | Elimina un índice |
| `list_all()` | Lista todos los índices |
| `save_alias(alias, target)` | Crea/actualiza alias |
| `resolve_alias(alias)` | Resuelve alias a nombre físico |

---

## Modelos de datos

```python
from lucis.models.search import SearchResult, SearchResponse
from lucis.core.health import HealthReport, ShardHealth
```

Detallados en [Modelos de datos](12-modelos-datos.md).

---

## Excepciones

```python
from lucis.exceptions import (
    LucisError,                 # base
    LucisEmptyCorpusError,      # corpus vacío
    LucisInvalidDocumentError,  # documento inválido
    LucisEngineError,           # error del motor
    LucisSearchError,           # error en búsqueda
    LucisTokenizationError,     # error en tokenización
)
```

Detalladas en [Excepciones](13-excepciones.md).

---

## Sharding

```python
from lucis.core.shard import (
    ShardManager,
    date_to_shard_key,
    normalize_to_shard_key,
    shard_key_in_range,
    LUCIS_GLOBAL_SHARD,              # "9999_99"
    LUCIS_DEFAULT_DATE_COLUMNS,      # ("created_at", "updated_at", "timestamp")
)
```

Detallado en [Sharding temporal](08-sharding-temporal.md).

---

## Compact data structures

```python
from lucis.utils.compact import CompactPostings, CompactDocLengths
```

| Clase | Descripción |
|---|---|
| `CompactPostings` | Posting list con arrays paralelos. ~12× menos RAM que dict. |
| `CompactDocLengths` | Longitudes de documento en array continuo. O(1) lookup. |

Interfaz compatible con `dict` read-only (`.get()`, `.keys()`, `.items()`, `in`).
