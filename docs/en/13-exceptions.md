# Exceptions

Yeny defines a hierarchy of exceptions to handle errors on a granular basis. They all inherit from `YenyError`.

---

##Hierarchy

```
YenyError (base)
├── YenyEmptyCorpusError      — Corpus vacío
├── YenyInvalidDocumentError  — Documento inválido
├── YenyEngineError           — Error del motor
├── YenySearchError           — Error en búsqueda
└── YenyTokenizationError     — Error en tokenización
```

---

## Import

```python
from yeny.exceptions import (
    YenyError,
    YenyEmptyCorpusError,
    YenyInvalidDocumentError,
    YenyEngineError,
    YenySearchError,
    YenyTokenizationError,
)
```

---

## Description of each exception

### `YenyError`

Base exception. Catch her to capture any Yeny mistakes:

```python
try:
    resultado = yn.search("algo")
except YenyError as e:
    print(f"Error de Yeny: {e}")
```

### `YenyEmptyCorpusError`

Launched when you try to index an empty corpus or one without valid documents.

```python
try:
    yn.index({})
except YenyEmptyCorpusError:
    print("No hay documentos que indexar")
```

Default message: `"The corpus is empty or contains no valid documents"`.

### `YenyInvalidDocumentError`

Launched when a document has the wrong type or other formatting problem.

```python
try:
    yn.index({1: 123})  # valor no es string
except YenyInvalidDocumentError as e:
    print(e)             # "Invalid document at index 0: ..."
    print(e.doc_index)   # 0
```

Attributes:
- `doc_index` (`int | None`): Index of the problematic document.

### `YenyEngineError`

It is launched when there is an internal error in the calculation engine.

```python
try:
    yn.search("algo")
except YenyEngineError as e:
    print(e)              # "Error in engine 'CoreEngine': ..."
    print(e.engine_name)  # "CoreEngine"
```

Attributes:
- `engine_name` (`str`): Name of the engine that failed.

### `YenySearchError`

It is thrown when there is an error during the search.

```python
try:
    yn.search("algo")
except YenySearchError as e:
    print(e)        # "Error during search for query 'algo': ..."
    print(e.query)  # "algo"
```

Attributes:
- `query` (`str`): The query that caused the error.

### `YenyTokenizationError`

Thrown when there is an error during tokenization.

```python
try:
    yn.index(datos)
except YenyTokenizationError:
    print("Error procesando texto")
```

---

## Recommended pattern

```python
from yeny.exceptions import YenyEmptyCorpusError, YenySearchError, YenyError

try:
    yn.index(mis_datos)
    resultados = yn.search("mi consulta")
except YenyEmptyCorpusError:
    # Manejar caso de corpus vacío
    print("Sin datos para indexar")
except YenySearchError as e:
    # Manejar error de búsqueda específicamente
    print(f"Fallo en búsqueda: {e}")
except YenyError as e:
    # Catch-all para otros errores de Yeny
    print(f"Error inesperado: {e}")
```

---

## Next step

- [Practical Recipes](14-recipes.md) — Complete end-to-end examples
- [API Reference](15-api-reference.md) — All signatures