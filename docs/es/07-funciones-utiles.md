# Funciones útiles — Toolkit Standalone

Los módulos internos de Lucis están diseñados para ser **usables de forma independiente**. Puedes importar funciones individuales para construir tus propios motores de búsqueda, hacer análisis de texto, o calcular similitudes sin usar la clase `Lucis`.

---

## Construcción de índices

### `build_index(corpus)`

Construye un índice invertido compacto en un solo paso O(n). Retorna `Dict[str, CompactPostings]`.

```python
from lucis.utils.index import build_index

corpus = [
    ["hola", "mundo", "hola"],
    ["python", "mundo"]
]

indice = build_index(corpus)

# Representación lógica:
# "hola"   → {0: 2}        (doc 0, 2 veces)
# "mundo"  → {0: 1, 1: 1}  (doc 0 y 1, 1 vez cada uno)
# "python" → {1: 1}        (doc 1, 1 vez)

# Acceder a postings
print(indice["hola"].get(0))    # 2
print(indice["mundo"].get(1))   # 1
print(indice["python"].get(0))  # 0 (no existe)
```

También acepta strings crudos (se tokenizan automáticamente con `word_tokenizer`):

```python
indice = build_index([
    "hola mundo hola",
    "python mundo"
])
```

> **📦 Nota — CompactPostings**
>
> `build_index` retorna posting lists como `CompactPostings`, no como diccionarios Python.
> Son ~12× más eficientes en RAM y se comportan como diccionarios read-only (`.get()`, `.keys()`, `.items()`, `in`).
> Usa `.to_dict()` si necesitas un dict regular.

### `get_bow(tokens)`

Genera un Bag of Words para un documento individual:

```python
from lucis.utils.index import get_bow

bow = get_bow(["python", "es", "genial", "python"])
# {"python": 2, "es": 1, "genial": 1}

# También acepta strings:
bow = get_bow("python es genial python")
# {"python": 2, "es": 1, "genial": 1}
```

### `get_corpus_bows(corpus)`

Genera Bag of Words para un corpus completo:

```python
from lucis.utils.index import get_corpus_bows

bows = get_corpus_bows(["hola mundo", "python hola"])
# [{"hola": 1, "mundo": 1}, {"python": 1, "hola": 1}]
```

### `get_vocabulary(corpus)`

Extrae el vocabulario único y ordenado del corpus:

```python
from lucis.utils.index import get_vocabulary

vocab = get_vocabulary(["hola mundo", "python mundo"])
# ["hola", "mundo", "python"]
```

---

## Estadísticas de índice

Todas las funciones aceptan un índice con estructura `{word: {doc_id: count, ...}, ...}`.

### Frecuencias raw

```python
from lucis.utils.index import get_tf_count, get_df_count, get_cf_count

indice = build_index(["python es genial", "python domina", "java también existe"])

# Term Frequency: ¿cuántas veces aparece "python" en el documento 0?
get_tf_count("python", 0, indice)  # 1

# Document Frequency: ¿en cuántos documentos aparece "python"?
get_df_count("python", indice)     # 2

# Collection Frequency: total de ocurrencias de "python" en todo el corpus
get_cf_count("python", indice)     # 2
```

### TF-IDF

```python
from lucis.utils.index import compute_tf, compute_idf, compute_tfidf, get_doc_len

indice = build_index(["python es genial", "python domina la ia", "java también existe"])
total_docs = 3
doc_lengths = get_doc_len(indice, total_docs)

# TF normalizado: count / |doc|
tf = compute_tf("python", 0, indice, doc_lengths)

# IDF (smoothed por defecto): log((N+1)/(df+1)) + 1
idf = compute_idf("python", indice, total_docs)

# TF-IDF = tf × idf
tfidf = compute_tfidf("python", 0, indice, doc_lengths, total_docs)
print(f"TF={tf:.4f}, IDF={idf:.4f}, TF-IDF={tfidf:.4f}")
```

### `get_doc_len(index, total_docs)`

Reconstruye las longitudes de documento desde el índice invertido:

```python
from lucis.utils.index import get_doc_len

lengths = get_doc_len(indice, 3)
# {0: 3, 1: 4, 2: 3}  — total de tokens por documento
```

### `compute_document_vector(doc_id, index, doc_lengths, total_docs)`

Crea un vector sparse TF-IDF para un documento (solo entradas no-cero):

```python
from lucis.utils.index import compute_document_vector

vector = compute_document_vector(0, indice, doc_lengths, total_docs)
# {"python": 0.1234, "es": 0.5678, "genial": 0.5678}
```

---

## Funciones matemáticas (Python puro)

Funciones para operaciones con vectores, sin dependencias externas.

### Vectores densos

