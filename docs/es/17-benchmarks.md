# Benchmarks

Lucis incluye una suite de benchmarks pequeña y determinista para responder
preguntas prácticas sobre sus dos motores públicos:

- ¿Cuánto tarda construirse un índice?
- ¿Cuánto tardan los distintos tipos de búsqueda?
- ¿Cuánto tardan las operaciones de persistencia JSON, SQLite y `.lcs`?
- ¿Qué tan grandes son los artefactos generados?
- ¿Qué ocurre cuando un índice se carga normalmente o mediante `mmap`?
- ¿La persistencia conserva IDs, orden del ranking y scores?
- ¿Cuánta memoria RSS se observa durante cada fase del worker?

La suite **no** mide relevancia de búsqueda, exactitud, recall, throughput
concurrente ni rendimiento frente a proyectos externos de búsqueda.

## Inicio rápido

Ejecuta los comandos desde un clon local del repositorio de Lucis:

```bash
python -m pip install -e .
python -m benchmarks run --profile tiny
```

La suite estándar no tiene dependencias obligatorias de benchmark. Para el
muestreo RSS del árbol de procesos, instala el extra opcional:

```bash
python -m pip install -e ".[benchmark]"
python -m benchmarks run --profile tiny --require-memory
```

El comando predeterminado ejecuta ambos motores. Selecciona un motor u otro
perfil cuando lo necesites:

```bash
python -m benchmarks run --profile small --engine core
python -m benchmarks run --profile medium --engine lite
python -m benchmarks run --profile small --warmups 5 --repetitions 20
```

`tiny` es la prueba de humo, `small` es la comparación local rápida más útil,
`medium` permite revisar el escalado y `large` es el límite oficial de
escalado, siempre opt-in. `large` nunca se ejecuta por accidente: debe
solicitarse explícitamente.

## Perfiles reproducibles

| Perfil | Documentos | Vocabulario | Longitud del documento | Predeterminado |
|---|---:|---:|---:|---|
| `tiny` | 100 | 2,048 términos | 12–52 tokens | Sí |
| `small` | 1,000 | 2,048 términos | 12–52 tokens | Opt-in |
| `medium` | 10,000 | 2,048 términos | 12–52 tokens | Opt-in |
| `large` | 100,000 | 2,048 términos | 12–52 tokens | Opt-in |

Todos los perfiles usan:

- seed `20260117`;
- generador `lexical_zipf_v1`;
- distribución de términos tipo Zipf con exponente `1.07`;
- distribución triangular de longitud con moda de 32 tokens;
- 2% de documentos duplicados intencionalmente;
- 17 consultas deterministas: 4 comunes, 4 raras, 4 de varios tokens, 4 sin
  resultados y 1 consulta repetida.

Cada perfil tiene hashes SHA-256 congelados de dataset y consultas en
`benchmarks/reference_hashes.json`. Antes de medir cualquier motor, el worker
de construcción regenera el corpus y compara ambos hashes contra el contrato
congelado. Una diferencia aborta la ejecución: significa que el generador
determinista divergió, y la causa debe investigarse en lugar de editar la
referencia. Los hashes demuestran que dos ejecuciones recibieron entradas
generadas idénticas; no significan que el tiempo medido deba ser idéntico.

## Una comparación justa entre Core y Lite

`CoreEngine` usa TF-IDF y similitud coseno. `LiteEngine` usa frecuencia de
término normalizada. Su comportamiento de ranking es distinto, pero ambos son
motores Python puro expuestos por la misma fachada `Lucis`.

Para comparar tiempos justamente, el benchmark entrega a ambos el mismo
corpus, consultas, `top_k=10` y `WordTokenizer`. Esto es importante porque
`LiteEngine` utiliza trigramas de caracteres de forma predeterminada. Usar un
tokenizer diferente por motor mezclaría el costo del motor con diferencias de
tokenización y tamaño del índice.

Por lo tanto, estos números comparan las dos implementaciones de ranking bajo
una configuración léxica controlada. No comparan sus valores predeterminados
nativos ni establecen qué motor produce resultados más relevantes.

## Cómo leer los números

Las mediciones de construcción, guardado, carga y tamaño tienen una muestra
por ejecución, así que su mediana y p95 mostrados son el mismo valor. Las
categorías de búsqueda contienen varias muestras por categoría (40 con las 10
repeticiones predeterminadas) y la categoría de consulta repetida contiene
100, así que ahí la mediana y el p95 sí son útiles. Ejecuta el comando varias
veces y agrega al comparar operaciones de una sola muestra.

Una invocación es una máquina y un momento. Para datos de campaña, ejecuta el
mismo comando varias veces y combina los resultados con `aggregate` (abajo),
que reporta la mediana de las medianas por ejecución junto con el mínimo y el
máximo como rango de variabilidad.

## Métricas

