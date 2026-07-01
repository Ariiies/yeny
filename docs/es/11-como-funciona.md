# Cómo funciona Lucis

Esta página explica los internos del motor de búsqueda: qué estructuras de datos se construyen, cómo se calcula la relevancia, y cómo se optimiza la memoria.

---

## Índice invertido

El corazón de Lucis es un **índice invertido** (inverted index): un diccionario que mapea cada palabra del vocabulario a la lista de documentos donde aparece, junto con su frecuencia.

### Ejemplo conceptual

Dado el corpus:

| doc\_id | texto |
|---|---|
| 0 | "python es genial" |
| 1 | "python domina la web" |
| 2 | "java también es genial" |

El índice invertido resultante sería:

```
"python"   → {0: 1, 1: 1}
"es"       → {0: 1, 2: 1}
"genial"   → {0: 1, 2: 1}
"domina"   → {1: 1}
"la"       → {1: 1}
"web"      → {1: 1}
"java"     → {2: 1}
"también"  → {2: 1}
```

Cada entrada (`{doc_id: frecuencia}`) se llama **posting list**.

### Construcción O(n)

`build_index` construye el índice en un solo recorrido del corpus:

1. Para cada documento, se cuentan las frecuencias de cada token (Bag of Words).
2. Cada par `(token, doc_id, freq)` se inserta en el índice invertido.
3. Las posting lists se comprimen en `CompactPostings` (ver abajo).

---

## CompactPostings — Posting lists eficientes

En lugar de diccionarios Python (`{doc_id: freq}`), Lucis almacena cada posting list como dos arrays paralelos ordenados:

```
CompactPostings:
  _doc_ids:  [0, 1, 42, 999, ...]     ← array.array('i'), ordenados
  _freqs:    [2, 1,  5,   3, ...]     ← array.array('I'), paralelo
```

**¿Por qué?**

| Estructura | RAM por entrada | Lookup |
|---|---|---|
| `dict` Python | ~100 bytes | O(1) |
| `CompactPostings` | ~8 bytes | O(log n) bisect |

En un índice de 2M documentos, esto reduce la RAM de ~3.5 GB a ~300–400 MB (**~90% de ahorro**). El lookup por bisect es O(log n), pero el layout contiguo en memoria es mucho más cache-friendly.

La interfaz es compatible con diccionarios:

```python
# CompactPostings se comporta como dict read-only
postings.get(42)       # frecuencia del doc 42, o 0
postings.keys()        # array de doc_ids
postings.items()       # iterador (doc_id, freq)
42 in postings         # True/False
postings.to_dict()     # {42: 5, 999: 3, ...} — dict regular
```

---

## CompactDocLengths

Las longitudes de documento (cantidad total de tokens) también usan un array compacto en vez de diccionario:

```
CompactDocLengths:
  _data: array.array('I', [15, 23, 8, 42, ...])
  # índice = doc_id, valor = longitud
```

Lookup O(1) por indexación directa. Mismo ahorro de RAM que CompactPostings.

---

## Cálculo de relevancia

### CoreEngine — TF-IDF + Similitud Coseno

El `CoreEngine` implementa el modelo clásico TF-IDF con similitud coseno:

**1. Term Frequency (TF)** — peso local del término en el documento:

$$TF(t, d) = \frac{f(t, d)}{|d|}$$

Donde $f(t, d)$ es la cantidad de veces que el término $t$ aparece en el documento $d$, y $|d|$ es la longitud total del documento.

**2. Inverse Document Frequency (IDF)** — peso global del término:

$$IDF(t) = \log\left(\frac{N + 1}{df(t) + 1}\right) + 1$$

Donde $N$ es el total de documentos y $df(t)$ es la cantidad de documentos que contienen $t$. El suavizado (+1) evita la división por cero.

**3. TF-IDF**:

$$TF\text{-}IDF(t, d) = TF(t, d) \times IDF(t)$$

**4. Similitud Coseno**:

$$\text{sim}(q, d) = \frac{\vec{q} \cdot \vec{d}}{|\vec{q}| \times |\vec{d}|}$$

El CoreEngine pre-calcula las normas de documento (`doc_norms`) durante la indexación, así la búsqueda solo necesita:
1. Tokenizar la query.
2. Calcular el vector TF-IDF de la query (sparse — solo los términos presentes).
3. Calcular el producto punto con cada documento candidato.
4. Dividir por las normas pre-calculadas.

### LiteEngine — TF Normalizado

El `LiteEngine` usa un scoring más simple y rápido:

$$\text{score}(q, d) = \sum_{t \in q} \frac{f(t, d)}{|d|}$$

No calcula IDF ni normas de documento. Esto lo hace más rápido pero menos preciso para consultas con términos raros.

---

## Formato binario .lcs

Para persistencia ultra-eficiente, Lucis puede guardar shards en formato binario `.lcs` (Lucis Compact Storage) que se carga vía memory-mapped I/O:

```
┌────────────────────────────────────┐
│ Header: magic + version + offsets  │
├────────────────────────────────────┤
│ Vocabulary: tokens (UTF-8)         │
├────────────────────────────────────┤
│ Posting data: doc_ids + freqs      │
│ (arrays de enteros compactados)    │
├────────────────────────────────────┤
│ Doc lengths array                  │
├────────────────────────────────────┤
│ ID map (original → internal)       │
└────────────────────────────────────┘
```

**Ventajas de mmap:**

- **Carga casi instantánea**: El OS mapea el archivo sin copiarlo a RAM.
- **RAM bajo demanda**: Solo las páginas accedidas se cargan en memoria física.
- **Compartido entre procesos**: Múltiples workers pueden leer el mismo `.lcs`.

Los archivos `.lcs` se generan automáticamente cuando guardas un índice con `generate_lcs()` o durante la indexación con storage binario.

---

## Shadow indexing — Reindexación sin downtime

Cuando llamas a `reindex()`, Lucis no destruye el índice activo. En su lugar:

1. **Crea una nueva versión** con un nombre físico versionado (ej. `mi_idx__v20240315_120000`).
2. **Construye el índice** en segundo plano sobre la nueva versión.
3. **Swapea el alias** — el nombre lógico (`mi_idx`) apunta a la nueva versión.
4. **Las búsquedas nunca se interrumpen** — durante el rebuild usaban la versión anterior.

Esto es el mecanismo que subyace tanto a `reindex()` como al `IndexWorker`.

---

## Paralelismo

Lucis usa `concurrent.futures.ThreadPoolExecutor` para paralelizar operaciones costosas:

- **Búsqueda multi-shard**: Cada shard se busca en un thread independiente, los resultados se fusionan y re-rankean.
- **Persistencia**: Los shards se guardan en paralelo.

El número de workers se configura automáticamente según los cores disponibles.

---

## Siguiente paso

- [Modelos de datos](modelos-datos.md) — SearchResult, SearchResponse
- [Referencia API](api-referencia.md) — Todas las firmas y parámetros
