# Yeny benchmark report

> These results describe one machine and one execution environment. They
> are not search-quality measurements or universal performance guarantees.

## Run

| Field | Value |
|---|---|
| Run ID | 20260801T192950Z-1ee716 |
| Started (UTC) | 2026-08-01T19:29:50.859092+00:00 |
| Finished (UTC) | 2026-08-01T19:34:13.654031+00:00 |
| Schema version | 1.0 |

## Environment

| Field | Value |
|---|---|
| python_version | 3.14.6 |
| python_implementation | CPython |
| platform | Linux-7.1.3-200.fc44.x86_64-x86_64-with-glibc2.43 |
| machine | x86_64 |
| yeny_version | 0.1.0 |
| cpu_model | AMD Ryzen 7 7730U with Radeon Graphics |
| logical_cpu_count | 16 |
| total_ram_bytes | 16054988800 (14.95 GiB) |
| memory_mechanisms | psutil, resource, proc |
| psutil_version | 7.0.0 |
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
| core | dataset_generation | - | - | 1.70 s | 1.70 s | 1 |
| core | index_build | - | - | 4.15 s | 4.15 s | 1 |
| core | index_e2e_json | - | - | 5.23 s | 5.23 s | 1 |
| core | search_first | - | common | 148.80 ms | 148.80 ms | 1 |
| core | search_warm | - | common | 127.09 ms | 149.50 ms | 40 |
| core | search_warm | - | rare | 130.85 µs | 141.28 µs | 40 |
| core | search_warm | - | multi | 148.76 ms | 175.18 ms | 40 |
| core | search_warm | - | no_result | 2.71 µs | 3.41 µs | 40 |
| core | search_warm | - | repeated | 153.32 ms | 155.91 ms | 100 |
| lite | dataset_generation | - | - | 861.25 ms | 861.25 ms | 1 |
| lite | index_build | - | - | 1.50 s | 1.50 s | 1 |
| lite | index_e2e_json | - | - | 3.26 s | 3.26 s | 1 |
| lite | search_first | - | common | 80.94 ms | 80.94 ms | 1 |
| lite | search_warm | - | common | 72.32 ms | 87.81 ms | 40 |
| lite | search_warm | - | rare | 74.92 µs | 77.89 µs | 40 |
| lite | search_warm | - | multi | 93.36 ms | 114.89 ms | 40 |
| lite | search_warm | - | no_result | 2.40 µs | 2.73 µs | 40 |
| lite | search_warm | - | repeated | 87.61 ms | 88.49 ms | 100 |

## Persistence

| Engine | Metric | Backend | Category | Median | p95 | Samples |
|---|---|---|---|---|---|---|
| core | json_save | - | - | 1.95 s | 1.95 s | 1 |
| core | json_artifact_size | - | - | 62.65 MiB | 62.65 MiB | 1 |
| core | sqlite_save | - | - | 953.10 ms | 953.10 ms | 1 |
| core | sqlite_artifact_size | - | - | 51.16 MiB | 51.16 MiB | 1 |
| core | yny_write | - | - | 43.16 ms | 43.16 ms | 1 |
| core | yny_artifact_size | - | - | 20.78 MiB | 20.78 MiB | 1 |
| lite | json_save | - | - | 1.78 s | 1.78 s | 1 |
| lite | json_artifact_size | - | - | 59.15 MiB | 59.15 MiB | 1 |
| lite | sqlite_save | - | - | 904.57 ms | 904.57 ms | 1 |
| lite | sqlite_artifact_size | - | - | 51.16 MiB | 51.16 MiB | 1 |
| lite | yny_write | - | - | 35.75 ms | 35.75 ms | 1 |
| lite | yny_artifact_size | - | - | 20.01 MiB | 20.01 MiB | 1 |

## Standard loads