| Métrica | Frontera medida |
|---|---|
| `dataset_generation` | Solo la generación determinista del corpus |
| `index_build` | `Lucis.index(..., persist=False)` |
| `index_e2e_json` | Construcción mediante `Lucis.from_dict`, incluida la persistencia JSON automática |
| `search_first` | Primera `Lucis.search` pública tras construir |
| `search_warm` | Búsquedas públicas tras warm-ups no medidos, agrupadas por categoría |
| `json_save`, `sqlite_save` | `Lucis.save` público |
| `*_artifact_size` | Bytes reales escritos en disco |
| `lcs_write` | Serialización `.lcs` del motor |
| `load_standard` | Constructor `Lucis` con autocarga para JSON o SQLite |
| `mmap_load` | Operación `load_mmap` del motor |
| `search_first_*`, `search_warm_*` | Búsqueda pública tras carga estándar o mapeada |
| `roundtrip_verified` | Número de consultas que conservan IDs, orden y scores |
| `memory_*` | Observaciones RSS de una fase completa del worker |

El tiempo de búsqueda incluye el preprocesamiento de la consulta y la
construcción de la respuesta porque el temporizador rodea la llamada pública
`Lucis.search`.

La verificación round-trip compara, para cada consulta y cada backend (JSON,
SQLite y `mmap`): el número de resultados, el ID de documento en cada
posición del ranking, el orden completo y cada score dentro de una tolerancia
documentada (`rel_tol=1e-9`, `abs_tol=1e-12`). Cualquier diferencia aborta la
ejecución en lugar de escribir un resultado aparentemente exitoso. Es una
prueba de fidelidad de la persistencia, no una métrica de relevancia.

## Modelo de procesos y memoria

Core y Lite se ejecutan por separado. Cada motor obtiene **cuatro**
intérpretes Python nuevos dentro de un único workspace temporal:

```text
motor
├── build          genera el corpus, construye, busca y persiste todo
├── load_json      recarga el artefacto JSON en un intérprete frío
├── load_sqlite    recarga el artefacto SQLite en un intérprete frío
└── load_mmap      mapea el artefacto .lcs en un intérprete frío
```

El proceso de construcción escribe en el workspace el manifiesto del dataset,
el conjunto de consultas, los resultados esperados por consulta y los
artefactos JSON/SQLite/`.lcs`. Cada proceso de carga lee ese contrato —sin
regenerar el corpus— y mide exactamente un backend, de modo que ningún
backend hereda cachés de importación ni estado de motor calentado por otro.
El tiempo de creación del proceso queda fuera de la frontera medida de carga.
Las conexiones SQLite y los handles mmap siempre se cierran antes de eliminar
el workspace.

Esto hace que cada carga sea «process-cold» respecto al intérprete Python.
La caché de páginas del sistema operativo **no** se vacía ni se controla —no
existe una forma portable y segura de hacerlo— y esa limitación se declara en
cada reporte.

Con `psutil` instalado, el proceso padre muestrea el árbol completo del
worker cada 5 ms y reporta, por motor **y fase** (`build`, `load_json`,
`load_sqlite`, `load_mmap`): RSS base, RSS pico, delta del pico, RSS propio
al final de la fase tras la recolección de basura y el máximo de procesos.
Estos valores describen el workflow completo de la fase, no el tamaño
exclusivo de ningún objeto engine. RSS no es propiedad exclusiva: las páginas
copy-on-write de fork pueden contarse más de una vez, los picos cortos pueden
escapar al muestreo, las arenas del asignador pueden permanecer y pueden
existir referencias vivas al final de la fase.

Sin `psutil`, Unix puede recurrir al pico RSS propio mediante `resource`;
Linux también puede leer el RSS actual desde `/proc`. Las capacidades
ausentes aparecen como `unavailable` con summaries nulos, nunca como cero.
`--require-memory` aborta con código de salida 3 cuando no existe ningún
mecanismo en el host.

## Metadatos capturados

Cada JSON de resultado identifica su máquina con:

| Metadato | Fuente |
|---|---|
| Versión, implementación y ejecutable de Python | Biblioteca estándar |
| Versión de Lucis | Metadatos del paquete |
| Sistema, release, plataforma y arquitectura | Biblioteca estándar |
| Modelo de CPU | `/proc/cpuinfo`, `PROCESSOR_IDENTIFIER` o `sysctl` |
| CPU lógicas | `os.cpu_count()` |
| RAM total en bytes | `psutil`, `/proc/meminfo`, `GlobalMemoryStatusEx` o `sysctl` |
| Versión de `psutil` | Metadatos del paquete, cuando está instalado |
| Mecanismos de memoria utilizables | Detectados en tiempo de ejecución |
| Resolución de `perf_counter` | `time.get_clock_info` |
| Commit de Git y estado del árbol | `git`, best effort |
| Timestamps UTC y configuración completa | El propio runner |
| Hashes SHA-256 de dataset y consultas | El contrato de referencia congelado |

Cada colector es best effort: una capacidad ausente se guarda como `null`,
nunca como cero.

## Resultados, validación y reportes

Por defecto, los resultados JSON con timestamp se escriben en
`benchmarks/results/`, ignorado por Git:

