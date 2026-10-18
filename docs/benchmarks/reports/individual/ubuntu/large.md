# Yeny benchmark report

> These results describe one machine and one execution environment. They
> are not search-quality measurements or universal performance guarantees.

## Run

| Field | Value |
|---|---|
| Run ID | 20260730T212800Z-6dd988 |
| Started (UTC) | 2026-07-30T21:28:00.365861+00:00 |
| Finished (UTC) | 2026-07-30T21:36:17.305409+00:00 |
| Schema version | 1.0 |

## Environment

| Field | Value |
|---|---|
| python_version | 3.11.14 |
| python_implementation | CPython |
| platform | Linux-7.0.0-28-generic-x86_64-with-glibc2.39 |
| machine | x86_64 |
| yeny_version | 0.1.0 |
| cpu_model | Intel(R) Core(TM) i7-7500U CPU @ 2.70GHz |
| logical_cpu_count | 4 |
| total_ram_bytes | 16614010880 (15.47 GiB) |
| memory_mechanisms | psutil, resource, proc |
| psutil_version | 7.2.2 |
| git_commit | a6ac3de8cf7ca5fdc1e1a07ec539e67660fea61f |
| git_dirty | False |

## Configuration

| Field | Value |
|---|---|
| profile | large |
| engines | ['core', 'lite'] |
| warmups | 3 |
| repetitions | 10 |
| require_memory | True |

## Dataset and queries

| Field | Value |
|---|---|
| profile | large |
| generator_version | lexical_zipf_v1 |
| seed | 20260117 |
| documents | 100000 |
| total_tokens | 3204543 |
| vocabulary_nominal | 2048 |
| vocabulary_observed | 2048 |
| intentional_duplicates | 2000 |
| sha256 | 1d8d248c3c04004cb979f71b32c69fa02210c88b2c60fc4bab2ed75db1b5c0b4 |

| Field | Value |
|---|---|
| query_set_version | queries_v1 |
| query_count | 17 |
| queries_sha256 | cf5fa3f7f016f713af8122c52b795c5d845496c9a72d11d72e62e8f063b3fb37 |

## Construction and search after build

| Engine | Metric | Backend | Category | Median | p95 | Samples |
|---|---|---|---|---|---|---|
| core | dataset_generation | - | - | 2.68 s | 2.68 s | 1 |
| core | index_build | - | - | 4.88 s | 4.88 s | 1 |
| core | index_e2e_json | - | - | 8.89 s | 8.89 s | 1 |
| core | search_first | - | common | 231.78 ms | 231.78 ms | 1 |
| core | search_warm | - | common | 229.97 ms | 317.10 ms | 40 |
| core | search_warm | - | rare | 520.15 µs | 617.04 µs | 40 |
| core | search_warm | - | multi | 240.80 ms | 344.91 ms | 40 |
| core | search_warm | - | no_result | 3.97 µs | 4.27 µs | 40 |
| core | search_warm | - | repeated | 249.57 ms | 369.28 ms | 100 |
| lite | dataset_generation | - | - | 1.74 s | 1.74 s | 1 |
| lite | index_build | - | - | 3.13 s | 3.13 s | 1 |
| lite | index_e2e_json | - | - | 6.71 s | 6.71 s | 1 |
| lite | search_first | - | common | 141.65 ms | 141.65 ms | 1 |
| lite | search_warm | - | common | 130.26 ms | 221.87 ms | 40 |
| lite | search_warm | - | rare | 121.57 µs | 128.52 µs | 40 |
| lite | search_warm | - | multi | 162.58 ms | 286.90 ms | 40 |
| lite | search_warm | - | no_result | 3.74 µs | 4.01 µs | 40 |
| lite | search_warm | - | repeated | 156.50 ms | 237.02 ms | 100 |

## Persistence

| Engine | Metric | Backend | Category | Median | p95 | Samples |
|---|---|---|---|---|---|---|
| core | json_save | - | - | 3.92 s | 3.92 s | 1 |
| core | json_artifact_size | - | - | 62.65 MiB | 62.65 MiB | 1 |
| core | sqlite_save | - | - | 1.51 s | 1.51 s | 1 |
| core | sqlite_artifact_size | - | - | 46.55 MiB | 46.55 MiB | 1 |
| core | yny_write | - | - | 126.64 ms | 126.64 ms | 1 |
| core | yny_artifact_size | - | - | 20.78 MiB | 20.78 MiB | 1 |
| lite | json_save | - | - | 3.40 s | 3.40 s | 1 |
| lite | json_artifact_size | - | - | 59.15 MiB | 59.15 MiB | 1 |
| lite | sqlite_save | - | - | 2.95 s | 2.95 s | 1 |
| lite | sqlite_artifact_size | - | - | 46.55 MiB | 46.55 MiB | 1 |
| lite | yny_write | - | - | 86.63 ms | 86.63 ms | 1 |
| lite | yny_artifact_size | - | - | 20.01 MiB | 20.01 MiB | 1 |