| Engine | Metric | Backend | Category | Median | p95 | Samples |
|---|---|---|---|---|---|---|
| core | load_standard | json | - | 1.20 s | 1.20 s | 1 |
| core | search_first_after_load | json | common | 140.16 ms | 140.16 ms | 1 |
| core | search_warm_after_load | json | common | 116.74 ms | 141.99 ms | 40 |
| core | search_warm_after_load | json | rare | 136.86 µs | 142.44 µs | 40 |
| core | search_warm_after_load | json | multi | 137.86 ms | 165.59 ms | 40 |
| core | search_warm_after_load | json | no_result | 2.83 µs | 3.05 µs | 40 |
| core | search_warm_after_load | json | repeated | 140.72 ms | 142.62 ms | 100 |
| core | load_standard | sqlite | - | 1.75 s | 1.75 s | 1 |
| core | search_first_after_load | sqlite | common | 153.60 ms | 153.60 ms | 1 |
| core | search_warm_after_load | sqlite | common | 130.33 ms | 151.91 ms | 40 |
| core | search_warm_after_load | sqlite | rare | 129.75 µs | 137.55 µs | 40 |
| core | search_warm_after_load | sqlite | multi | 149.21 ms | 176.13 ms | 40 |
| core | search_warm_after_load | sqlite | no_result | 2.58 µs | 2.87 µs | 40 |
| core | search_warm_after_load | sqlite | repeated | 152.14 ms | 153.70 ms | 100 |
| lite | load_standard | json | - | 1.11 s | 1.11 s | 1 |
| lite | search_first_after_load | json | common | 83.35 ms | 83.35 ms | 1 |
| lite | search_warm_after_load | json | common | 70.65 ms | 87.80 ms | 40 |
| lite | search_warm_after_load | json | rare | 74.52 µs | 80.07 µs | 40 |
| lite | search_warm_after_load | json | multi | 92.79 ms | 110.38 ms | 40 |
| lite | search_warm_after_load | json | no_result | 2.52 µs | 2.93 µs | 40 |
| lite | search_warm_after_load | json | repeated | 88.28 ms | 89.15 ms | 100 |
| lite | load_standard | sqlite | - | 1.12 s | 1.12 s | 1 |
| lite | search_first_after_load | sqlite | common | 81.25 ms | 81.25 ms | 1 |
| lite | search_warm_after_load | sqlite | common | 72.85 ms | 87.98 ms | 40 |
| lite | search_warm_after_load | sqlite | rare | 74.13 µs | 79.66 µs | 40 |
| lite | search_warm_after_load | sqlite | multi | 92.67 ms | 111.37 ms | 40 |
| lite | search_warm_after_load | sqlite | no_result | 2.42 µs | 2.71 µs | 40 |
| lite | search_warm_after_load | sqlite | repeated | 88.99 ms | 89.63 ms | 100 |

## Memory-mapped loads

| Engine | Metric | Backend | Category | Median | p95 | Samples |
|---|---|---|---|---|---|---|
| core | mmap_load | - | - | 13.48 ms | 13.48 ms | 1 |
| core | search_first_mmap | - | common | 266.34 ms | 266.34 ms | 1 |
| core | search_warm_mmap | - | common | 217.89 ms | 260.91 ms | 40 |
| core | search_warm_mmap | - | rare | 284.51 µs | 295.15 µs | 40 |
| core | search_warm_mmap | - | multi | 294.29 ms | 349.35 ms | 40 |
| core | search_warm_mmap | - | no_result | 2.87 µs | 3.07 µs | 40 |
| core | search_warm_mmap | - | repeated | 266.36 ms | 271.26 ms | 100 |
| lite | mmap_load | - | - | 2.44 ms | 2.44 ms | 1 |
| lite | search_first_mmap | - | common | 92.61 ms | 92.61 ms | 1 |
| lite | search_warm_mmap | - | common | 76.21 ms | 92.55 ms | 40 |
| lite | search_warm_mmap | - | rare | 82.21 µs | 87.01 µs | 40 |
| lite | search_warm_mmap | - | multi | 98.56 ms | 118.72 ms | 40 |
| lite | search_warm_mmap | - | no_result | 2.54 µs | 2.86 µs | 40 |
| lite | search_warm_mmap | - | repeated | 92.84 ms | 93.94 ms | 100 |

