# Benchmarks

Lucis incluye una suite pequeña y determinista de benchmarks para responder
preguntas prácticas sobre sus dos motores públicos:

- ¿Cuánto tarda en construirse un índice?
- ¿Cuánto tardan distintos tipos de búsqueda?
- ¿Cuánto tardan las operaciones de persistencia JSON, SQLite y `.lcs`?
- ¿Cuánto espacio ocupan los artefactos generados?
- ¿Qué ocurre al cargar un índice de forma normal o mediante `mmap`?
- ¿La persistencia conserva los mismos IDs de documentos en los resultados?
- ¿Cuánta memoria RSS se observa durante cada fase del worker?

La suite **no** mide relevancia, exactitud, recall, throughput concurrente ni
rendimiento frente a otros proyectos de búsqueda.

## Inicio rápido

Ejecuta los comandos desde un clon local del repositorio de Lucis:

```bash
python -m pip install -e .
python -m benchmarks run --profile tiny
```

La suite estándar no necesita dependencias obligatorias de benchmark. Para
muestrear el RSS del árbol de procesos, instala el extra opcional:

```bash
python -m pip install -e ".[benchmark]"
python -m benchmarks run --profile tiny --require-memory
```

El comando predeterminado ejecuta ambos motores. Puedes elegir un motor u otro
perfil:

```bash
python -m benchmarks run --profile small --engine core
python -m benchmarks run --profile medium --engine lite
python -m benchmarks run --profile small --warmups 5 --repetitions 20
```

`tiny` es la prueba de humo, `small` es la comparación local rápida más útil y
`medium` permite revisar el escalado.

## Perfiles reproducibles

| Perfil | Documentos | Vocabulario | Longitud del documento |
|---|---:|---:|---:|
| `tiny` | 100 | 2,048 términos | 12–52 tokens |
| `small` | 1,000 | 2,048 términos | 12–52 tokens |
| `medium` | 10,000 | 2,048 términos | 12–52 tokens |

Todos los perfiles usan:

- seed `20260117`;
- generador `lexical_zipf_v1`;
- distribución de términos tipo Zipf con exponente `1.07`;
- distribución triangular de longitud con moda de 32 tokens;
- 2% de documentos duplicados intencionalmente;
- 17 consultas deterministas: 4 comunes, 4 raras, 4 de varios tokens, 4 sin
  resultados y 1 consulta repetida.

El resultado guarda hashes SHA-256 del dataset y de las consultas. Estos
hashes demuestran que dos ejecuciones recibieron entradas generadas idénticas;
no significan que el tiempo medido deba ser idéntico.

## Una comparación justa entre Core y Lite

`CoreEngine` usa TF-IDF y similitud coseno. `LiteEngine` usa frecuencia de
término normalizada. Su comportamiento de ranking es distinto, pero ambos son
motores Python puro expuestos por la misma fachada `Lucis`.

Para comparar tiempos justamente, el benchmark entrega a ambos el mismo
corpus, consultas, `top_k=10` y `word_tokenizer`. Esto es importante porque
`LiteEngine` utiliza trigramas de caracteres de forma predeterminada. Usar un
tokenizer diferente por motor mezclaría el costo del motor con diferencias de
tokenización y tamaño del índice.

Por lo tanto, estos números comparan las dos implementaciones de ranking bajo
una configuración léxica controlada. No comparan sus configuraciones nativas
ni determinan cuál produce resultados más relevantes.

## Cómo interpretar los números

La tabla siguiente corresponde a una **ejecución auditada ilustrativa**, no a
un baseline publicado ni a una garantía de rendimiento. Su objetivo es mostrar
la escala y las unidades que un usuario encontrará en el reporte.

La ejecución `20260729T230354Z-518467` usó Lucis 0.1.0, CPython 3.13.5, Linux
x86_64, 4 CPU lógicas y el perfil `small`. El árbol de trabajo tenía cambios
sin commit, por lo que este resultado no debe usarse como cifra oficial del
release.

| Medición | Core | Lite | Muestras |
|---|---:|---:|---:|
| Construcción del índice | 52.78 ms | 37.29 ms | 1 por motor |
| Construcción más persistencia JSON automática | 94.45 ms | 89.13 ms | 1 por motor |
| Búsqueda común calentada, mediana / p95 | 2.72 / 4.43 ms | 1.71 / 2.11 ms | 40 por motor |
| Búsqueda rara calentada, mediana / p95 | 22.29 / 41.05 µs | 8.20 / 9.41 µs | 40 por motor |
| Carga JSON | 39.81 ms | 21.31 ms | 1 por motor |
| Carga con `mmap` | 2.70 ms | 3.45 ms | 1 por motor |
| Artefacto `.lcs` | 354.05 KiB | 346.24 KiB | 1 por motor |
| Pico RSS del árbol durante construcción | 77.91 MiB | 77.40 MiB | 1 muestra de fase |
| Conjuntos de IDs conservados | 17/17 en 3 backends | 17/17 en 3 backends | JSON, SQLite, mmap |

En esta ejecución concreta, Lite tardó menos al construir el índice y en las
dos categorías de búsqueda calentada mostradas, mientras Core tuvo la carga
única de `mmap` más corta. Los archivos `.lcs` difirieron en unos 8 KiB y los
picos RSS de todo el worker de construcción fueron casi iguales. Es un buen
ejemplo de por qué una ejecución debe leerse como un conjunto de compromisos y
no como un único “ganador”.

Las mediciones de construcción, guardado, carga y tamaño tienen actualmente
una muestra por ejecución. Por eso su mediana y p95 mostrados son el mismo
valor. Las categorías de búsqueda contienen 40 muestras y la consulta repetida
contiene 100; en esos casos la mediana y el p95 sí son informativos. Repite el
comando completo para comparar operaciones de una sola muestra.

