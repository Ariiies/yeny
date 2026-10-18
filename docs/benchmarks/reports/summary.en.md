# Yeny 0.1.0 benchmark results

Status: complete campaign, 16/16 results validated  
Measured commit: `a6ac3de8cf7ca5fdc1e1a07ec539e67660fea61f`  
Profiles: 100, 1,000, 10,000, and 100,000 documents  
Configuration: 3 warm-ups, 10 repetitions, Core and Lite

## Executive summary

Yeny completed the planned matrix on Fedora, Ubuntu, Windows 11, and macOS.
All 16 files satisfy schema 1.0, and every engine/backend combination
preserved the 17 expected results, their order, and their scores: 1,632
successful backend-query checks in total.

At 100,000 documents, `LiteEngine` built the index 33.8% to 63.8% faster than
`CoreEngine` on the same machine. For warmed common queries, Lite reduced the
median by 35.1% to 50.3%. This is a speed comparison under the shared
`word_tokenizer`; it is not a relevance measurement or a comparison of both
engines' native defaults.

The `.yny` format remained near 20 MiB on every platform and was about 66–68%
smaller than JSON. Loading through `mmap` was 36 to 453 times faster than JSON
loading in these runs. That ratio describes loading only, does not guarantee
that every mapped search is faster, and the operating-system page cache was
not controlled.

## Measured environments

| Platform | CPU | Logical CPUs | RAM | Python | Memory | Git state |
|---|---|---:|---:|---|---|---|
| Fedora 44 | AMD Ryzen 7 7730U | 16 | 15.0 GiB | 3.14.6 | `psutil` | clean |
| Ubuntu | Intel Core i7-7500U | 4 | 15.5 GiB | 3.11.14 | `psutil` | clean |
| Windows 11 | AMD64 Family 25 Model 80 | 16 | 15.3 GiB | 3.13.0 | `psutil` | clean |
| macOS | Apple M4 | 10 | 16.0 GiB | 3.13.2 | `resource` | **dirty** |

Differences between rows combine hardware, Python, and operating system. The
defensible comparison is Core versus Lite within one row, not a platform
ranking.

## Large profile: 100,000 documents

| Platform | Engine | Build | Warm common median / p95 | JSON load | `mmap` load | `.yny` |
|---|---|---:|---:|---:|---:|---:|
| Fedora | Core | 4.15 s | 127.09 / 149.50 ms | 1.20 s | 13.48 ms | 20.78 MiB |
| Fedora | Lite | 1.50 s | 72.32 / 87.81 ms | 1.11 s | 2.44 ms | 20.01 MiB |
| Ubuntu | Core | 4.88 s | 229.97 / 317.10 ms | 2.71 s | 31.88 ms | 20.78 MiB |
| Ubuntu | Lite | 3.13 s | 130.26 / 221.87 ms | 2.43 s | 20.87 ms | 20.01 MiB |
| Windows | Core | 4.30 s | 229.87 / 268.71 ms | 1.97 s | 29.90 ms | 20.78 MiB |
| Windows | Lite | 2.15 s | 114.28 / 145.67 ms | 1.85 s | 15.12 ms | 20.01 MiB |
| macOS* | Core | 1.17 s | 75.04 / 93.00 ms | 0.62 s | 17.12 ms | 20.78 MiB |
| macOS* | Lite | 0.77 s | 48.69 / 59.90 ms | 0.77 s | 10.57 ms | 20.01 MiB |

\* macOS is exploratory because it recorded `git_dirty: true`.

## Main conclusions

1. The suite runs and produces valid output on all four tested operating
   system families.
2. Lite has the lower time cost under this controlled lexical setup; Core
   retains its TF-IDF/cosine model and should not be judged on speed alone.
3. `.yny` + `mmap` is the preferred path when startup time and artifact size
   matter, while mapped search can have different runtime costs.
4. Persistence fidelity holds throughout the measured matrix.

## Citation limits

- There is one run per platform and profile. Single-sample operations have no
  variability estimate.
- Machines use different CPUs and Python versions.
- The operating-system page cache was not flushed.
- The corpus is synthetic and does not measure quality, recall, or concurrency.
- macOS used a dirty tree and had no `psutil`; its timings are exploratory and
  it is not an official memory control.
- Cite the measured commit `a6ac3de8` and Yeny 0.1.0 with these results.

## Evidence

Original JSON files are under [`../raw`](../raw), and all 16 complete reports
are under [`individual`](individual). See the
[benchmark guide](../../en/17-benchmarks.md) for methodology, measurement
boundaries, and reproduction commands.