## Memory

RSS values are process readings, not exclusive ownership. `n/a` marks capabilities unavailable on this host; they are never reported as zero.

| Engine | Phase | Metric | Scope | Value | Status |
|---|---|---|---|---|---|
| core | build | memory_baseline_rss | process_tree | 8.70 MiB | ok |
| core | build | memory_peak_rss | process_tree | 412.91 MiB | ok |
| core | build | memory_peak_rss_delta | process_tree | 404.20 MiB | ok |
| core | build | memory_stable_rss | self_only | 342.91 MiB | ok |
| core | build | memory_max_processes | process_tree | 1 | ok |
| core | load_json | memory_baseline_rss | process_tree | 8.04 MiB | ok |
| core | load_json | memory_peak_rss | process_tree | 243.80 MiB | ok |
| core | load_json | memory_peak_rss_delta | process_tree | 235.76 MiB | ok |
| core | load_json | memory_stable_rss | self_only | 208.50 MiB | ok |
| core | load_json | memory_max_processes | process_tree | 1 | ok |
| core | load_sqlite | memory_baseline_rss | process_tree | 8.80 MiB | ok |
| core | load_sqlite | memory_peak_rss | process_tree | 325.48 MiB | ok |
| core | load_sqlite | memory_peak_rss_delta | process_tree | 316.68 MiB | ok |
| core | load_sqlite | memory_stable_rss | self_only | 237.76 MiB | ok |
| core | load_sqlite | memory_max_processes | process_tree | 1 | ok |
| core | load_mmap | memory_baseline_rss | process_tree | 8.83 MiB | ok |
| core | load_mmap | memory_peak_rss | process_tree | 135.35 MiB | ok |
| core | load_mmap | memory_peak_rss_delta | process_tree | 126.52 MiB | ok |
| core | load_mmap | memory_stable_rss | self_only | 125.93 MiB | ok |
| core | load_mmap | memory_max_processes | process_tree | 1 | ok |
| lite | build | memory_baseline_rss | process_tree | 8.62 MiB | ok |
| lite | build | memory_peak_rss | process_tree | 379.56 MiB | ok |
| lite | build | memory_peak_rss_delta | process_tree | 370.94 MiB | ok |
| lite | build | memory_stable_rss | self_only | 301.80 MiB | ok |
| lite | build | memory_max_processes | process_tree | 1 | ok |
| lite | load_json | memory_baseline_rss | process_tree | 8.64 MiB | ok |
| lite | load_json | memory_peak_rss | process_tree | 231.79 MiB | ok |
| lite | load_json | memory_peak_rss_delta | process_tree | 223.16 MiB | ok |
| lite | load_json | memory_stable_rss | self_only | 194.28 MiB | ok |
| lite | load_json | memory_max_processes | process_tree | 1 | ok |
| lite | load_sqlite | memory_baseline_rss | process_tree | 8.52 MiB | ok |
| lite | load_sqlite | memory_peak_rss | process_tree | 301.97 MiB | ok |
| lite | load_sqlite | memory_peak_rss_delta | process_tree | 293.45 MiB | ok |
| lite | load_sqlite | memory_stable_rss | self_only | 220.23 MiB | ok |
| lite | load_sqlite | memory_max_processes | process_tree | 1 | ok |
| lite | load_mmap | memory_baseline_rss | process_tree | 8.55 MiB | ok |
| lite | load_mmap | memory_peak_rss | process_tree | 128.39 MiB | ok |
| lite | load_mmap | memory_peak_rss_delta | process_tree | 119.84 MiB | ok |
| lite | load_mmap | memory_stable_rss | self_only | 123.83 MiB | ok |
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
