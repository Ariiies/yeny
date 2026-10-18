# Getting started

This guide will take you from zero to your first functional search engine in minutes.

---

## Your first search engine in 5 lines

```python
from yeny import Yeny

datos = {
    "doc1": "Python es un lenguaje versátil para desarrollo web",
    "doc2": "JavaScript domina el frontend moderno",
    "doc3": "Python y JavaScript son los lenguajes más populares"
}

buscador = Yeny.from_dict(datos, name="mi_buscador")
resultados = buscador.search("python web")
print(resultados)
```

That's all. Yeny is responsible for tokenizing the text, building the inverted index, calculating the TF-IDF vectors and finding the most relevant documents.

---

## Working with lists

If you don't have specific IDs, you can use a list. Yeny assigns sequential IDs automatically (0, 1, 2...):

```python
from yeny import Yeny

articulos = [
    "Cómo aprender machine learning desde cero",
    "Guía completa de desarrollo web con Django",
    "Introducción a las redes neuronales",
    "REST APIs con FastAPI y Python"
]

buscador = Yeny.from_list(articulos, name="articulos")
resultados = buscador.search("machine learning python")

for r in resultados.results:
    print(f"  Doc {r.doc_id}: score={r.score}")
```

---

## Understanding the results

Each search returns a `SearchResponse`, a structured object with all the information:

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

The `SearchResult` contains:
- **`doc_id`**: The original identifier of the document (the key of the dict, or the index of the list).
- **`score`**: Relevance score (0.0 to 1.0, based on cosine similarity).
- **`rank`**: Position in the results (1 = most relevant).

---

## Saving and loading indexes

Yeny automatically persists indexes. You can save and reload without rebuilding:

```python
# Crear y guardar
buscador = Yeny.from_dict(datos, name="mi_indice")
buscador.save()

# ... más tarde, en otro script ...
buscador = Yeny(name="mi_indice")  # Carga automáticamente
resultados = buscador.search("mi consulta")
```

By default, indexes are saved in the `yeny_data/` folder as JSON files. See [Storage](06-storage.md) for other options (SQLite, MySQL, PostgreSQL).

---

## Choosing an engine

Yeny includes two search engines with different profiles:

| Feature | `CoreEngine` | `LiteEngine` |
|---|---|---|
| **Algorithm** | TF-IDF + Cosine Similarity | Normalized TF |
| **Precision** | High | Good |
| **RAM** | Moderate | Low |
| **Speed** | Quick | Very fast |
| **Dependencies** | None | None |
| **Default tokenizer** | `WordTokenizer` | `CharNgramTokenizer(3)` |
| **Best for** | Precise search | High volume, fuzzy search |
| **Incremental indexing** | No | Yes |

```python
# CoreEngine (default) — mejor precisión
buscador_core = Yeny.from_dict(datos, name="preciso", engine="core")

# LiteEngine — más ligero, búsqueda fuzzy por defecto
buscador_lite = Yeny.from_dict(datos, name="rapido", engine="lite")
```

See [Search Engines](04-engines.md) for complete details.

---

## Custom preprocessor

Yeny allows you to inject your own text preprocessor. This gives you full control over how the text is tokenized:

```python
from yeny import Yeny
from yeny.utils.nlp import WordTokenizer, remove_punctuation, remove_accents

# Pipeline personalizado
def mi_preprocesador(texto):
    texto = remove_accents(texto)
    texto = remove_punctuation(texto)
    return WordTokenizer()(texto)

buscador = Yeny.from_dict(datos, name="custom", preprocessor=mi_preprocesador)
```

The preprocessor can return:
- **`list[str]`** — Tokens are used directly.
- **`str`** — Yeny applies a basic tokenizer as a final step.

The same preprocessor is used for both indexing and searching, ensuring consistency in the vector space.

See [Preprocessors](05-preprocessors.md) for more details and examples.

---

## Next step

Now that you know the basics, explore:

- [The Yeny class](03-yeny-object.md) — All methods and options
- [Search Engines](04-engines.md) — CoreEngine vs LiteEngine in depth
- [Recipes](14-recipes.md) — Complete practical examples