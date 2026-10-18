# Preprocesadores y NLP

Yeny incluye un sistema de preprocesamiento de texto completamente personalizable. El preprocesador controla cómo se transforma el texto antes de indexarlo y buscarlo.

---

## El sistema de preprocesador

Cada instancia de `Yeny` (o cada engine) tiene un preprocesador que se aplica **tanto a la indexación como a la búsqueda**, garantizando que ambos operan en el mismo espacio vectorial.

```python
from yeny import Yeny

def mi_preprocesador(texto: str) -> list[str]:
    """Mi pipeline personalizado."""
    return texto.lower().split()

buscador = Yeny.from_dict(datos, name="custom", preprocessor=mi_preprocesador)
```

### Reglas del preprocesador

Un preprocesador es cualquier callable con firma `(str) → str | list[str]`:

- Si retorna **`list[str]`**: Los tokens se usan directamente.
- Si retorna **`str`**: Yeny aplica `SimpleTokenizer` (split por espacios) como paso final.

```python
# Opción 1: retornar tokens directamente
def prep_tokens(texto):
    return texto.lower().split()

# Opción 2: retornar string preprocesado (Yeny tokeniza al final)
def prep_texto(texto):
    return texto.lower().strip()
```

---

## Tokenizadores incluidos

Yeny incluye cuatro clases tokenizadoras en `yeny.utils.nlp`:

### `SimpleTokenizer()`

Divide por espacios. El más básico.

```python
from yeny.utils.nlp import SimpleTokenizer

SimpleTokenizer()("Hola mundo cruel")
# → ["Hola", "mundo", "cruel"]
```

### `WordTokenizer()`

Extrae solo palabras (regex), ignora números, convierte a minúsculas. Soporta caracteres españoles (áéíóúüñ).

```python
from yeny.utils.nlp import WordTokenizer

WordTokenizer()("Python 3.11 es increíble para IA!")
# → ["python", "es", "increíble", "para", "ia"]
```

Este es el tokenizador por defecto de `CoreEngine`.

### `NgramTokenizer(n)`

Clase invocable que crea un tokenizador de n-gramas de **palabras**:

```python
from yeny.utils.nlp import NgramTokenizer

bigram = NgramTokenizer(2)
bigram("hola mundo cruel")
# → ["hola mundo", "mundo cruel"]

trigram = NgramTokenizer(3)
trigram("uno dos tres cuatro")
# → ["uno dos tres", "dos tres cuatro"]
```

### `CharNgramTokenizer(n)`

Clase invocable que crea un tokenizador de n-gramas de **caracteres**. Ideal para búsqueda fuzzy y tolerancia a errores tipográficos:

```python
from yeny.utils.nlp import CharNgramTokenizer

trigram = CharNgramTokenizer(3)
trigram("python")
# → ["pyt", "yth", "tho", "hon"]

trigram("pythn")  # con typo
# → ["pyt", "yth", "thn"]
# Aún comparte "pyt" y "yth" con "python" → match parcial
```

El texto se convierte a minúsculas carácter a carácter (los espacios se conservan).

Este es el tokenizador por defecto de `LiteEngine`.

---

## Limpiadores de texto

Yeny incluye funciones de limpieza de texto en `yeny.utils.nlp` que puedes combinar en tu preprocesador:

### `lowercase(text)` / `uppercase(text)`

```python
from yeny.utils.nlp import lowercase, uppercase

lowercase("Hola Mundo")  # → "hola mundo"
uppercase("Hola Mundo")  # → "HOLA MUNDO"
```

### `strip_whitespace(text)`

Elimina espacios al inicio/final y normaliza espacios múltiples:

```python
from yeny.utils.nlp import strip_whitespace

strip_whitespace("  hola   mundo  ")  # → "hola mundo"
```

### `remove_punctuation(text, keep="")`

Elimina signos de puntuación (incluyendo `¡¿` del español):

```python
from yeny.utils.nlp import remove_punctuation

remove_punctuation("¡Hola, mundo! ¿Cómo estás?")
# → "Hola mundo Cómo estás"

remove_punctuation("precio: $100.50", keep=".$")
# → "precio $100.50"
```

