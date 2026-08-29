# Lucis benchmark report

> These results describe one machine and one execution environment. They
> are not search-quality measurements or universal performance guarantees.

## Run

| Field | Value |
|---|---|
| Run ID | 20260730T212413Z-5e28d8 |
| Started (UTC) | 2026-07-30T21:24:13.195048+00:00 |
| Finished (UTC) | 2026-07-30T21:24:14.962765+00:00 |
| Schema version | 1.0 |

## Environment

| Field | Value |
|---|---|
| python_version | 3.11.14 |
| python_implementation | CPython |
| platform | Linux-7.0.0-28-generic-x86_64-with-glibc2.39 |
| machine | x86_64 |
| lucis_version | 0.1.0 |
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
| profile | tiny |
| engines | ['core', 'lite'] |
| warmups | 3 |
| repetitions | 10 |
| require_memory | True |

## Dataset and queries

| Field | Value |
|---|---|
| profile | tiny |
| generator_version | lexical_zipf_v1 |
| seed | 20260117 |
| documents | 100 |
| total_tokens | 3305 |
| vocabulary_nominal | 2048 |
| vocabulary_observed | 735 |
| intentional_duplicates | 2 |
| sha256 | 60735906d9feebb636cd173b04d80497eda774956df222dbd4de291e9d135be0 |

| Field | Value |
|---|---|
| query_set_version | queries_v1 |
| query_count | 17 |
| queries_sha256 | 78de5bc2f7e91be29ae348183ed12e3c386d477c5a354af377465acaf995a4f4 |

## Construction and search after build

| Engine | Metric | Backend | Category | Median | p95 | Samples |
|---|---|---|---|---|---|---|
| core | dataset_generation | - | - | 6.37 ms | 6.37 ms | 1 |
| core | index_build | - | - | 3.73 ms | 3.73 ms | 1 |
| core | index_e2e_json | - | - | 14.54 ms | 14.54 ms | 1 |
| core | search_first | - | common | 215.65 µs | 215.65 µs | 1 |
| core | search_warm | - | common | 131.01 µs | 408.74 µs | 40 |
| core | search_warm | - | rare | 9.08 µs | 10.39 µs | 40 |
| core | search_warm | - | multi | 148.46 µs | 468.56 µs | 40 |
| core | search_warm | - | no_result | 3.84 µs | 4.05 µs | 40 |
| core | search_warm | - | repeated | 224.38 µs | 411.98 µs | 100 |
| lite | dataset_generation | - | - | 3.78 ms | 3.78 ms | 1 |
| lite | index_build | - | - | 2.89 ms | 2.89 ms | 1 |
| lite | index_e2e_json | - | - | 7.90 ms | 7.90 ms | 1 |
| lite | search_first | - | common | 143.35 µs | 143.35 µs | 1 |
| lite | search_warm | - | common | 77.31 µs | 165.79 µs | 40 |
| lite | search_warm | - | rare | 7.53 µs | 8.36 µs | 40 |
| lite | search_warm | - | multi | 93.19 µs | 117.61 µs | 40 |
| lite | search_warm | - | no_result | 3.83 µs | 10.26 µs | 40 |
| lite | search_warm | - | repeated | 80.92 µs | 88.80 µs | 100 |

## Persistence

| Engine | Metric | Backend | Category | Median | p95 | Samples |
|---|---|---|---|---|---|---|
| core | json_save | - | - | 10.59 ms | 10.59 ms | 1 |
| core | json_artifact_size | - | - | 80.35 KiB | 80.35 KiB | 1 |
| core | sqlite_save | - | - | 10.94 ms | 10.94 ms | 1 |
| core | sqlite_artifact_size | - | - | 196.00 KiB | 196.00 KiB | 1 |
| core | lcs_write | - | - | 3.98 ms | 3.98 ms | 1 |
| core | lcs_artifact_size | - | - | 77.64 KiB | 77.64 KiB | 1 |
| lite | json_save | - | - | 5.44 ms | 5.44 ms | 1 |
| lite | json_artifact_size | - | - | 77.03 KiB | 77.03 KiB | 1 |
| lite | sqlite_save | - | - | 13.92 ms | 13.92 ms | 1 |
| lite | sqlite_artifact_size | - | - | 196.00 KiB | 196.00 KiB | 1 |
| lite | lcs_write | - | - | 5.65 ms | 5.65 ms | 1 |
| lite | lcs_artifact_size | - | - | 76.86 KiB | 76.86 KiB | 1 |