## Standard loads

| Engine | Metric | Backend | Category | Median | p95 | Samples |
|---|---|---|---|---|---|---|
| core | load_standard | json | - | 2.71 s | 2.71 s | 1 |
| core | search_first_after_load | json | common | 324.63 ms | 324.63 ms | 1 |
| core | search_warm_after_load | json | common | 203.43 ms | 322.05 ms | 40 |
| core | search_warm_after_load | json | rare | 200.17 µs | 305.17 µs | 40 |
| core | search_warm_after_load | json | multi | 247.80 ms | 318.57 ms | 40 |
| core | search_warm_after_load | json | no_result | 3.96 µs | 4.17 µs | 40 |
| core | search_warm_after_load | json | repeated | 242.01 ms | 339.93 ms | 100 |
| core | load_standard | sqlite | - | 3.31 s | 3.31 s | 1 |
| core | search_first_after_load | sqlite | common | 215.03 ms | 215.03 ms | 1 |
| core | search_warm_after_load | sqlite | common | 251.30 ms | 340.82 ms | 40 |
| core | search_warm_after_load | sqlite | rare | 211.26 µs | 348.95 µs | 40 |
| core | search_warm_after_load | sqlite | multi | 256.08 ms | 366.64 ms | 40 |
| core | search_warm_after_load | sqlite | no_result | 4.05 µs | 5.14 µs | 40 |
| core | search_warm_after_load | sqlite | repeated | 266.00 ms | 375.57 ms | 100 |
| lite | load_standard | json | - | 2.43 s | 2.43 s | 1 |
| lite | search_first_after_load | json | common | 145.48 ms | 145.48 ms | 1 |
| lite | search_warm_after_load | json | common | 131.60 ms | 215.65 ms | 40 |
| lite | search_warm_after_load | json | rare | 120.24 µs | 347.67 µs | 40 |
| lite | search_warm_after_load | json | multi | 164.41 ms | 225.78 ms | 40 |
| lite | search_warm_after_load | json | no_result | 3.68 µs | 4.01 µs | 40 |
| lite | search_warm_after_load | json | repeated | 151.17 ms | 221.11 ms | 100 |
| lite | load_standard | sqlite | - | 1.85 s | 1.85 s | 1 |
| lite | search_first_after_load | sqlite | common | 153.48 ms | 153.48 ms | 1 |
| lite | search_warm_after_load | sqlite | common | 171.18 ms | 299.72 ms | 40 |
| lite | search_warm_after_load | sqlite | rare | 121.09 µs | 169.25 µs | 40 |
| lite | search_warm_after_load | sqlite | multi | 160.71 ms | 255.30 ms | 40 |
| lite | search_warm_after_load | sqlite | no_result | 3.70 µs | 4.10 µs | 40 |
| lite | search_warm_after_load | sqlite | repeated | 156.29 ms | 223.72 ms | 100 |

## Memory-mapped loads

| Engine | Metric | Backend | Category | Median | p95 | Samples |
|---|---|---|---|---|---|---|
| core | mmap_load | - | - | 31.88 ms | 31.88 ms | 1 |
| core | search_first_mmap | - | common | 397.71 ms | 397.71 ms | 1 |
| core | search_warm_mmap | - | common | 382.33 ms | 513.80 ms | 40 |
| core | search_warm_mmap | - | rare | 525.80 µs | 1.34 ms | 40 |
| core | search_warm_mmap | - | multi | 518.02 ms | 733.15 ms | 40 |
| core | search_warm_mmap | - | no_result | 9.14 µs | 15.07 µs | 40 |
| core | search_warm_mmap | - | repeated | 486.53 ms | 643.86 ms | 100 |
| lite | mmap_load | - | - | 20.87 ms | 20.87 ms | 1 |
| lite | search_first_mmap | - | common | 252.58 ms | 252.58 ms | 1 |
| lite | search_warm_mmap | - | common | 142.17 ms | 181.85 ms | 40 |
| lite | search_warm_mmap | - | rare | 458.82 µs | 499.90 µs | 40 |
| lite | search_warm_mmap | - | multi | 178.37 ms | 281.20 ms | 40 |
| lite | search_warm_mmap | - | no_result | 3.97 µs | 4.38 µs | 40 |
| lite | search_warm_mmap | - | repeated | 178.59 ms | 256.98 ms | 100 |

## Memory