### `remove_numbers(text)`

```python
from yeny.utils.nlp import remove_numbers

remove_numbers("Python 3.11 lanzado en 2022")
# → "Python . lanzado en "
```

### `remove_extra_spaces(text)`

```python
from yeny.utils.nlp import remove_extra_spaces

remove_extra_spaces("hola    mundo   cruel")
# → "hola mundo cruel"
```

### `remove_urls(text)`

```python
from yeny.utils.nlp import remove_urls

remove_urls("Visita https://yeny.dev para más info")
# → "Visita  para más info"
```

### `remove_emails(text)`

```python
from yeny.utils.nlp import remove_emails

remove_emails("Contacto: user@empresa.com para info")
# → "Contacto:  para info"
```

### `remove_html_tags(text)`

```python
from yeny.utils.nlp import remove_html_tags

remove_html_tags("<p>Hola <b>mundo</b></p>")
# → "Hola mundo"
```

### `normalize_unicode(text)` / `remove_accents(text)`

Elimina acentos y caracteres diacríticos. Útil para búsquedas donde los acentos no importan.

```python
from yeny.utils.nlp import remove_accents

remove_accents("café résumé naïve")
# → "cafe resume naive"
```

---

## Creando tu propio preprocesador

### Pipeline simple

Encadena funciones para crear tu pipeline:

```python
from yeny import Yeny
from yeny.utils.nlp import (
    WordTokenizer,
    remove_accents,
    remove_punctuation,
    remove_html_tags,
)

def preprocesador_blog(texto):
    """Pipeline para artículos de blog con HTML."""
    texto = remove_html_tags(texto)
    texto = remove_accents(texto)
    texto = remove_punctuation(texto)
    return WordTokenizer()(texto)

buscador = Yeny.from_dict(articulos, name="blog", preprocessor=preprocesador_blog)
```

### Pipeline con limpieza agresiva

```python
from yeny.utils.nlp import (
    WordTokenizer,
    remove_accents,
    remove_punctuation,
    remove_urls,
    remove_emails,
    remove_numbers,
    strip_whitespace,
)

def preprocesador_emails(texto):
    """Pipeline agresivo para corpus de emails."""
    texto = remove_urls(texto)
    texto = remove_emails(texto)
    texto = remove_html_tags(texto)
    texto = remove_numbers(texto)
    texto = remove_accents(texto)
    texto = remove_punctuation(texto)
    texto = strip_whitespace(texto)
    return WordTokenizer()(texto)

buscador = Yeny.from_dict(emails, name="email_search", preprocessor=preprocesador_emails)
```

### Preprocesador que retorna string

Si tu preprocesador retorna `str` en lugar de `list[str]`, Yeny aplica `SimpleTokenizer` automáticamente:

```python
def solo_limpiar(texto):
    """Solo limpia, no tokeniza. Yeny tokenizará con SimpleTokenizer."""
    return texto.lower().strip()

buscador = Yeny.from_dict(datos, name="limpio", preprocessor=solo_limpiar)
```

---

## Integración con librerías externas

Puedes usar cualquier librería NLP como preprocesador de Yeny:

### Ejemplo con NLTK

```python
import nltk
from nltk.stem import SnowballStemmer

stemmer = SnowballStemmer("spanish")

def preprocesador_nltk(texto):
    tokens = nltk.word_tokenize(texto.lower(), language="spanish")
    return [stemmer.stem(t) for t in tokens if t.isalpha()]

buscador = Yeny.from_dict(datos, name="stemmed", preprocessor=preprocesador_nltk)
```

### Ejemplo con spaCy

```python
import spacy
nlp = spacy.load("es_core_news_sm")

def preprocesador_spacy(texto):
    doc = nlp(texto)
    return [token.lemma_.lower() for token in doc if not token.is_stop and token.is_alpha]

buscador = Yeny.from_dict(datos, name="lemmatized", preprocessor=preprocesador_spacy)
```

---

## Siguiente paso

- [Almacenamiento](06-almacenamiento.md) — Backends de persistencia
- [Funciones útiles](07-funciones-utiles.md) — Toolkit modular standalone