```bash
python -m benchmarks run --profile small
```

Usa otro directorio de salida si lo prefieres:

```bash
python -m benchmarks run --profile small --output /tmp/lucis-results
```

Valida el contrato completo del resultado:

```bash
python -m benchmarks validate benchmarks/results/<run>.json
```

`validate` va mucho más allá de la estructura: comprueba los timestamps, los
hashes congelados de dataset y consultas, que cada summary sea exactamente
consistente con sus muestras raw, que la memoria no disponible sea nula en
lugar de cero, que cada motor solicitado haya producido la matriz completa de
métricas y que cada backend haya verificado las 17 consultas round-trip. Un
JSON alterado o incompleto se rechaza con código de salida 4 y un mensaje
accionable.

Crea un reporte Markdown legible junto al JSON:

```bash
python -m benchmarks report benchmarks/results/<run>.json
```

Ningún comando sobrescribe un resultado o reporte existente.

## Campaña publicada de Lucis 0.1.0

El repositorio incluye una campaña completa ejecutada en Fedora, Ubuntu,
Windows 11 y macOS. Contiene los perfiles `tiny`, `small`, `medium` y `large`
para Core y Lite: 16 resultados JSON, todos validados contra el schema 1.0 y
con fidelidad round-trip confirmada para las 17 consultas en JSON, SQLite y
`mmap`.

La campaña está archivada con sus datos originales, reportes individuales,
resumen editorial y presentación en
[`docs/benchmarks`](../benchmarks/README.md). Para conocer las conclusiones y
las salvedades antes de citar cifras, consulta el
[resumen en español](../benchmarks/reports/summary.es.md).

Los resultados se obtuvieron en el commit `a6ac3de8` de Lucis 0.1.0. Cada
perfil tiene una sola ejecución por equipo; además, cambian CPU, versión de
Python y sistema operativo. Por eso Core y Lite sí se comparan dentro de una
misma ejecución, pero las cifras entre equipos no forman un ranking de
sistemas operativos. La ejecución de macOS queda marcada como exploratoria
porque registró `git_dirty: true` y no contó con `psutil`.

## Agregar varias ejecuciones

Combina ejecuciones oficiales compatibles sin transcribir cifras:

```bash
python -m benchmarks aggregate benchmarks/results/*.json --output summary.md
```

Esto escribe `summary.md` más un `summary.aggregate.json` trazable. El
agregador primero valida cada archivo en profundidad y después se niega a
mezclar ejecuciones que difieran en versión de schema, versión de Lucis,
commit, versión menor de Python, perfil, hash de dataset, hash de consultas,
motores, warm-ups, repeticiones o requisito de memoria. Las ejecuciones de
sistemas operativos o máquinas distintos se reportan como grupos separados,
nunca fusionados.

Para cada métrica, el resumen publica la mediana de las medianas por
ejecución, el mínimo y el máximo de esas medianas como rango de variabilidad,
la mediana de los p95 por ejecución, el número de ejecuciones y los run IDs
de origen. Nada se descarta como outlier; una variabilidad superior al 20% se
lista como advertencia para revisión manual, junto con ejecuciones con árbol
sucio y metadatos faltantes.

## Comparar ejecuciones con responsabilidad

Para una comparación local útil:

1. Usa el mismo commit, versión de Python, perfil, warm-ups y repeticiones.
2. Cierra aplicaciones intensivas en CPU o disco.
3. Mantén las mismas condiciones de energía y temperatura.
4. Compara Core y Lite de la misma invocación.
5. Repite el comando completo y compara medianas agregadas, no solo el
   resultado más rápido.
6. Trata un resultado con `git_dirty: true` como exploratorio.

El tiempo varía con la planificación de CPU, la caché del sistema de
archivos, la versión del intérprete, el almacenamiento y la carga en segundo
plano. Los hashes de dataset y consultas establecen entradas idénticas, no un
estado idéntico de la máquina.

## Limitaciones actuales

- El corpus es sintético y léxico; no representa todos los idiomas ni
  distribuciones de producción.
- Ningún perfil supera los 100,000 documentos en esta release.
- No hay ground truth de relevancia, concurrencia, throughput, sharding,
  worker ni comparación con proyectos externos.
- Las cargas son process-cold por backend, pero la caché de páginas del
  sistema operativo no se controla.
- Las operaciones de construcción, guardado y carga tienen una muestra por
  invocación; agrega varias ejecuciones para cifras de campaña.
- El RSS suma páginas compartidas y puede sobreestimar la memoria exclusiva;
  el muestreo puede perder procesos auxiliares de vida corta.
- El preflight multiplataforma se sigue por separado de este documento.

Para la referencia corta orientada al runner, consulta
[`benchmarks/README.md`](../../benchmarks/README.md).

## Siguiente paso

- [Pruebas](16-pruebas.md) — Ejecutar la suite de validación del proyecto
- [Motores de búsqueda](04-motores.md) — Entender los algoritmos Core y Lite
