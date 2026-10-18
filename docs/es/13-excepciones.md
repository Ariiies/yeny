# Excepciones

Yeny define una jerarquía de excepciones para manejar errores de forma granular. Todas heredan de `YenyError`.

---

## Jerarquía

```
YenyError (base)
├── YenyEmptyCorpusError      — Corpus vacío
├── YenyInvalidDocumentError  — Documento inválido
├── YenyEngineError           — Error del motor
├── YenySearchError           — Error en búsqueda
└── YenyTokenizationError     — Error en tokenización
```

---

## Importación

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

## Descripción de cada excepción

### `YenyError`

Excepción base. Atrápala para capturar cualquier error de Yeny:

```python
try:
    resultado = yn.search("algo")
except YenyError as e:
    print(f"Error de Yeny: {e}")
```

### `YenyEmptyCorpusError`

Se lanza cuando intentas indexar un corpus vacío o sin documentos válidos.

```python
try:
    yn.index({})
except YenyEmptyCorpusError:
    print("No hay documentos que indexar")
```

Mensaje por defecto: `"The corpus is empty or contains no valid documents"`.

### `YenyInvalidDocumentError`

Se lanza cuando un documento tiene tipo incorrecto u otro problema de formato.

```python
try:
    yn.index({1: 123})  # valor no es string
except YenyInvalidDocumentError as e:
    print(e)             # "Invalid document at index 0: ..."
    print(e.doc_index)   # 0
```

Atributos:
- `doc_index` (`int | None`): Índice del documento problemático.

### `YenyEngineError`

Se lanza cuando hay un error interno del motor de cálculo.

```python
try:
    yn.search("algo")
except YenyEngineError as e:
    print(e)              # "Error in engine 'CoreEngine': ..."
    print(e.engine_name)  # "CoreEngine"
```

Atributos:
- `engine_name` (`str`): Nombre del motor que falló.

### `YenySearchError`

Se lanza cuando hay un error durante la búsqueda.

```python
try:
    yn.search("algo")
except YenySearchError as e:
    print(e)        # "Error during search for query 'algo': ..."
    print(e.query)  # "algo"
```

Atributos:
- `query` (`str`): La query que causó el error.

### `YenyTokenizationError`

Se lanza cuando hay un error durante la tokenización.

```python
try:
    yn.index(datos)
except YenyTokenizationError:
    print("Error procesando texto")
```

---

## Patrón recomendado

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

## Siguiente paso

- [Recetas prácticas](14-recetas.md) — Ejemplos completos de extremo a extremo
- [Referencia API](15-api-referencia.md) — Todas las firmas