```python
from lucis.utils.math.core import (
    dot_product,
    vector_norm,
    cosine_similarity,
    batch_cosine_similarity,
    argsort_descending,
)

vec_a = [0.5, 0.3, 0.0, 0.8]
vec_b = [0.2, 0.7, 0.1, 0.4]

# Producto punto
dot_product(vec_a, vec_b)  # 0.63

# Norma L2 (euclidiana)
vector_norm(vec_a)  # 0.9899...

# Similitud coseno
cosine_similarity(vec_a, vec_b)  # 0.6816...

# Índices ordenados por valor descendente (para ranking)
values = [0.2, 0.8, 0.5, 0.1]
argsort_descending(values)  # [1, 2, 0, 3]
```

### Batch de similitudes

```python
from lucis.utils.math.core import batch_cosine_similarity

query = [0.5, 0.3, 0.8]
documentos = [
    [0.2, 0.7, 0.4],
    [0.9, 0.1, 0.6],
    [0.0, 0.5, 0.3],
]

# Calcula similitud coseno con cada documento (generator)
for score in batch_cosine_similarity(query, documentos):
    print(f"  score={score:.4f}")
```

### Vectores sparse

Para vectores con muchos ceros (como TF-IDF), es más eficiente trabajar con diccionarios:

```python
from lucis.utils.math.core import (
    sparse_dot_product,
    sparse_vector_norm,
    sparse_cosine_similarity,
)

vec_a = {"python": 0.5, "web": 0.3, "django": 0.8}
vec_b = {"python": 0.7, "api": 0.4, "django": 0.2}

# Producto punto sparse — solo itera sobre claves comunes
sparse_dot_product(vec_a, vec_b)  # 0.51

# Norma L2 sparse
sparse_vector_norm(vec_a)  # 0.9899...

# Similitud coseno sparse
sparse_cosine_similarity(vec_a, vec_b)  # 0.5678...
```

### Ordenar resultados

```python
from lucis.utils.math.core import sort_results

scores = {0: 0.85, 1: 0.32, 2: 0.91, 3: 0.45}
top = sort_results(scores, limit=2)
# [(2, 0.91), (0, 0.85)]
```

---

<!-- 
## 🔮 Próximamente — Funciones aceleradas con NumPy

En futuras versiones, las funciones de `lucis.utils.math.plus` y
`lucis.utils.index.statsplus` ofrecerán versiones aceleradas con NumPy:

- `dot_product_plus`, `cosine_similarity_plus` — SIMD-optimized
- `batch_cosine_similarity_plus` — matrix multiplication en una llamada
- `pairwise_cosine_similarity_plus` — matriz n×n de similitud
- `top_k_similar_plus` — argpartition O(n) en vez de O(n log n)
- `compute_tfidf_plus` — Matriz TF-IDF densa (docs × vocab)
- `compute_sparse_tfidf_matrix` — Matriz sparse CSR con scipy

Instalar con: `pip install lucis[plus]`
-->

## Decoradores utilitarios

Lucis incluye decoradores que automatizan la normalización de input:

### `@corpus_input(tokenizer)`

Auto-tokeniza el corpus si recibe strings crudos:

```python
from lucis.utils.decorators import corpus_input
from lucis.utils.nlp import word_tokenizer

@corpus_input(word_tokenizer)
def mi_funcion(corpus):
    """corpus será List[List[str]] — ya tokenizado."""
    for doc_tokens in corpus:
        print(doc_tokens)

# Ambas llamadas son equivalentes:
mi_funcion(["hola mundo", "python web"])
mi_funcion([["hola", "mundo"], ["python", "web"]])
```

### `@doc_input(tokenizer)`

Auto-tokeniza un documento o query individual:

```python
from lucis.utils.decorators import doc_input
from lucis.utils.nlp import word_tokenizer

@doc_input(word_tokenizer)
def procesar(tokens):
    """tokens será List[str] — ya tokenizado."""
    return tokens

procesar("hola mundo")         # → ["hola", "mundo"]
procesar(["hola", "mundo"])    # → ["hola", "mundo"]
```

---

## Serialización

Lucis auto-selecciona el serializador JSON más rápido disponible:

```python
from lucis.utils.serialization import dumps, loads, BACKEND

print(BACKEND)  # "orjson" si está instalado, sino "json"

texto = dumps({"hola": 42, "mundo": [1, 2, 3]})  # str
objeto = loads(texto)                              # dict
```

- **orjson**: ~4× más rápido que stdlib, se usa automáticamente si está instalado
- **json**: stdlib, sin dependencias

Ambos producen `str` (no bytes), compatible con columnas SQL TEXT.

---

## Siguiente paso

- [Sharding temporal](sharding-temporal.md) — Partición mensual para grandes datasets
- [IndexWorker](worker.md) — Reindexación automática
