# Lucis

> **Un toolkit NLP minimalista y generador de motores de búsqueda para Python.**

Lucis es una librería ligera y flexible diseñada para ayudar a desarrolladores a construir e integrar funcionalidad de búsqueda en sus aplicaciones con cero fricción.

Sigue una filosofía de **"poder progresivo"**:

1. **Sin dependencias**: El núcleo corre en Python 3.11+ puro. Sin extensiones C, sin librerías pesadas.
2. **Plug-and-Play**: API simple para ingestar datos y empezar a buscar inmediatamente.
3. **Persistente**: Guarda y carga tus índices (JSON, SQLite, MySQL, PostgreSQL).
4. **NLP integrado**: Incluye tokenizadores eficientes (Word, N-gram, Char-gram).

---

## Instalación

```bash
# Instalar el núcleo (sin dependencias externas)
pip install lucis

# Instalar con soporte para bases de datos SQL (MySQL, PostgreSQL, etc.)
pip install lucis[alchemy]

# MySQL
pip install lucis[mysql]

# PostgreSQL
pip install lucis[postgresql]
```

## Ejemplo rápido

```python
from lucis import Lucis

# Tu dataset (diccionario o lista)
documentos = {
    "doc1": "Python es increíble para ciencia de datos e IA",
    "doc2": "Los motores de búsqueda son sistemas complejos",
    "doc3": "Lucis hace simple construir buscadores"
}

# Inicializar y construir índice
buscador = Lucis.from_dict(documentos, name="mi_indice")

# ¡Buscar!
resultados = buscador.search("python búsqueda", top_k=2)
print(resultados)
```

**Salida:**

```
SearchResponse(
    query='python búsqueda',
    tokens=['python', 'búsqueda'],
    engine='CoreEngine',
    total_results=2,
    search_time_ms=0.14,
    results=[
        SearchResult(doc_id='doc1', score=0.275692, rank=1),
        SearchResult(doc_id='doc2', score=0.241425, rank=2)
    ]
)
```

---

## Documentación

### Empezando
- [Primeros pasos](02-primeros-pasos.md) — Tu primer buscador en 5 líneas
- [La clase Lucis](03-objeto-lucis.md) — Referencia completa del objeto principal

### Conceptos fundamentales
- [Motores de búsqueda](04-motores.md) — CoreEngine vs LiteEngine
- [Preprocesadores](05-preprocesadores.md) — Tokenizadores, limpiadores y pipelines personalizados
- [Almacenamiento](06-almacenamiento.md) — JSON, SQLite, MySQL, PostgreSQL

### Herramientas modulares
- [Funciones útiles](07-funciones-utiles.md) — Toolkit standalone: build_index, bag of words, TF-IDF, similitud coseno
- [Pruebas](16-pruebas.md) — Cómo ejecutar la suite, coverage y estructura de tests
- [Guía de tests](16-pruebas.md) — Carpeta por carpeta, comandos y flujo recomendado para contribuidores

### Funcionalidades avanzadas
- [Sharding temporal](08-sharding-temporal.md) — Partición mensual para grandes datasets
- [IndexWorker](09-worker.md) — Reindexación automática en background
- [Health Monitoring](10-salud.md) — Monitoreo de RAM, timing y diagnósticos

### Referencia técnica
- [Cómo funciona](11-como-funciona.md) — Internos: índice invertido, formato .lcs, matemáticas
- [Modelos de datos](12-modelos-datos.md) — SearchResult, SearchResponse, HealthReport
- [Excepciones](13-excepciones.md) — Manejo de errores
- [Recetas](14-recetas.md) — Ejemplos prácticos completos
- [API Reference](15-api-referencia.md) — Referencia exhaustiva de todas las funciones
- [Pruebas/Tests](16-pruebas.md) — Tests y pruebas unitarias del sistema

---

## Licencia

MIT License — [Luis Aries Meza Castillo](https://github.com/Ariiies)
