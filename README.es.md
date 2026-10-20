<p align="center">
  <img src="assets/yeny_lockup3.png" height="120" align="middle" alt="Yeny Logo">
</p>

<p align="center">
  <a href="https://github.com/sponsors/Ariiies"><img src="https://img.shields.io/badge/Sponsor-GitHub-ea4aaa?logo=github" alt="Sponsor"></a>
  <a href="https://pypi.org/project/yeny/"><img src="https://img.shields.io/pypi/v/yeny" alt="PyPI"></a>
  <a href="https://www.python.org/"><img src="https://img.shields.io/badge/python-3.10+-blue" alt="Python"></a>
</p>

<p align="center">
  <b>🌐 Language / Idioma:</b> &nbsp;
  <a href="https://github.com/Ariiies/yeny#readme">English</a> &nbsp;|&nbsp;
  <strong>Español</strong>
</p>

> Un toolkit ligero para construir sistemas de búsqueda personalizados en Python.

### "Una forma fácil de construir motores de búsqueda en Python."

Yeny es un toolkit de búsqueda ligero y orientado a producción que te ayuda a construir funcionalidades de búsqueda de texto completo rápidamente, sin renunciar a controles avanzados cuando tu conjunto de datos crece.

Sigue una filosofía de potencia progresiva:
- Comienza con Python puro y cero dependencias externas obligatorias.
- Escala a persistencia respaldada por SQL y fragmentación temporal cuando sea necesario.
- Mantén la ergonomía de la API simple a través de un único punto de entrada de alto nivel: `Yeny`.

## Tabla de Contenidos

