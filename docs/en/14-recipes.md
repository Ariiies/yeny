# Practical recipes

Complete end-to-end examples for common use cases. All examples are drafts with generic data — adjust them to your real case.

---

## 1. Email search engine

```python
from lucis import Lucis

emails = {
    "email_001": "Reunión de proyecto mañana a las 10am en la sala de conferencias",
    "email_002": "Factura pendiente del mes de marzo, revisar adjunto",
    "email_003": "Actualización del proyecto: fase 2 completada exitosamente",
    "email_004": "Recordatorio: entregar informe trimestral antes del viernes",
}

luc = Lucis(name="emails", engine="lite")
luc.index(emails)

response = luc.search("proyecto")
for r in response.results:
    print(f"  #{r.rank} [{r.doc_id}] score={r.score:.4f}")
    print(f"    {emails[r.doc_id][:80]}")
```

---

## 2. Blog Article Finder with SQLite

```python
from lucis import Lucis

luc = Lucis.from_sqlite_table(
    db_path="blog.db",
    table_name="posts",
    text_column="contenido",
    id_column="slug",
    name="blog_idx",
    engine="core",
    storage_type="sqlite",
)

# Buscar
response = luc.search("tutorial python", limit=5)
for r in response.results:
    print(f"  {r.doc_id}: {r.score:.4f}")

# Guardar el índice para no re-procesar al reiniciar
luc.save()

# Cargar en el próximo arranque
luc.load()
```

---

## 3. Fuzzy search with char_ngram

Character n-grams allow you to find partial matches and tolerate typos:

```python
from lucis import Lucis

productos = {
    "p1": "Laptop Dell Inspiron 15",
    "p2": "Laptop HP Pavilion",
    "p3": "Monitor Samsung 27 pulgadas",
    "p4": "Teclado Logitech MX Keys",
}

luc = Lucis(
    name="productos",
    engine="lite",
    tokenizer="char_ngram",   # trigramas de caracteres
    ngram_size=3,
)
luc.index(productos)

# "lapto" matchea con "Laptop" gracias a los n-gramas compartidos
response = luc.search("lapto dell")
for r in response.results:
    print(f"  {r.doc_id}: {r.score:.4f} → {productos[r.doc_id]}")
```

---

## 4. Worker with MySQL database

```python
from lucis import Lucis, IndexWorker

MYSQL_URL = "mysql+pymysql://user:pass@localhost/mi_db"

luc = Lucis.from_alchemy_table(
    alchemy_url=MYSQL_URL,
    table_name="articulos",
    text_column="contenido",
    id_column="id",
    date_column="created_at",
    name="articulos_idx",
    engine="lite",
    storage_type="alchemy",
    max_loaded_shards=6,
    memory_limit_mb=2048,
)

def obtener_datos():
    return luc.storage.read_table(
        "articulos", text_column="contenido", id_column="id"
    )

worker = IndexWorker(
    lucis=luc,
    data_fn=obtener_datos,
    interval=120,
    auto_purge=True,
    keep_versions=3,
    on_rebuild=lambda name: print(f"[rebuild] {name}"),
    on_error=lambda exc: print(f"[error] {exc}"),
)
worker.start()

# Tu aplicación web usa luc.search() normalmente
# El worker actualiza el índice cada 2 minutos sin interrumpir búsquedas
```

---

## 5. Multi-field search

To search multiple fields simultaneously, concatenate the fields when indexing:

```python
from lucis import Lucis

articulos = [
    {"titulo": "Guía de Python", "cuerpo": "Aprende Python desde cero", "tags": "tutorial python"},
    {"titulo": "API REST con Flask", "cuerpo": "Construye APIs robustas", "tags": "api flask python"},
    {"titulo": "Base de datos SQL", "cuerpo": "Fundamentos de SQL", "tags": "sql base-datos"},
]

# Concatenar campos con separador
datos = {}
for i, art in enumerate(articulos):
    texto = f"{art['titulo']} {art['cuerpo']} {art['tags']}"
    datos[f"art_{i}"] = texto

luc = Lucis(name="articulos", engine="core")
luc.index(datos)

# Busca en todos los campos a la vez
response = luc.search("python api")
```