RSS values are process readings, not exclusive ownership. `n/a` marks capabilities unavailable on this host; they are never reported as zero.

| Engine | Phase | Metric | Scope | Value | Status |
|---|---|---|---|---|---|
| core | build | memory_baseline_rss | process_tree | 7.54 MiB | ok |
| core | build | memory_peak_rss | process_tree | 932.86 MiB | ok |
| core | build | memory_peak_rss_delta | process_tree | 925.32 MiB | ok |
| core | build | memory_stable_rss | self_only | 265.52 MiB | ok |
| core | build | memory_max_processes | process_tree | 3 | ok |
| core | load_json | memory_baseline_rss | process_tree | 6.76 MiB | ok |
| core | load_json | memory_peak_rss | process_tree | 242.64 MiB | ok |
| core | load_json | memory_peak_rss_delta | process_tree | 235.89 MiB | ok |
| core | load_json | memory_stable_rss | self_only | 206.14 MiB | ok |
| core | load_json | memory_max_processes | process_tree | 1 | ok |
| core | load_sqlite | memory_baseline_rss | process_tree | 7.40 MiB | ok |
| core | load_sqlite | memory_peak_rss | process_tree | 322.61 MiB | ok |
| core | load_sqlite | memory_peak_rss_delta | process_tree | 315.21 MiB | ok |
| core | load_sqlite | memory_stable_rss | self_only | 242.24 MiB | ok |
| core | load_sqlite | memory_max_processes | process_tree | 1 | ok |
| core | load_mmap | memory_baseline_rss | process_tree | 6.72 MiB | ok |
| core | load_mmap | memory_peak_rss | process_tree | 121.88 MiB | ok |
| core | load_mmap | memory_peak_rss_delta | process_tree | 115.16 MiB | ok |
| core | load_mmap | memory_stable_rss | self_only | 111.56 MiB | ok |
| core | load_mmap | memory_max_processes | process_tree | 1 | ok |
| lite | build | memory_baseline_rss | process_tree | 6.81 MiB | ok |
| lite | build | memory_peak_rss | process_tree | 860.15 MiB | ok |
| lite | build | memory_peak_rss_delta | process_tree | 853.34 MiB | ok |
| lite | build | memory_stable_rss | self_only | 223.03 MiB | ok |
| lite | build | memory_max_processes | process_tree | 3 | ok |
| lite | load_json | memory_baseline_rss | process_tree | 6.86 MiB | ok |
| lite | load_json | memory_peak_rss | process_tree | 227.40 MiB | ok |
| lite | load_json | memory_peak_rss_delta | process_tree | 220.54 MiB | ok |
| lite | load_json | memory_stable_rss | self_only | 191.93 MiB | ok |
| lite | load_json | memory_max_processes | process_tree | 1 | ok |
| lite | load_sqlite | memory_baseline_rss | process_tree | 6.96 MiB | ok |
| lite | load_sqlite | memory_peak_rss | process_tree | 301.26 MiB | ok |
| lite | load_sqlite | memory_peak_rss_delta | process_tree | 294.30 MiB | ok |
| lite | load_sqlite | memory_stable_rss | self_only | 222.82 MiB | ok |
| lite | load_sqlite | memory_max_processes | process_tree | 1 | ok |
| lite | load_mmap | memory_baseline_rss | process_tree | 6.86 MiB | ok |
| lite | load_mmap | memory_peak_rss | process_tree | 121.30 MiB | ok |
| lite | load_mmap | memory_peak_rss_delta | process_tree | 114.45 MiB | ok |
| lite | load_mmap | memory_stable_rss | self_only | 105.43 MiB | ok |
| lite | load_mmap | memory_max_processes | process_tree | 1 | ok |

## Round-trip verification

Each loaded index returned the same documents, in the same ranking order, with the same scores as the freshly built index for every query.

| Engine | Backend | Verified queries |
|---|---|---|
| core | json | 17 |
| core | sqlite | 17 |
| core | mmap | 17 |
| lite | json | 17 |
| lite | sqlite | 17 |
| lite | mmap | 17 |

## Limitations

- Search latencies use the public `Yeny.search` boundary and include query preprocessing and response wrapping.
- Every backend load (JSON, SQLite, mmap) starts in its own fresh interpreter, so Python state is process-cold; the OS page cache is not controlled and may still warm later runs.
- Memory values describe the whole phase workflow, not the exclusive size of any engine object.
- Tree RSS sums resident pages shared by fork (copy-on-write), so it can overstate exclusive usage.
- Sampling-based peaks can miss shorter-lived worker processes.
- End-of-phase self RSS is captured after garbage collection, but live references and allocator arenas can remain.
- Peak RSS delta covers the whole phase and is not exclusive to a single operation.
