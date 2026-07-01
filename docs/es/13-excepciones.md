# Excepciones

Lucis define una jerarquía de excepciones para manejar errores de forma granular. Todas heredan de `LucisError`.

---

## Jerarquía

```
LucisError (base)
├── LucisEmptyCorpusError      — Corpus vacío
├── LucisInvalidDocumentError  — Documento inválido
├── LucisEngineError           — Error del motor
├── LucisSearchError           — Error en búsqueda
└── LucisTokenizationError     — Error en tokenización
```

---

## Importación

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

## Descripción de cada excepción

### `LucisError`

Excepción base. Atrápala para capturar cualquier error de Lucis:

```python
try:
    resultado = luc.search("algo")
except LucisError as e:
    print(f"Error de Lucis: {e}")
```

### `LucisEmptyCorpusError`

Se lanza cuando intentas indexar un corpus vacío o sin documentos válidos.

```python
try:
    luc.index({})
except LucisEmptyCorpusError:
    print("No hay documentos que indexar")
```

Mensaje por defecto: `"The corpus is empty or contains no valid documents"`.

### `LucisInvalidDocumentError`

Se lanza cuando un documento tiene tipo incorrecto u otro problema de formato.

```python
try:
    luc.index({1: 123})  # valor no es string
except LucisInvalidDocumentError as e:
    print(e)             # "Invalid document at index 0: ..."
    print(e.doc_index)   # 0
```

Atributos:
- `doc_index` (`int | None`): Índice del documento problemático.

### `LucisEngineError`

Se lanza cuando hay un error interno del motor de cálculo.

```python
try:
    luc.search("algo")
except LucisEngineError as e:
    print(e)              # "Error in engine 'CoreEngine': ..."
    print(e.engine_name)  # "CoreEngine"
```

Atributos:
- `engine_name` (`str`): Nombre del motor que falló.

### `LucisSearchError`

Se lanza cuando hay un error durante la búsqueda.

```python
try:
    luc.search("algo")
except LucisSearchError as e:
    print(e)        # "Error during search for query 'algo': ..."
    print(e.query)  # "algo"
```

Atributos:
- `query` (`str`): La query que causó el error.

### `LucisTokenizationError`

Se lanza cuando hay un error durante la tokenización.

```python
try:
    luc.index(datos)
except LucisTokenizationError:
    print("Error procesando texto")
```

---

## Patrón recomendado

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

## Siguiente paso

- [Recetas prácticas](recetas.md) — Ejemplos completos de extremo a extremo
- [Referencia API](api-referencia.md) — Todas las firmas
