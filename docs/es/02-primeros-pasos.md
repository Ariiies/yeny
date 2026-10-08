# Primeros pasos

Esta guía te llevará de cero a tu primer buscador funcional en minutos.

---

## Tu primer buscador en 5 líneas

```python
from lucis import Lucis

datos = {
    "doc1": "Python es un lenguaje versátil para desarrollo web",
    "doc2": "JavaScript domina el frontend moderno",
    "doc3": "Python y JavaScript son los lenguajes más populares"
}

buscador = Lucis.from_dict(datos, name="mi_buscador")
resultados = buscador.search("python web")
print(resultados)
```

Eso es todo. Lucis se encarga de tokenizar el texto, construir el índice invertido, calcular los vectores TF-IDF y encontrar los documentos más relevantes.

---

## Trabajando con listas

Si no tienes IDs específicos, puedes usar una lista. Lucis asigna IDs secuenciales automáticamente (0, 1, 2...):

```python
from lucis import Lucis

articulos = [
    "Cómo aprender machine learning desde cero",
    "Guía completa de desarrollo web con Django",
    "Introducción a las redes neuronales",
    "REST APIs con FastAPI y Python"
]

buscador = Lucis.from_list(articulos, name="articulos")
resultados = buscador.search("machine learning python")

for r in resultados.results:
    print(f"  Doc {r.doc_id}: score={r.score}")
```

---

## Entendiendo los resultados

Cada búsqueda devuelve un `SearchResponse`, un objeto estructurado con toda la información:

```python
resultados = buscador.search("python desarrollo", top_k=3)

# Metadatos de la búsqueda
print(resultados.query)            # "python desarrollo"
print(resultados.tokens)           # ["python", "desarrollo"]
print(resultados.engine)           # "CoreEngine"
print(resultados.total_results)    # 3
print(resultados.search_time_ms)   # 0.08

# Resultados individuales
for r in resultados.results:
    print(f"  #{r.rank} — doc_id={r.doc_id}, score={r.score}")

# Exportar como diccionario (JSON-ready)
print(resultados.to_dict())
```

El `SearchResult` contiene:
- **`doc_id`**: El identificador original del documento (la key del dict, o el índice de la lista).
- **`score`**: Puntuación de relevancia (0.0 a 1.0, basada en similitud coseno).
- **`rank`**: Posición en los resultados (1 = más relevante).

---

## Guardando y cargando índices

Lucis persiste automáticamente los índices. Puedes guardar y recargar sin reconstruir:

```python
# Crear y guardar
buscador = Lucis.from_dict(datos, name="mi_indice")
buscador.save()

# ... más tarde, en otro script ...
buscador = Lucis(name="mi_indice")  # Carga automáticamente
resultados = buscador.search("mi consulta")
```

Por defecto, los índices se guardan en la carpeta `lucis_data/` como archivos JSON. Consulta [Almacenamiento](06-almacenamiento.md) para conocer otras opciones (SQLite, MySQL, PostgreSQL).

---

## Eligiendo un motor

Lucis incluye dos motores de búsqueda con diferentes perfiles:

| Característica | `CoreEngine` | `LiteEngine` |
|---|---|---|
| **Algoritmo** | TF-IDF + Similitud Coseno | TF normalizado |
| **Precisión** | Alta | Buena |
| **RAM** | Moderada | Baja |
| **Velocidad** | Rápida | Muy rápida |
| **Dependencias** | Ninguna | Ninguna |
| **Tokenizador default** | `WordTokenizer` | `CharNgramTokenizer(3)` |
| **Mejor para** | Búsqueda precisa | Alto volumen, búsqueda fuzzy |
| **Indexación incremental** | No | Sí |

```python
# CoreEngine (default) — mejor precisión
buscador_core = Lucis.from_dict(datos, name="preciso", engine="core")

# LiteEngine — más ligero, búsqueda fuzzy por defecto
buscador_lite = Lucis.from_dict(datos, name="rapido", engine="lite")
```

Consulta [Motores de búsqueda](04-motores.md) para detalles completos.

---

## Preprocessor personalizado

Lucis permite inyectar tu propio preprocesador de texto. Esto te da control total sobre cómo se tokeniza el texto:

```python
from lucis import Lucis
from lucis.utils.nlp import WordTokenizer, remove_punctuation, remove_accents

# Pipeline personalizado
def mi_preprocesador(texto):
    texto = remove_accents(texto)
    texto = remove_punctuation(texto)
    return WordTokenizer()(texto)

buscador = Lucis.from_dict(datos, name="custom", preprocessor=mi_preprocesador)
```

El preprocesador puede devolver:
- **`list[str]`** — Los tokens se usan directamente.
- **`str`** — Lucis aplica un tokenizador básico como paso final.

El mismo preprocesador se usa tanto para indexación como para búsqueda, garantizando consistencia en el espacio vectorial.

Consulta [Preprocesadores](05-preprocesadores.md) para más detalles y ejemplos.

---

## Siguiente paso

Ahora que sabes lo básico, explora:

- [La clase Lucis](03-objeto-lucis.md) — Todos los métodos y opciones
- [Motores de búsqueda](04-motores.md) — CoreEngine vs LiteEngine en profundidad
- [Recetas](14-recetas.md) — Ejemplos prácticos completos
