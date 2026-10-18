# Practical recipes

Complete end-to-end examples for common use cases. All examples are drafts with generic data — adjust them to your real case.

---

## 1. Email search engine

```python
from yeny import Yeny

emails = {
    "email_001": "Reunión de proyecto mañana a las 10am en la sala de conferencias",
    "email_002": "Factura pendiente del mes de marzo, revisar adjunto",
    "email_003": "Actualización del proyecto: fase 2 completada exitosamente",
    "email_004": "Recordatorio: entregar informe trimestral antes del viernes",
}

yn = Yeny(name="emails", engine="lite")
yn.index(emails)

response = yn.search("proyecto")
for r in response.results:
    print(f"  #{r.rank} [{r.doc_id}] score={r.score:.4f}")
    print(f"    {emails[r.doc_id][:80]}")
```

---

## 2. Blog Article Finder with SQLite

```python
from yeny import Yeny
from yeny.config import YenyOptions

yn = Yeny.from_sqlite_table(
    db_path="blog.db",
    table_name="posts",
    text_column="contenido",
    id_column="slug",
    name="blog_idx",
    engine="core",
)

# Buscar
response = yn.search("tutorial python", top_k=5)
for r in response.results:
    print(f"  {r.doc_id}: {r.score:.4f}")

# The factory persists automatically; a new process can reopen it:
yn = Yeny(
    name="blog_idx",
    engine="core",
    options=YenyOptions(storage_type="sqlite", db_path="blog.db"),
)
```

---

## 3. Fuzzy search with char_ngram

Character n-grams allow you to find partial matches and tolerate typos:

```python
from yeny import Yeny

productos = {
    "p1": "Laptop Dell Inspiron 15",
    "p2": "Laptop HP Pavilion",
    "p3": "Monitor Samsung 27 pulgadas",
    "p4": "Teclado Logitech MX Keys",
}

yn = Yeny(
    name="productos",
    engine="lite",
)
yn.index(productos)

# "lapto" matchea con "Laptop" gracias a los n-gramas compartidos
response = yn.search("lapto dell")
for r in response.results:
    print(f"  {r.doc_id}: {r.score:.4f} → {productos[r.doc_id]}")
```

---

## 4. Worker with MySQL database

```python
from yeny import Yeny
from yeny.config import YenyOptions, TableSource

MYSQL_URL = "mysql+pymysql://user:pass@localhost/mi_db"

yn = Yeny.from_table(
    TableSource(
        table="articulos",
        connection_url=MYSQL_URL,
        text_columns="contenido",
        id_column="id",
        date_column="created_at",
    ),
    name="articulos_idx",
    engine="lite",
    options=YenyOptions(max_loaded_shards=6, memory_limit_mb=2048),
)

worker = yn.create_worker(
    interval=120,
    connection_url=MYSQL_URL,
    auto_purge=True,
    keep_versions=3,
    on_rebuild=lambda name: print(f"[rebuild] {name}"),
    on_error=lambda exc: print(f"[error] {exc}"),
)
worker.start()

# Tu aplicación web usa yn.search() normalmente
# El worker actualiza el índice cada 2 minutos sin interrumpir búsquedas
```

---

## 5. Multi-field search

To search multiple fields simultaneously, concatenate the fields when indexing:

```python
from yeny import Yeny
from yeny.config import YenyOptions

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

yn = Yeny(name="articulos", engine="core")
yn.index(datos)

# Busca en todos los campos a la vez
response = yn.search("python api")
```

---

## 6. Modular use — Standalone function without Yeny

You can use Yeny functions without the main class:

```python
from yeny.utils.index import build_index, get_doc_len
from yeny.utils.index import compute_tfidf
from yeny.utils.math.core import sparse_cosine_similarity
from yeny.utils.nlp import WordTokenizer

# Corpus
corpus = [
    "python es un lenguaje de programación",
    "machine learning con python",
    "desarrollo web con javascript",
]

# Tokenizar y construir índice
tokenized = [WordTokenizer()(doc) for doc in corpus]
index = build_index(tokenized)
doc_lengths = get_doc_len(index, len(corpus))

# Calcular vector TF-IDF para un documento
vector_doc0 = {}
for token in tokenized[0]:
    score = compute_tfidf(token, 0, index, doc_lengths, len(corpus))
    if score > 0:
        vector_doc0[token] = score

# Calcular vector de query
query_tokens = WordTokenizer()("python programación")
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
from yeny import Yeny

# Empezar con JSON (desarrollo)
yn = Yeny(name="mi_idx", engine="lite")
yn.index(mis_datos)
yn.save()

# Migrar a SQLite (producción)
luc_prod = Yeny(
    name="mi_idx",
    engine="lite",
    options=YenyOptions(storage_type="sqlite", db_path="prod.db"),
)
luc_prod.index(mis_datos)  # re-indexar con el nuevo storage
luc_prod.save()

# O migrar a PostgreSQL
luc_pg = Yeny(
    name="mi_idx",
    engine="lite",
    options=YenyOptions(
        storage_type="alchemy",
        connection_url="postgresql+psycopg2://user:pass@host/db",
    ),
)
luc_pg.index(mis_datos)
luc_pg.save()
```

---

## 8. Health monitoring in production

```python
import json
import time
from yeny import Yeny
from yeny.config import YenyOptions

yn = Yeny(
    name="prod_idx",
    engine="lite",
    options=YenyOptions(storage_type="sqlite", db_path="prod.db"),
)

# Health check puntual con benchmark
report = yn.health_check(benchmark_query="test de latencia")
print(report)

# Exportar para sistema de monitoreo
data = report.to_dict()
# enviar_a_datadog(data)  # o prometheus, grafana, etc.

# Monitoreo continuo
monitor = yn.health_monitor(interval=60)
monitor.start()

# ... aplicación en ejecución ...

monitor.stop()
monitor.print_summary()
```

---

## 9. Custom Preprocessor with Advanced Cleanup

```python
from yeny import Yeny
from yeny.utils.nlp import (
    WordTokenizer,
    remove_html_tags,
    remove_urls,
    remove_emails,
    strip_whitespace,
    lowercase,
)

def mi_preprocesador(text):
    """Pipeline personalizado: limpia HTML, URLs, emails, luego tokeniza."""
    text = remove_html_tags(text)
    text = remove_urls(text)
    text = remove_emails(text)
    text = strip_whitespace(text)
    text = lowercase(text)
    return WordTokenizer()(text)

yn = Yeny(
    name="web_scraping",
    engine="core",
    preprocessor=mi_preprocesador,
)
yn.index(datos_web)
```

---

## 10. Rollback to previous version

```python
from yeny import Yeny
from yeny.config import YenyOptions

yn = Yeny(
    name="mi_idx",
    engine="lite",
    options=YenyOptions(storage_type="sqlite", db_path="app.db"),
)

# Ver versiones disponibles
versiones = yn.list_versions()
for v in versiones:
    print(v)

# Volver a la versión anterior y recargarla
yn.rollback()

# Verificar
report = yn.health_check()
print(f"Docs: {report.total_docs}")
```

---

## Next step

- [API Reference](15-api-reference.md) — All signatures and parameters
- [How it works](11-how-it-works.md) — Engine internals
