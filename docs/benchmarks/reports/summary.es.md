# Resultados de benchmarks de Yeny 0.1.0

Estado: campaña completa, 16/16 resultados validados  
Commit medido: `a6ac3de8cf7ca5fdc1e1a07ec539e67660fea61f`  
Perfiles: 100, 1,000, 10,000 y 100,000 documentos  
Configuración: 3 warm-ups, 10 repeticiones, Core y Lite

## Resumen ejecutivo

Yeny completó la matriz prevista en Fedora, Ubuntu, Windows 11 y macOS. Los
16 archivos cumplen el schema 1.0 y cada combinación de motor y backend
conservó los 17 resultados esperados, su orden y sus scores. En total son
1,632 verificaciones backend-consulta satisfactorias.

En el perfil de 100,000 documentos, `LiteEngine` construyó el índice entre
33.8% y 63.8% más rápido que `CoreEngine` dentro de la misma máquina. Para las
consultas comunes calentadas, Lite redujo la mediana entre 35.1% y 50.3%.
Esto mide velocidad con el mismo `word_tokenizer`; no mide relevancia ni
compara los valores predeterminados nativos de ambos motores.

El formato `.yny` ocupó cerca de 20 MiB en todas las plataformas y redujo el
tamaño aproximadamente 66–68% frente a JSON. La carga mediante `mmap` fue de
36 a 453 veces más rápida que la carga JSON en estas ejecuciones. Esa cifra
describe el tiempo de carga, no garantiza que todas las búsquedas sobre
`mmap` sean más rápidas, y el caché de páginas del sistema operativo no fue
controlado.

## Entornos medidos

| Plataforma | CPU | CPU lógicas | RAM | Python | Memoria | Estado Git |
|---|---|---:|---:|---|---|---|
| Fedora 44 | AMD Ryzen 7 7730U | 16 | 15.0 GiB | 3.14.6 | `psutil` | limpio |
| Ubuntu | Intel Core i7-7500U | 4 | 15.5 GiB | 3.11.14 | `psutil` | limpio |
| Windows 11 | AMD64 Family 25 Model 80 | 16 | 15.3 GiB | 3.13.0 | `psutil` | limpio |
| macOS | Apple M4 | 10 | 16.0 GiB | 3.13.2 | `resource` | **sucio** |

Las diferencias entre filas mezclan hardware, Python y sistema operativo. La
comparación defendible es Core contra Lite dentro de la misma fila, no un
ranking de plataformas.

## Perfil large: 100,000 documentos

| Plataforma | Motor | Construcción | Búsqueda común mediana / p95 | Carga JSON | Carga `mmap` | `.yny` |
|---|---|---:|---:|---:|---:|---:|
| Fedora | Core | 4.15 s | 127.09 / 149.50 ms | 1.20 s | 13.48 ms | 20.78 MiB |
| Fedora | Lite | 1.50 s | 72.32 / 87.81 ms | 1.11 s | 2.44 ms | 20.01 MiB |
| Ubuntu | Core | 4.88 s | 229.97 / 317.10 ms | 2.71 s | 31.88 ms | 20.78 MiB |
| Ubuntu | Lite | 3.13 s | 130.26 / 221.87 ms | 2.43 s | 20.87 ms | 20.01 MiB |
| Windows | Core | 4.30 s | 229.87 / 268.71 ms | 1.97 s | 29.90 ms | 20.78 MiB |
| Windows | Lite | 2.15 s | 114.28 / 145.67 ms | 1.85 s | 15.12 ms | 20.01 MiB |
| macOS* | Core | 1.17 s | 75.04 / 93.00 ms | 0.62 s | 17.12 ms | 20.78 MiB |
| macOS* | Lite | 0.77 s | 48.69 / 59.90 ms | 0.77 s | 10.57 ms | 20.01 MiB |

\* macOS es exploratorio por `git_dirty: true`.

## Escalado de construcción

| Plataforma | Motor | tiny | small | medium | large |
|---|---|---:|---:|---:|---:|
| Fedora | Core | 0.005 s | 0.039 s | 0.377 s | 4.147 s |
| Fedora | Lite | 0.004 s | 0.029 s | 0.141 s | 1.502 s |
| Ubuntu | Core | 0.004 s | 0.060 s | 0.415 s | 4.880 s |
| Ubuntu | Lite | 0.003 s | 0.038 s | 0.319 s | 3.128 s |
| Windows | Core | 0.005 s | 0.038 s | 0.417 s | 4.297 s |
| Windows | Lite | 0.004 s | 0.026 s | 0.214 s | 2.148 s |
| macOS* | Core | 0.001 s | 0.011 s | 0.106 s | 1.170 s |
| macOS* | Lite | 0.001 s | 0.008 s | 0.075 s | 0.774 s |

El tiempo crece aproximadamente con el tamaño del corpus en esta matriz. No
se ajustó un modelo de complejidad porque cada operación de construcción tiene
una sola muestra por perfil.

## Memoria y persistencia

En el perfil `large`, el delta de RSS pico de la fase de construcción fue de
366 a 925 MiB en los tres equipos con `psutil`. La fase de carga `mmap` quedó
entre 102 y 127 MiB. Son lecturas del proceso o árbol de procesos, no memoria
exclusiva del índice; las páginas compartidas y la resolución de muestreo
pueden alterar el valor.

Los artefactos `.yny` son idénticos en tamaño entre sistemas para un mismo
motor porque el corpus y la configuración son deterministas: 20.78 MiB para
Core y 20.01 MiB para Lite en `large`. Todos los round-trips JSON, SQLite y
`mmap` conservaron IDs, orden y scores.

## Conclusiones publicables

1. La suite funciona y produce resultados válidos en las cuatro familias de
   sistema operativo probadas.
2. Lite ofrece el mejor costo temporal en esta configuración léxica
   controlada; Core conserva su modelo TF-IDF/coseno y no debe evaluarse solo
   por velocidad.
3. `.yny` + `mmap` es la vía recomendada cuando importan arranque y tamaño de
   artefacto, aceptando que el patrón de búsqueda mapeada puede tener otros
   costos.
4. La persistencia es fiel en toda la matriz medida.

## Límites para citar estos datos

- Hay una ejecución por plataforma y perfil. Las operaciones con una sola
  muestra no tienen una estimación de variabilidad.
- Los equipos usan CPU y versiones de Python diferentes.
- El caché de páginas del sistema operativo no se limpió.
- El corpus es sintético y no mide calidad, recall ni concurrencia.
- macOS registró un árbol Git sucio y no tuvo `psutil`; sus tiempos son útiles
  como exploración, pero no como control oficial de memoria.
- El repositorio actual puede avanzar después del commit medido; al citar la
  campaña debe mantenerse la referencia a `a6ac3de8` y Yeny 0.1.0.

## Evidencia

Los JSON originales están en [`../raw`](../raw) y los 16 reportes completos en
[`individual`](individual). La metodología, fronteras de medición y comandos
de reproducción están en la
[guía de benchmarks](../../es/17-benchmarks.md).