---

## 6. Modular use — Standalone function without Lucis

You can use Lucis functions without the main class:

```python
from lucis.utils.index import build_index, get_doc_len
from lucis.utils.index import compute_tfidf
from lucis.utils.math.core import sparse_cosine_similarity
from lucis.utils.nlp import word_tokenizer

# Corpus
corpus = [
    "python es un lenguaje de programación",
    "machine learning con python",
    "desarrollo web con javascript",
]

# Tokenizar y construir índice
tokenized = [word_tokenizer(doc) for doc in corpus]
index = build_index(tokenized)
doc_lengths = get_doc_len(index, len(corpus))

# Calcular vector TF-IDF para un documento
vector_doc0 = {}
for token in tokenized[0]:
    score = compute_tfidf(token, 0, index, doc_lengths, len(corpus))
    if score > 0:
        vector_doc0[token] = score

# Calcular vector de query
query_tokens = word_tokenizer("python programación")
query_vector = {}
for token in query_tokens:
    score = compute_tfidf(token, 0, index, doc_lengths, len(corpus))
    if score > 0:
        query_vector[token] = score

# Similitud
sim = sparse_cosine_similarity(query_vector, vector_doc0)
print(f"Similitud: {sim:.4f}")
```

---

## 7. Migration between storages

```python
from lucis import Lucis

# Empezar con JSON (desarrollo)
luc = Lucis(name="mi_idx", engine="lite", storage_type="json")
luc.index(mis_datos)
luc.save()

# Migrar a SQLite (producción)
luc_prod = Lucis(name="mi_idx", engine="lite", storage_type="sqlite", db_path="prod.db")
luc_prod.index(mis_datos)  # re-indexar con el nuevo storage
luc_prod.save()

# O migrar a PostgreSQL
luc_pg = Lucis(
    name="mi_idx",
    engine="lite",
    storage_type="alchemy",
    alchemy_url="postgresql+psycopg2://user:pass@host/db",
)
luc_pg.index(mis_datos)
luc_pg.save()
```

---

## 8. Health monitoring in production

```python
import json
import time
from lucis import Lucis

luc = Lucis(name="prod_idx", engine="lite", storage_type="sqlite", db_path="prod.db")
luc.load()

# Health check puntual con benchmark
report = luc.health_check(benchmark_query="test de latencia")
print(report)

# Exportar para sistema de monitoreo
data = report.to_dict()
# enviar_a_datadog(data)  # o prometheus, grafana, etc.

# Monitoreo continuo
monitor = luc.health_monitor(interval=60)
monitor.start()

# ... aplicación en ejecución ...

monitor.stop()
monitor.print_summary()
```

---

## 9. Custom Preprocessor with Advanced Cleanup

```python
from lucis import Lucis
from lucis.utils.nlp import (
    word_tokenizer,
    clean_whitespace,
    clean_html,
    clean_urls,
    clean_emails,
    lowercase,
)

def mi_preprocesador(text):
    """Pipeline personalizado: limpia HTML, URLs, emails, luego tokeniza."""
    text = clean_html(text)
    text = clean_urls(text)
    text = clean_emails(text)
    text = clean_whitespace(text)
    text = lowercase(text)
    return word_tokenizer(text)

luc = Lucis(
    name="web_scraping",
    engine="core",
    preprocessor=mi_preprocesador,
)
luc.index(datos_web)
```

---

## 10. Rollback to previous version

```python
from lucis import Lucis

luc = Lucis(name="mi_idx", engine="lite", storage_type="sqlite", db_path="app.db")

# Ver versiones disponibles
versiones = luc.list_versions()
for v in versiones:
    print(v)

# Cargar una versión específica
luc.load(version=versiones[-2])  # penúltima versión

# Verificar
report = luc.health_check()
print(f"Docs: {report.total_docs}")
```

---

## Next step

- [API Reference](api-referencia.md) — All signatures and parameters
- [How it works](como-funciona.md) — Engine internals