# Exceptions

Lucis defines a hierarchy of exceptions to handle errors on a granular basis. They all inherit from `LucisError`.

---

##Hierarchy

```
LucisError (base)
├── LucisEmptyCorpusError      — Corpus vacío
├── LucisInvalidDocumentError  — Documento inválido
├── LucisEngineError           — Error del motor
├── LucisSearchError           — Error en búsqueda
└── LucisTokenizationError     — Error en tokenización
```

---

## Import

```python
from lucis.exceptions import (
    LucisError,
    LucisEmptyCorpusError,
    LucisInvalidDocumentError,
    LucisEngineError,
    LucisSearchError,
    LucisTokenizationError,
)
```

---

## Description of each exception

### `LucisError`

Base exception. Catch her to capture any Lucis mistakes:

```python
try:
    resultado = luc.search("algo")
except LucisError as e:
    print(f"Error de Lucis: {e}")
```

### `LucisEmptyCorpusError`

Launched when you try to index an empty corpus or one without valid documents.

```python
try:
    luc.index({})
except LucisEmptyCorpusError:
    print("No hay documentos que indexar")
```

Default message: `"The corpus is empty or contains no valid documents"`.

### `LucisInvalidDocumentError`

Launched when a document has the wrong type or other formatting problem.

```python
try:
    luc.index({1: 123})  # valor no es string
except LucisInvalidDocumentError as e:
    print(e)             # "Invalid document at index 0: ..."
    print(e.doc_index)   # 0
```

Attributes:
- `doc_index` (`int | None`): Index of the problematic document.

### `LucisEngineError`

It is launched when there is an internal error in the calculation engine.

```python
try:
    luc.search("algo")
except LucisEngineError as e:
    print(e)              # "Error in engine 'CoreEngine': ..."
    print(e.engine_name)  # "CoreEngine"
```

Attributes:
- `engine_name` (`str`): Name of the engine that failed.

### `LucisSearchError`

It is thrown when there is an error during the search.

```python
try:
    luc.search("algo")
except LucisSearchError as e:
    print(e)        # "Error during search for query 'algo': ..."
    print(e.query)  # "algo"
```

Attributes:
- `query` (`str`): The query that caused the error.

### `LucisTokenizationError`

Thrown when there is an error during tokenization.

```python
try:
    luc.index(datos)
except LucisTokenizationError:
    print("Error procesando texto")
```

---

## Recommended pattern

```python
from lucis.exceptions import LucisEmptyCorpusError, LucisSearchError, LucisError

try:
    luc.index(mis_datos)
    resultados = luc.search("mi consulta")
except LucisEmptyCorpusError:
    # Manejar caso de corpus vacío
    print("Sin datos para indexar")
except LucisSearchError as e:
    # Manejar error de búsqueda específicamente
    print(f"Fallo en búsqueda: {e}")
except LucisError as e:
    # Catch-all para otros errores de Lucis
    print(f"Error inesperado: {e}")
```

---

## Next step

- [Practical Recipes](14-recipes.md) — Complete end-to-end examples
- [API Reference](15-api-reference.md) — All signatures