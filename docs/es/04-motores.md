# Motores de búsqueda

Lucis incluye dos motores de búsqueda con diferentes perfiles de rendimiento. Ambos funcionan en Python puro, sin dependencias externas.

---

## CoreEngine — El corazón de Lucis

`CoreEngine` es el motor principal. Implementa **TF-IDF completo con similitud coseno**, lo que lo hace ideal cuando la precisión de los resultados es lo más importante.

```python
from lucis import Lucis

buscador = Lucis.from_dict(datos, name="preciso", engine="core")
```

### ¿Cómo funciona?

1. **Indexación**: Construye un índice invertido compacto y pre-calcula las normas L2 de cada documento.
2. **Búsqueda**: Construye un vector de query TF-IDF on-the-fly, encuentra documentos candidatos y calcula la similitud coseno.

### Tokenizer por defecto

`WordTokenizer` — Extrae solo palabras (ignora números, convierte a minúsculas).

```python
from lucis.utils.nlp import WordTokenizer

WordTokenizer()("Python 3.11 es increíble!")
# → ["python", "es", "increíble"]
```

### Cuándo usar CoreEngine

- Búsquedas donde la **relevancia precisa** importa
- Corpus pequeños a medianos
- Cuando no necesitas indexación incremental

> **📐 Nota Matemática — TF-IDF y Similitud Coseno**
>
> **Term Frequency normalizado:**
> ```
> tf(t, d) = count(t, d) / |d|
> ```
> Donde `count(t,d)` es cuántas veces aparece el término `t` en el documento `d`, y `|d|` es el total de tokens del documento.
>
> **Inverse Document Frequency (smoothed):**
> ```
> idf(t) = log((N + 1) / (df(t) + 1)) + 1
> ```
> Donde `N` es el total de documentos y `df(t)` es el número de documentos que contienen `t`.
>
> **TF-IDF:**
> ```
> tfidf(t, d) = tf(t, d) × idf(t)
> ```
>
> **Similitud Coseno:**
> ```
> cos(A, B) = (A · B) / (||A|| × ||B||)
> ```
> El score final es el coseno del ángulo entre el vector de query y el vector de cada documento. 1.0 = idénticos, 0.0 = sin relación.

---

## LiteEngine — Ligero y rápido

`LiteEngine` es un motor minimalista que usa solo **Term Frequency normalizado**. Sin IDF, sin similitud coseno. Esto lo hace significativamente más ligero en RAM y disco.

```python
from lucis import Lucis

buscador = Lucis.from_dict(datos, name="rapido", engine="lite")
```

### ¿Cómo funciona?

La puntuación de cada documento es simplemente:

```
score(d, Q) = Σ tf(t, d) / |d|   para cada término t en la query Q
```

No hay vectores, no hay IDF. Solo cuenta cuántas veces aparecen los términos de la query en cada documento, normalizado por la longitud del documento.

### Tokenizer por defecto

`CharNgramTokenizer(3)` con lowercase — Genera trigramas de caracteres, ideal para búsqueda fuzzy.

```python
from lucis.utils.nlp import CharNgramTokenizer

tokenizer = CharNgramTokenizer(3)
tokenizer("python")
# → ["pyt", "yth", "tho", "hon"]
```

Esto significa que LiteEngine funciona bien con errores tipográficos y coincidencias parciales.

### Cuándo usar LiteEngine

- **Gran volumen** de documentos donde la velocidad importa más que la precisión perfecta
- **RAM limitada** — usa significativamente menos memoria
- **Búsqueda fuzzy** — el tokenizer de char n-grams tolera typos
- **Indexación incremental** — soporta `add_documents()` y `remove_documents()`

> **📐 Nota Matemática — TF normalizado**
>
> ```
> score(d, Q) = Σ  tf(t, d) / |d|
> ```
>
> Donde:
> - `tf(t, d)` = conteo raw del término `t` en el documento `d`
> - `|d|` = total de tokens en el documento `d`
> - La suma es sobre todos los términos `t` que aparecen tanto en la query `Q` como en el documento `d`

---

## Tabla comparativa

| Característica | CoreEngine | LiteEngine |
|---|---|---|
| **Algoritmo** | TF-IDF + Similitud Coseno | TF normalizado |
| **Precisión** | ⭐⭐⭐ Alta | ⭐⭐ Buena |
| **Uso de RAM** | Moderado | Bajo |
| **Velocidad** | Rápida | Muy rápida |
| **Dependencias** | Ninguna | Ninguna |
| **Tokenizador default** | `WordTokenizer` | `CharNgramTokenizer(3)` |
| **`add_documents()`** | No | Sí |
| **`remove_documents()`** | No | Sí |
| **Mejor para** | Precisión | Volumen + Fuzzy |

---

## Uso standalone del engine

Los motores son componentes independientes. Puedes importarlos y usarlos directamente sin la clase `Lucis`, si solo necesitas las primitivas de búsqueda:

```python
from lucis.engines import CoreEngine

# Crear engine directamente
engine = CoreEngine()

# Indexar
engine.build_index({
    "doc1": "Python es versátil",
    "doc2": "JavaScript domina el frontend",
    "doc3": "Python y JS son populares"
})

# Buscar (retorna lista de tuplas)
resultados = engine.search("python frontend", top_k=2)
for doc_id, score in resultados:
    print(f"  {doc_id}: {score:.4f}")
```

```python
from lucis.engines import LiteEngine

engine = LiteEngine()
engine.build_index(["documento uno", "documento dos", "documento tres"])

resultados = engine.search("uno tres", top_k=2)
for doc_id, score in resultados:
    print(f"  {doc_id}: {score:.4f}")
```

Esto es útil cuando quieres integrar solo la lógica de búsqueda en tu propia aplicación, sin persistencia ni orquestación.

---

<!-- 
## 🔮 Próximamente — Motores optimizados (Plus)

En futuras versiones, Lucis incluirá motores optimizados que aprovecharán
NumPy para operaciones vectorizadas SIMD y Polars para procesamiento 
paralelo de grandes corpus:

- **NumpyEngine**: batch_cosine_similarity, TF-IDF matricial
- **PolarsEngine**: build_index paralelo para corpus masivos

Instalar con: `pip install lucis[plus]`
-->

## Siguiente paso

- [Preprocesadores](05-preprocesadores.md) — Personalizar tokenización y limpieza de texto
- [Funciones útiles](07-funciones-utiles.md) — Usar las primitivas de búsqueda como toolkit standalone