- [Características](#características)
- [Instalación](#instalación)
- [Inicio Rápido](#inicio-rápido)
- [Ejemplos](#ejemplos)
- [Arquitectura General](#arquitectura-general)
- [¿Por qué Yeny?](#por-qué-yeny)
- [Documentación](#documentación)
- [Benchmarks](#benchmarks)
- [Pruebas](#pruebas)
- [Patrocinar](#patrocinar)
- [Contribuir](#contribuir)
- [Hoja de Ruta](#hoja-de-ruta)
- [Dedicatoria](#dedicatoria)
- [Licencia](#licencia)

## Características

- Motores en Python puro (`core` y `lite`)
- Preprocesadores y tokenizadores NLP integrados
- Recuperación con ranking y modelos de respuesta estructurados
- **Persistencia binaria (`.yny`)** — archivos de índice mapeados en memoria para carga con RAM casi cero, más metadatos ligeros en SQLite (modo WAL). La persistencia es **automática** — `from_dict()`, `from_list()` y `from_table()` guardan sin necesidad de llamar a `.save()`.
- **Ingesta directa desde BD** — lee desde tablas SQLite, MySQL o PostgreSQL sin contaminar tu base de datos (adaptadores de solo lectura, cero tablas `yeny_*` en tu BD)
- Persistencia de índices versionada con soporte de rollback
- Fragmentación temporal para grandes corpus de series temporales
- Reindexación en segundo plano con `IndexWorker` (cero tiempo de inactividad)
- Reportes de salud y diagnóstico
- Funciones utilitarias independientes para indexación y matemáticas vectoriales
- Backends opcionales de almacenamiento JSON o SQL completo para casos de uso más simples

## Instalación

Instala desde [PyPI](https://pypi.org/project/yeny/):

```bash
pip install yeny
```

Soporte SQL opcional:

```bash
# Soporte genérico con SQLAlchemy
pip install yeny[alchemy]

# MySQL
pip install yeny[mysql]

# PostgreSQL
pip install yeny[postgresql]
```

Alternativamente, instala desde el código fuente:

```bash
git clone https://github.com/Ariiies/yeny.git
cd yeny
pip install .
```

## Inicio Rápido

```python
from yeny import Yeny

documents = {
    "doc1": "Python is a versatile language for backend systems",
    "doc2": "JavaScript dominates modern frontend development",
    "doc3": "Yeny makes search implementation straightforward",
}

searcher = Yeny.from_dict(documents, name="demo_index", engine="core")
response = searcher.search("python frontend", top_k=2)

print(response)
# Output:
# SearchResponse(
#     query='python frontend',
#     tokens=['python', 'frontend'],
#     engine='CoreEngine',
#     total_results=2,
#     search_time_ms=0.14,
#     results=[
#         SearchResult(doc_id='doc1', score=0.2757, rank=1),
#         SearchResult(doc_id='doc2', score=0.2414, rank=2)
#     ]
# )
```

Las factorías persisten automáticamente. Recarga después con el mismo nombre lógico:

```python
loaded = Yeny(name="demo_index")
response = loaded.search("python")
```

La infraestructura avanzada es opcional y tipada:

```python
from yeny import Yeny
from yeny.config import YenyOptions, TableConfig, TableSource

options = YenyOptions(storage_dir="search_data", memory_limit_mb=512)
searcher = Yeny.from_table(
    TableSource(
        table="articles",
        connection_url=DB_URL,
        text_columns=["title", "body"],
        id_column="id",
        date_column="created_at",
    ),
    engine="lite",
    config=TableConfig(where_clause="published = 1"),
    options=options,
)
```

`YenyOptions.binary_dir` acepta `"auto"` (deriva `<storage_dir>/yny`),
`None` (desactiva la persistencia `.yny`) o un directorio explícito.

## Ejemplos

Escenarios ejecutables y documentados de extremo a extremo están en [`examples/`](examples/):

- **[Búsqueda cifrada sobre MySQL](examples/encrypted_search/README.md)** —
  búsqueda de texto completo sobre columnas cifradas con Fernet (`name`/`email`/`number`)
  usando un índice ciego de HMAC-trigramas, fragmentación temporal, persistencia `.yny`
  y un playground interactivo. Toda la integración con Yeny
  cabe en ~15 líneas dentro de `playground.py`.

```bash
cd examples/encrypted_search
pip install "../..[encrypted-search-example]"
python seed_controlled_data.py && python playground.py
```

Consulta [`examples/encrypted_search/README.md`](examples/encrypted_search/README.md)
para la configuración, modelo de seguridad y guía de adaptación.

## Arquitectura General

```
                  ┌──────────────────┐
                  │  DatabaseReader  │  ← solo lectura (tu BD)
                  │ SQLite / MySQL / │
                  │   PostgreSQL     │
                  └────────┬─────────┘
                           │ ingesta de datos
                           ▼
Documentos → Preprocesadores → Motor → Almacenamiento
                │                │
                ▼                ▼
          Tokenizadores   ┌──────────────┐
          (word, char,    │ binarios .yny │  ← mmap (datos del índice)
           n-gram)        │  + SQLite WAL │  ← metadatos y alias
                          └──────────────┘
```

- `yeny.main.Yeny`: API de alto nivel y orquestación (patrón Facade)
- `yeny.engines`:
    - `CoreEngine`: TF-IDF + similitud del coseno
    - `LiteEngine`: enfoque ligero de TF normalizado
- `yeny.storage`:
    - `MetadataStorage` **(recomendado)**: SQLite WAL para metadatos + binarios `.yny` para datos del índice
    - `JSONStorage`: archivos `.json` simples (simple / depuración)
    - `SQLiteStorage`: índice completo serializado en tablas SQLite
    - `AlchemyStorage`: índice completo serializado vía SQLAlchemy (MySQL, PostgreSQL, etc.)
- `yeny.storage.DatabaseReader`: adaptador de **solo lectura** para ingestar desde tu BD sin crear tablas `yeny_*`
- `yeny.worker`: worker asíncrono/periódico de reindexación (cero tiempo de inactividad)
- `yeny.health`: reportes de salud del sistema e índices
- `yeny.utils`: NLP, helpers de indexación, matemáticas, serialización, helpers de mmap

## ¿Por qué Yeny?

> **Nota:** La comparación a continuación es cualitativa. Los benchmarks de Yeny comparan
> sus propios motores `core` y `lite`; no evalúan proyectos externos.

| Característica | Yeny | Whoosh | Meilisearch | Elasticsearch |
|---|---|---|---|---|
| **Python puro (cero deps)** | ✅ | ✅ | ❌ (Rust) | ❌ (Java) |
| **Ingesta directa desde tablas** | ✅ | ❌ | ❌ | ❌ |
| **Fragmentación temporal** | ✅ | ❌ | ❌ | ✅ |
| **Worker en segundo plano** | ✅ | ❌ | ❌ | ✅ |
| **Rollback / versionado** | ✅ | ❌ | ❌ | ✅ |
| **Docs bilingües (EN + ES)** | ✅ | ❌ | ❌ | ❌ |
| **Cero servicios externos** | ✅ | ✅ | ❌ | ❌ |

**Donde Yeny brilla:**

Yeny está construido para **proyectos pequeños y medianos** que necesitan búsqueda sin la sobrecarga de una infraestructura de búsqueda completa. No necesitas levantar un servidor separado, configurar clusters ni aprender un nuevo DSL de consultas — solo `pip install yeny` y listo.

- **Proyectos pequeños y prototipos** — Cuando tu conjunto de datos está en los miles o bajos millones de documentos, Yeny te da búsqueda con calidad de producción sin levantar una instancia de Elasticsearch o Meilisearch.
- **Casos de uso embebidos** — Ideal para herramientas CLI, aplicaciones de escritorio o backends Python (Flask, FastAPI) que necesitan búsqueda como biblioteca, no como servicio.
- **Alta personalización** — Intercambia tokenizadores, inyecta tus propios preprocesadores o incluso trae bibliotecas NLP externas (spaCy, NLTK). Yeny se adapta a tu dominio, no al revés.
- **Datos nativos en SQL** — Si tus datos ya viven en SQLite, MySQL o PostgreSQL, Yeny ingesta directamente desde tablas o consultas — sin necesidad de pipelines ETL.
- **Corpus de series temporales** — La fragmentación temporal te permite consultar logs, correos o artículos por rango de fechas sin cargar todo en RAM.

## Documentación

Yeny incluye documentación completa en español e inglés.

- [Índice en Español](docs/es/01-index.md)
- [English Index](docs/en/01-index.md)

Puntos de entrada útiles:

- Primeros pasos: [Español](docs/es/02-primeros-pasos.md), [English](docs/en/02-first-steps.md)
- Referencia del objeto Yeny: [Español](docs/es/03-objeto-yeny.md), [English](docs/en/03-yeny-object.md)
- Referencia de API: [Español](docs/es/15-api-referencia.md), [English](docs/en/15-api-reference.md)
- Guía de pruebas: [Español](docs/es/16-pruebas.md), [English](docs/en/16-tests.md)
- Guía de benchmarks: [Español](docs/es/17-benchmarks.md), [English](docs/en/17-benchmarks.md)

## Benchmarks

Yeny incluye una suite determinista local para comparar `CoreEngine` y
`LiteEngine` con el mismo corpus generado, consultas y tokenizador:

```bash
python -m benchmarks run --profile tiny
```

Mide construcción de índices, latencia de búsqueda pública, persistencia
JSON/SQLite, serialización `.yny` y carga por `mmap`, tamaño de artefactos
y memoria RSS disponible. Los resultados se guardan como JSON con marca
temporal para que las ejecuciones puedan validarse y compararse sin
sobrescribir datos previos.

Estos benchmarks miden velocidad, uso de recursos y fidelidad de persistencia—no
relevancia de búsqueda ni rendimiento frente a otros proyectos. Consulta la
[guía en español](docs/es/17-benchmarks.md), la
[English guide](docs/en/17-benchmarks.md) o la
[referencia rápida del runner](benchmarks/README.md). La campaña multiplataforma
publicada, resultados brutos, reportes generados y presentación están disponibles en
el [paquete de documentación de benchmarks](docs/benchmarks/README.md).

## Pruebas

```bash
python -m pytest -q
```

## Patrocinar

Yeny es un proyecto de código abierto. Si este toolkit te ha ahorrado tiempo o te ha ayudado a construir funcionalidades de búsqueda robustas, considera apoyar su desarrollo y mantenimiento continuo.

💝 [Patrocina Yeny en GitHub](https://github.com/sponsors/Ariiies)

## Contribuir

Las contribuciones son bienvenidas. Abre un issue o envía un pull request.

## Hoja de Ruta

El desarrollo avanza paso a paso—priorizando la ergonomía en Python puro primero, mientras se construye progresivamente aceleración nativa opcional en paralelo.

### Motores Planificados (Python Puro)

| Motor | Estado | Descripción |
|---|---|---|
| **BM25Engine** | 🧪 Planificado | Scoring de relevancia BM25 — mejor saturación IDF y normalización por longitud de documento que TF-IDF. Ideal para búsqueda de propósito general. |
| **NanoEngine / CountEngine** | 🧪 Planificado | Motor ultraligero de frecuencia de términos bruta (bag-of-words) con cero overhead de normalización. Diseñado para máxima velocidad en escenarios de coincidencia simple de palabras clave junto a `LiteEngine`. |

### Vía Paralela: Aceleración con Rust

| Componente | Estado | Descripción |
|---|---|---|
| **Rust Core & Tokenizers** | 🦀 En Progreso | Integración gradual de bindings opcionales en Rust (vía PyO3) desarrollados en paralelo para acelerar tokenización, construcción de índices invertidos y kernels de scoring, manteniendo intacto el fallback en Python puro. |

### Tentativo / Exploración Futura

- 🔬 **Búsqueda difusa y tolerante a errores:** Coincidencia Levenshtein/Damerau-Levenshtein integrada en el pipeline de búsqueda.
- 🔬 **Búsqueda facetada:** Filtrar resultados por campos de metadatos (categoría, fecha, autor) junto al scoring de texto completo.
- 🔬 **Stemming multilenguaje:** Soporte opcional de stemming para español, inglés y más.

> **Leyenda:** 🧪 Planificado = siguiente en el pipeline · 🦀 En Progreso = vía paralela · 🔬 Tentativo = exploración a largo plazo

## Dedicatoria

> **En amorosa memoria de mi madre, Yeny.**
>
> Este proyecto lleva su nombre como un homenaje a su vida, su calidez y todo lo que me enseñó. Cada línea de código en **Yeny** se comparte libremente con la comunidad de desarrolladores en su honor, para que su nombre siga construyendo, conectando y ayudando a otros a crear. ❤️

## Licencia

[Licencia MIT](LICENSE)