## Standard loads

| Engine | Metric | Backend | Category | Median | p95 | Samples |
|---|---|---|---|---|---|---|
| core | load_standard | json | - | 4.91 ms | 4.91 ms | 1 |
| core | search_first_after_load | json | common | 335.42 µs | 335.42 µs | 1 |
| core | search_warm_after_load | json | common | 307.57 µs | 404.48 µs | 40 |
| core | search_warm_after_load | json | rare | 9.55 µs | 11.66 µs | 40 |
| core | search_warm_after_load | json | multi | 252.57 µs | 408.55 µs | 40 |
| core | search_warm_after_load | json | no_result | 4.02 µs | 10.68 µs | 40 |
| core | search_warm_after_load | json | repeated | 141.03 µs | 411.73 µs | 100 |
| core | load_standard | sqlite | - | 5.53 ms | 5.53 ms | 1 |
| core | search_first_after_load | sqlite | common | 312.95 µs | 312.95 µs | 1 |
| core | search_warm_after_load | sqlite | common | 132.14 µs | 193.52 µs | 40 |
| core | search_warm_after_load | sqlite | rare | 9.33 µs | 10.66 µs | 40 |
| core | search_warm_after_load | sqlite | multi | 151.10 µs | 185.28 µs | 40 |
| core | search_warm_after_load | sqlite | no_result | 3.86 µs | 4.11 µs | 40 |
| core | search_warm_after_load | sqlite | repeated | 138.55 µs | 173.21 µs | 100 |
| lite | load_standard | json | - | 3.09 ms | 3.09 ms | 1 |
| lite | search_first_after_load | json | common | 229.26 µs | 229.26 µs | 1 |
| lite | search_warm_after_load | json | common | 78.97 µs | 92.86 µs | 40 |
| lite | search_warm_after_load | json | rare | 7.39 µs | 8.12 µs | 40 |
| lite | search_warm_after_load | json | multi | 95.85 µs | 149.92 µs | 40 |
| lite | search_warm_after_load | json | no_result | 3.63 µs | 8.61 µs | 40 |
| lite | search_warm_after_load | json | repeated | 82.49 µs | 133.92 µs | 100 |
| lite | load_standard | sqlite | - | 4.36 ms | 4.36 ms | 1 |
| lite | search_first_after_load | sqlite | common | 250.92 µs | 250.92 µs | 1 |
| lite | search_warm_after_load | sqlite | common | 80.37 µs | 128.31 µs | 40 |
| lite | search_warm_after_load | sqlite | rare | 7.37 µs | 8.69 µs | 40 |
| lite | search_warm_after_load | sqlite | multi | 95.62 µs | 115.46 µs | 40 |
| lite | search_warm_after_load | sqlite | no_result | 3.67 µs | 3.93 µs | 40 |
| lite | search_warm_after_load | sqlite | repeated | 81.67 µs | 127.69 µs | 100 |

## Memory-mapped loads

| Engine | Metric | Backend | Category | Median | p95 | Samples |
|---|---|---|---|---|---|---|
| core | mmap_load | - | - | 1.03 ms | 1.03 ms | 1 |
| core | search_first_mmap | - | common | 483.67 µs | 483.67 µs | 1 |
| core | search_warm_mmap | - | common | 289.48 µs | 321.37 µs | 40 |
| core | search_warm_mmap | - | rare | 15.01 µs | 15.80 µs | 40 |
| core | search_warm_mmap | - | multi | 712.84 µs | 1.27 ms | 40 |
| core | search_warm_mmap | - | no_result | 12.72 µs | 15.01 µs | 40 |
| core | search_warm_mmap | - | repeated | 311.12 µs | 946.29 µs | 100 |
| lite | mmap_load | - | - | 1.00 ms | 1.00 ms | 1 |
| lite | search_first_mmap | - | common | 260.30 µs | 260.30 µs | 1 |
| lite | search_warm_mmap | - | common | 230.77 µs | 261.55 µs | 40 |
| lite | search_warm_mmap | - | rare | 9.79 µs | 21.56 µs | 40 |
| lite | search_warm_mmap | - | multi | 114.58 µs | 264.28 µs | 40 |
| lite | search_warm_mmap | - | no_result | 10.62 µs | 12.20 µs | 40 |
| lite | search_warm_mmap | - | repeated | 107.06 µs | 273.95 µs | 100 |

