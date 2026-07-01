# Preprocessors and NLP

Lucis includes a fully customizable text preprocessing system. The preprocessor controls how the text is transformed before it is indexed and searched.

---

## The preprocessor system

Each instance of `Lucis` (or each engine) has a preprocessor that applies **to both indexing and searching**, ensuring that both operate in the same vector space.

```python
from lucis import Lucis

def mi_preprocesador(texto: str) -> list[str]:
    """Mi pipeline personalizado."""
    return texto.lower().split()

buscador = Lucis.from_dict(datos, name="custom", preprocessor=mi_preprocesador)
```

### Preprocessor rules

A preprocessor is any callable with signature `(str) → str | list[str]`:

- If **`list[str]`** returns: The tokens are used directly.
- If **`str`** returns: Lucis applies `simple_tokenizer` (split by spaces) as a final step.

```python
# Opción 1: retornar tokens directamente
def prep_tokens(texto):
    return texto.lower().split()

# Opción 2: retornar string preprocesado (Lucis tokeniza al final)
def prep_texto(texto):
    return texto.lower().strip()
```

---

## Tokenizers included

Lucis includes four tokenizers in `lucis.utils.nlp`:

### `simple_tokenizer(text)`

Divide by spaces. The most basic.

```python
from lucis.utils.nlp import simple_tokenizer

simple_tokenizer("Hola mundo cruel")
# → ["Hola", "mundo", "cruel"]
```

### `word_tokenizer(text)`

Extracts only words (regex), ignores numbers, converts to lowercase. Supports Spanish characters (áéíóúüñ).

```python
from lucis.utils.nlp import word_tokenizer

word_tokenizer("Python 3.11 es increíble para IA!")
# → ["python", "es", "increíble", "para"]
```

This is the default tokenizer for `CoreEngine`.

### `ngram_tokenizer(n)`

Factory that creates a **word** n-gram tokenizer:

```python
from lucis.utils.nlp import ngram_tokenizer

bigram = ngram_tokenizer(2)
bigram("hola mundo cruel")
# → ["hola mundo", "mundo cruel"]

trigram = ngram_tokenizer(3)
trigram("uno dos tres cuatro")
# → ["uno dos tres", "dos tres cuatro"]
```

### `char_ngram_tokenizer(n)`

Factory that creates a **character** n-gram tokenizer. Ideal for fuzzy search and typo tolerance:

```python
from lucis.utils.nlp import char_ngram_tokenizer

trigram = char_ngram_tokenizer(3)
trigram("python")
# → ["pyt", "yth", "tho", "hon"]

trigram("pythn")  # con typo
# → ["pyt", "yth", "thn"]
# Aún comparte "pyt" y "yth" con "python" → match parcial
```

Spaces are replaced with `_` and the text is converted to lowercase.

This is the default tokenizer for `LiteEngine`.

---

## Text Cleaners

Lucis includes text cleaning functions in `lucis.utils.nlp` that you can combine in your preprocessor:

### `lowercase(text)` / `uppercase(text)`

```python
from lucis.utils.nlp import lowercase, uppercase

lowercase("Hola Mundo")  # → "hola mundo"
uppercase("Hola Mundo")  # → "HOLA MUNDO"
```

### `strip_whitespace(text)`

Remove leading/ending spaces and normalize multiple spaces:

```python
from lucis.utils.nlp import strip_whitespace

strip_whitespace("  hola   mundo  ")  # → "hola mundo"
```

### `remove_punctuation(text, keep="")`

Remove punctuation marks (including `¡¿` from Spanish):

```python
from lucis.utils.nlp import remove_punctuation

remove_punctuation("¡Hola, mundo! ¿Cómo estás?")
# → "Hola mundo Cómo estás"

remove_punctuation("precio: $100.50", keep=".$")
# → "precio $100.50"
```

### `remove_numbers(text)`

```python
from lucis.utils.nlp import remove_numbers

remove_numbers("Python 3.11 lanzado en 2022")
# → "Python . lanzado en "
```

### `remove_extra_spaces(text)`

```python
from lucis.utils.nlp import remove_extra_spaces

remove_extra_spaces("hola    mundo   cruel")
# → "hola mundo cruel"
```

### `remove_urls(text)`

```python
from lucis.utils.nlp import remove_urls

remove_urls("Visita https://lucis.dev para más info")
# → "Visita  para más info"
```

### `remove_emails(text)`

```python
from lucis.utils.nlp import remove_emails

remove_emails("Contacto: user@empresa.com para info")
# → "Contacto:  para info"
```

### `remove_html_tags(text)`

```python
from lucis.utils.nlp import remove_html_tags

remove_html_tags("<p>Hola <b>mundo</b></p>")
# → "Hola mundo"
```

### `normalize_unicode(text)` / `remove_accents(text)`

Remove accents and diacritics. Useful for searches where accents don't matter.

```python
from lucis.utils.nlp import remove_accents

remove_accents("café résumé naïve")
# → "cafe resume naive"
```

---

## Creating your own preprocessor

### Simple Pipeline

Chain functions to create your pipeline:

```python
from lucis import Lucis
from lucis.utils.nlp import (
    word_tokenizer,
    remove_accents,
    remove_punctuation,
    remove_html_tags,
)

def preprocesador_blog(texto):
    """Pipeline para artículos de blog con HTML."""
    texto = remove_html_tags(texto)
    texto = remove_accents(texto)
    texto = remove_punctuation(texto)
    return word_tokenizer(texto)

buscador = Lucis.from_dict(articulos, name="blog", preprocessor=preprocesador_blog)
```

### Pipeline with aggressive cleaning

```python
from lucis.utils.nlp import (
    word_tokenizer,
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
    return word_tokenizer(texto)

buscador = Lucis.from_dict(emails, name="email_search", preprocessor=preprocesador_emails)
```

### Preprocessor that returns string

If your preprocessor returns `str` instead of `list[str]`, Lucis applies `simple_tokenizer` automatically:

```python
def solo_limpiar(texto):
    """Solo limpia, no tokeniza. Lucis tokenizará con simple_tokenizer."""
    return texto.lower().strip()

buscador = Lucis.from_dict(datos, name="limpio", preprocessor=solo_limpiar)
```

---

## Integration with external libraries

You can use any NLP library as a Lucis preprocessor:

### Example with NLTK

```python
import nltk
from nltk.stem import SnowballStemmer

stemmer = SnowballStemmer("spanish")

def preprocesador_nltk(texto):
    tokens = nltk.word_tokenize(texto.lower(), language="spanish")
    return [stemmer.stem(t) for t in tokens if t.isalpha()]

buscador = Lucis.from_dict(datos, name="stemmed", preprocessor=preprocesador_nltk)
```

### Example with spaCy

```python
import spacy
nlp = spacy.load("es_core_news_sm")

def preprocesador_spacy(texto):
    doc = nlp(texto)
    return [token.lemma_.lower() for token in doc if not token.is_stop and token.is_alpha]

buscador = Lucis.from_dict(datos, name="lemmatized", preprocessor=preprocesador_spacy)
```

---

## Next step

- [Storage](almacenamiento.md) — Persistence backends
- [Useful functions](funciones-utiles.md) — Standalone modular toolkit