## Métricas

| Métrica | Límite medido |
|---|---|
| `dataset_generation` | Solo la generación determinista del corpus |
| `index_build` | `Lucis.index(..., persist=False)` |
| `index_e2e_json` | Construcción mediante `Lucis.from_dict`, incluida la persistencia JSON automática |
| `search_first` | Primera llamada pública a `Lucis.search` después de construir |
| `search_warm` | Búsquedas públicas después del calentamiento, agrupadas por categoría |
| `json_save`, `sqlite_save` | Método público `Lucis.save` |
| `*_artifact_size` | Bytes reales escritos en disco |
| `lcs_write` | Serialización `.lcs` del motor |
| `load_standard` | Constructor `Lucis` con autoload para JSON o SQLite |
| `mmap_load` | Operación `load_mmap` del motor |
| `search_first_*`, `search_warm_*` | Búsqueda pública después de carga normal o mapeada |
| `roundtrip_verified` | Consultas que conservan los mismos IDs ordenados |
| `memory_*` | Observaciones RSS de toda la fase de construcción o carga |

El tiempo de búsqueda incluye el preprocesamiento de la consulta y la
construcción de la respuesta porque el timer rodea la llamada pública
`Lucis.search`.

La verificación round-trip comprueba el conjunto de IDs principales después
de cargar mediante JSON, SQLite y `mmap`. Actualmente no compara el orden del
ranking ni los scores de punto flotante.

## Modelo de procesos y memoria

Core y Lite se ejecutan por separado. Cada motor recibe:

1. Un proceso de construcción que genera datos, construye, busca y escribe
   todos los artefactos de persistencia.
2. Un proceso nuevo de carga que mide JSON, SQLite y `mmap` secuencialmente.
3. Un workspace temporal único que se elimina al terminar el motor.

El segundo proceso evita que los objetos Python de construcción contaminen las
mediciones de carga. Sin embargo, cada backend no recibe su propio intérprete
nuevo y la caché de páginas del sistema operativo no se vacía ni controla.

Cuando `psutil` está instalado, el proceso padre muestrea todo el árbol del
worker cada 5 ms. Reporta RSS inicial, RSS pico, delta del pico, RSS propio al
final de la fase después de recolección de basura y máximo de procesos. RSS no
representa propiedad exclusiva: las páginas copy-on-write de procesos
bifurcados pueden contarse más de una vez, pueden perderse picos muy breves, el
allocator puede conservar arenas y todavía puede haber referencias vivas al
final de la fase.

Sin `psutil`, Unix puede degradar al RSS pico del propio proceso mediante
`resource`; Linux también puede leer el RSS propio actual desde `/proc`. Las
capacidades ausentes aparecen como `unavailable` con summaries nulos, nunca
como cero.

## Resultados, validación y reportes

De forma predeterminada, los resultados JSON con timestamp se escriben en
`benchmarks/results/`, carpeta ignorada por Git:

```bash
python -m benchmarks run --profile small
```

También puedes indicar otro directorio:

```bash
python -m benchmarks run --profile small --output /tmp/lucis-results
```

Valida el contrato estructural interno:

```bash
python -m benchmarks validate benchmarks/results/<run>.json
```

Crea un reporte Markdown legible junto al JSON:

```bash
python -m benchmarks report benchmarks/results/<run>.json
```

Ningún comando sobrescribe un resultado o reporte existente. `validate`
comprueba el contrato estructural de nivel superior de la suite; no es una
certificación semántica completa de cada medición.

## Comparar ejecuciones responsablemente

Para obtener una comparación local útil:

1. Usa el mismo commit, versión de Python, perfil, calentamientos y
   repeticiones.
2. Cierra aplicaciones ajenas que usen intensivamente CPU o disco.
3. Mantén las mismas condiciones de energía y temperatura.
4. Compara Core y Lite dentro de la misma invocación.
5. Repite el comando completo y compara medianas y p95, no solo el mejor
   resultado.
6. Considera exploratorio cualquier resultado con `git_dirty: true`.

Los tiempos varían por planificación de CPU, caché del filesystem, versión del
intérprete, almacenamiento y carga en segundo plano. Los hashes de dataset y
consultas demuestran entradas idénticas, no un estado idéntico de la máquina.

## Limitaciones actuales

- El corpus es sintético y léxico; no representa todos los idiomas ni todas
  las distribuciones de producción.
- Solo `tiny`, `small` y `medium` son perfiles estables.
- No existe ground truth de relevancia ni se miden concurrencia, throughput,
  sharding, workers o proyectos externos.
- Las cargas de los backends comparten un proceso de carga y una caché de
  sistema operativo no controlada.
- Las operaciones de construcción, guardado y carga tienen un solo tiempo por
  invocación.
- El round-trip comprueba IDs, no el orden del ranking ni los scores.
- Los metadatos del entorno guardan plataforma, CPU lógicas, Python, Lucis y
  Git, pero todavía no guardan la RAM total del sistema; la descripción del CPU
  puede ser genérica en algunas plataformas.
- El progreso en vivo se informa por motor, no por cada escenario interno del
  benchmark.
- La auditoría actual validó Linux localmente: pasaron las 100 pruebas de
  benchmarks y las 386 pruebas totales del repositorio. La validación
  multiplataforma sigue pendiente.

Para una referencia breve orientada al runner, consulta
[`benchmarks/README.md`](../../benchmarks/README.md).

## Siguiente paso

- [Pruebas](16-pruebas.md) — Ejecutar la suite de validación del proyecto
- [Motores de búsqueda](04-motores.md) — Entender los algoritmos Core y Lite