## Memory

RSS values are process readings, not exclusive ownership. `n/a` marks capabilities unavailable on this host; they are never reported as zero.

| Engine | Phase | Metric | Scope | Value | Status |
|---|---|---|---|---|---|
| core | build | memory_baseline_rss | process_tree | 6.87 MiB | ok |
| core | build | memory_peak_rss | process_tree | 27.96 MiB | ok |
| core | build | memory_peak_rss_delta | process_tree | 21.09 MiB | ok |
| core | build | memory_stable_rss | self_only | 27.96 MiB | ok |
| core | build | memory_max_processes | process_tree | 1 | ok |
| core | load_json | memory_baseline_rss | process_tree | 7.48 MiB | ok |
| core | load_json | memory_peak_rss | process_tree | 25.74 MiB | ok |
| core | load_json | memory_peak_rss_delta | process_tree | 18.26 MiB | ok |
| core | load_json | memory_stable_rss | self_only | 25.73 MiB | ok |
| core | load_json | memory_max_processes | process_tree | 1 | ok |
| core | load_sqlite | memory_baseline_rss | process_tree | 7.34 MiB | ok |
| core | load_sqlite | memory_peak_rss | process_tree | 26.66 MiB | ok |
| core | load_sqlite | memory_peak_rss_delta | process_tree | 19.32 MiB | ok |
| core | load_sqlite | memory_stable_rss | self_only | 26.66 MiB | ok |
| core | load_sqlite | memory_max_processes | process_tree | 1 | ok |
| core | load_mmap | memory_baseline_rss | process_tree | 6.84 MiB | ok |
| core | load_mmap | memory_peak_rss | process_tree | 25.63 MiB | ok |
| core | load_mmap | memory_peak_rss_delta | process_tree | 18.79 MiB | ok |
| core | load_mmap | memory_stable_rss | self_only | 25.58 MiB | ok |
| core | load_mmap | memory_max_processes | process_tree | 1 | ok |
| lite | build | memory_baseline_rss | process_tree | 6.77 MiB | ok |
| lite | build | memory_peak_rss | process_tree | 28.02 MiB | ok |
| lite | build | memory_peak_rss_delta | process_tree | 21.25 MiB | ok |
| lite | build | memory_stable_rss | self_only | 28.02 MiB | ok |
| lite | build | memory_max_processes | process_tree | 1 | ok |
| lite | load_json | memory_baseline_rss | process_tree | 6.94 MiB | ok |
| lite | load_json | memory_peak_rss | process_tree | 25.75 MiB | ok |
| lite | load_json | memory_peak_rss_delta | process_tree | 18.80 MiB | ok |
| lite | load_json | memory_stable_rss | self_only | 25.74 MiB | ok |
| lite | load_json | memory_max_processes | process_tree | 1 | ok |
| lite | load_sqlite | memory_baseline_rss | process_tree | 6.67 MiB | ok |
| lite | load_sqlite | memory_peak_rss | process_tree | 26.63 MiB | ok |
| lite | load_sqlite | memory_peak_rss_delta | process_tree | 19.96 MiB | ok |
| lite | load_sqlite | memory_stable_rss | self_only | 26.63 MiB | ok |
| lite | load_sqlite | memory_max_processes | process_tree | 1 | ok |
| lite | load_mmap | memory_baseline_rss | process_tree | 6.86 MiB | ok |
| lite | load_mmap | memory_peak_rss | process_tree | 25.61 MiB | ok |
| lite | load_mmap | memory_peak_rss_delta | process_tree | 18.75 MiB | ok |
| lite | load_mmap | memory_stable_rss | self_only | 25.55 MiB | ok |
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

- Search latencies use the public `Lucis.search` boundary and include query preprocessing and response wrapping.
- Every backend load (JSON, SQLite, mmap) starts in its own fresh interpreter, so Python state is process-cold; the OS page cache is not controlled and may still warm later runs.
- Memory values describe the whole phase workflow, not the exclusive size of any engine object.
- Tree RSS sums resident pages shared by fork (copy-on-write), so it can overstate exclusive usage.
- Sampling-based peaks can miss shorter-lived worker processes.
- End-of-phase self RSS is captured after garbage collection, but live references and allocator arenas can remain.
- Peak RSS delta covers the whole phase and is not exclusive to a single operation.
