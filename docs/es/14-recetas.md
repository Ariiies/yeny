# Recetas prácticas

Ejemplos completos de extremo a extremo para casos de uso comunes. Todos los ejemplos son borradores con datos genéricos — ajústalos a tu caso real.

---

## 1. Buscador de emails

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

## 2. Buscador de artículos de blog con SQLite

```python
from lucis import Lucis
from lucis.config import LucisOptions

luc = Lucis.from_sqlite_table(
    db_path="blog.db",
    table_name="posts",
    text_column="contenido",
    id_column="slug",
    name="blog_idx",
    engine="core",
)

# Buscar
response = luc.search("tutorial python", top_k=5)
for r in response.results:
    print(f"  {r.doc_id}: {r.score:.4f}")

# El factory persiste automáticamente; otro proceso puede reabrirlo:
luc = Lucis(
    name="blog_idx",
    engine="core",
    options=LucisOptions(storage_type="sqlite", db_path="blog.db"),
)
```

---

## 3. Búsqueda fuzzy con char_ngram

Los n-gramas de caracteres permiten encontrar coincidencias parciales y tolerar errores tipográficos:

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
)
luc.index(productos)

# "lapto" matchea con "Laptop" gracias a los n-gramas compartidos
response = luc.search("lapto dell")
for r in response.results:
    print(f"  {r.doc_id}: {r.score:.4f} → {productos[r.doc_id]}")
```

---

## 4. Worker con base de datos MySQL

```python
from lucis import Lucis
from lucis.config import LucisOptions, TableSource

MYSQL_URL = "mysql+pymysql://user:pass@localhost/mi_db"

luc = Lucis.from_table(
    TableSource(
        table="articulos",
        connection_url=MYSQL_URL,
        text_columns="contenido",
        id_column="id",
        date_column="created_at",
    ),
    name="articulos_idx",
    engine="lite",
    options=LucisOptions(max_loaded_shards=6, memory_limit_mb=2048),
)

worker = luc.create_worker(
    interval=120,
    connection_url=MYSQL_URL,
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

## 5. Búsqueda multi-campo

Para buscar en varios campos simultáneamente, concatena los campos al indexar:

```python
from lucis import Lucis
from lucis.config import LucisOptions

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

## 6. Uso modular — Función standalone sin Lucis

Puedes usar las funciones de Lucis sin la clase principal:

```python
from lucis.utils.index import build_index, get_doc_len
from lucis.utils.index import compute_tfidf
from lucis.utils.math.core import sparse_cosine_similarity
from lucis.utils.nlp import WordTokenizer

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

## 7. Migración entre storages

```python
from lucis import Lucis

# Empezar con JSON (desarrollo)
luc = Lucis(name="mi_idx", engine="lite")
luc.index(mis_datos)
luc.save()

# Migrar a SQLite (producción)
luc_prod = Lucis(
    name="mi_idx",
    engine="lite",
    options=LucisOptions(storage_type="sqlite", db_path="prod.db"),
)
luc_prod.index(mis_datos)  # re-indexar con el nuevo storage
luc_prod.save()

# O migrar a PostgreSQL
luc_pg = Lucis(
    name="mi_idx",
    engine="lite",
    options=LucisOptions(
        storage_type="alchemy",
        connection_url="postgresql+psycopg2://user:pass@host/db",
    ),
)
luc_pg.index(mis_datos)
luc_pg.save()
```

---

## 8. Monitoreo de salud en producción

```python
import json
import time
from lucis import Lucis
from lucis.config import LucisOptions

luc = Lucis(
    name="prod_idx",
    engine="lite",
    options=LucisOptions(storage_type="sqlite", db_path="prod.db"),
)

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

## 9. Preprocesador personalizado con limpieza avanzada

```python
from lucis import Lucis
from lucis.utils.nlp import (
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

luc = Lucis(
    name="web_scraping",
    engine="core",
    preprocessor=mi_preprocesador,
)
luc.index(datos_web)
```

---

## 10. Rollback a versión anterior

```python
from lucis import Lucis
from lucis.config import LucisOptions

luc = Lucis(
    name="mi_idx",
    engine="lite",
    options=LucisOptions(storage_type="sqlite", db_path="app.db"),
)

# Ver versiones disponibles
versiones = luc.list_versions()
for v in versiones:
    print(v)

# Volver a la versión anterior y recargarla
luc.rollback()

# Verificar
report = luc.health_check()
print(f"Docs: {report.total_docs}")
```

---

## Siguiente paso

- [Referencia API](15-api-referencia.md) — Todas las firmas y parámetros
- [Cómo funciona](11-como-funciona.md) — Internos del motor
