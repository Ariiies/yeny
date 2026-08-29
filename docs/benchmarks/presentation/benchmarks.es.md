---
marp: true
theme: default
paginate: true
title: Lucis 0.1.0 — Benchmarks multiplataforma
description: Resultados reproducibles en Fedora, Ubuntu, Windows y macOS
---

<!-- _class: lead -->

# Lucis 0.1.0

## Benchmarks multiplataforma

Core · Lite · JSON · SQLite · `.lcs`/`mmap`

16 ejecuciones validadas · 4 sistemas · hasta 100,000 documentos

---

# Qué queríamos demostrar

- Que la suite se ejecuta de forma reproducible en Linux, Windows y macOS.
- Cómo escalan Core y Lite con el mismo corpus, consultas y tokenizer.
- Qué costo tienen construcción, búsqueda, persistencia y carga.
- Que JSON, SQLite y `mmap` conservan IDs, ranking y scores.

No medimos relevancia, recall, concurrencia ni productos externos.

---

# Cobertura completa

| | tiny | small | medium | large |
|---|---:|---:|---:|---:|
| Documentos | 100 | 1,000 | 10,000 | 100,000 |
| Fedora | ✓ | ✓ | ✓ | ✓ |
| Ubuntu | ✓ | ✓ | ✓ | ✓ |
| Windows 11 | ✓ | ✓ | ✓ | ✓ |
| macOS | ✓ | ✓ | ✓ | ✓ |

Cada ejecución incluye Core, Lite, JSON, SQLite y `.lcs`/`mmap`.

---

# Contrato reproducible

- Lucis 0.1.0, commit `a6ac3de8`.
- Seed `20260117` y hashes SHA-256 congelados.
- 17 consultas deterministas.
- 3 warm-ups y 10 repeticiones.
- Procesos fríos separados para construcción y cada backend de carga.
- Mismo `word_tokenizer` para comparar Core y Lite justamente.

**Resultado:** 16/16 JSON válidos y 1,632 verificaciones
backend-consulta satisfactorias.

---

# Perfil large: construcción

| Plataforma | Core | Lite | Reducción con Lite |
|---|---:|---:|---:|
| Fedora | 4.15 s | 1.50 s | 63.8% |
| Ubuntu | 4.88 s | 3.13 s | 35.9% |
| Windows | 4.30 s | 2.15 s | 50.0% |
| macOS* | 1.17 s | 0.77 s | 33.8% |

Lite construyó más rápido en los cuatro equipos bajo la configuración léxica
controlada.

---

# Perfil large: búsqueda común calentada

| Plataforma | Core mediana / p95 | Lite mediana / p95 |
|---|---:|---:|
| Fedora | 127.09 / 149.50 ms | 72.32 / 87.81 ms |
| Ubuntu | 229.97 / 317.10 ms | 130.26 / 221.87 ms |
| Windows | 229.87 / 268.71 ms | 114.28 / 145.67 ms |
| macOS* | 75.04 / 93.00 ms | 48.69 / 59.90 ms |

Lite redujo la mediana entre 35.1% y 50.3% dentro de cada máquina.

---

# Persistencia: la señal más clara

Para 100,000 documentos:

- `.lcs`: 20.78 MiB Core y 20.01 MiB Lite.
- 66–68% menos espacio que JSON.
- Carga `mmap`: 2.44–31.88 ms en la matriz.
- Entre 36× y 453× menos tiempo de carga que JSON.
- 17/17 consultas fieles en JSON, SQLite y `mmap`.

`mmap` optimiza arranque y tamaño; no promete menor latencia para todas las
búsquedas.

---

# Memoria

En `large`, para los tres sistemas con `psutil`:

| Fase | Delta de RSS pico observado |
|---|---:|
| Construcción | 366–925 MiB |
| Carga `mmap` | 102–127 MiB |

Estas cifras abarcan la fase y el árbol de procesos. No representan memoria
exclusiva del índice. macOS solo tuvo `resource`, por lo que sus valores
comparables quedan como no disponibles.

---

# Cómo leer la comparación

Los equipos no son equivalentes:

- CPUs distintas: Ryzen 7, i7-7500U, AMD64 Family 25 y Apple M4.
- Python 3.11, 3.13 y 3.14.
- Una ejecución por plataforma y perfil.
- El caché de páginas del sistema no fue controlado.
- macOS registró `git_dirty: true`.

**Sí:** Core vs Lite dentro de la misma ejecución.  
**No:** ranking de sistemas operativos o promesa universal.

---

<!-- _class: lead -->

# Conclusión

Lucis 0.1.0 queda respaldado por una campaña reproducible y auditable en
cuatro sistemas.

**Lite** prioriza costo temporal.  
**Core** conserva TF-IDF/coseno.  
**`.lcs` + `mmap`** es la ruta recomendada para arranque y tamaño.

Datos, reportes y metodología: `docs/benchmarks/`
