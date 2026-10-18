# Yeny benchmark report

> These results describe one machine and one execution environment. They
> are not search-quality measurements or universal performance guarantees.

## Run

| Field | Value |
|---|---|
| Run ID | 20260801T192714Z-9ae740 |
| Started (UTC) | 2026-08-01T19:27:14.712038+00:00 |
| Finished (UTC) | 2026-08-01T19:27:41.026658+00:00 |
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
| profile | medium |
| engines | ['core', 'lite'] |
| warmups | 3 |
| repetitions | 10 |
| require_memory | True |

## Dataset and queries

| Field | Value |
|---|---|
| profile | medium |
| generator_version | lexical_zipf_v1 |
| seed | 20260117 |
| documents | 10000 |
| total_tokens | 320281 |
| vocabulary_nominal | 2048 |
| vocabulary_observed | 2048 |
| intentional_duplicates | 200 |
| sha256 | bd6ff2e7de8f98bfa62a6a18b0abb06795ea7cb28ba3f27593362c08df434573 |

| Field | Value |
|---|---|
| query_set_version | queries_v1 |
| query_count | 17 |
| queries_sha256 | f9b4250d58530f8f6f4820087b9b018911387c795c426e5aba10636907b076b9 |

## Construction and search after build

| Engine | Metric | Backend | Category | Median | p95 | Samples |
|---|---|---|---|---|---|---|
| core | dataset_generation | - | - | 184.62 ms | 184.62 ms | 1 |
| core | index_build | - | - | 377.48 ms | 377.48 ms | 1 |
| core | index_e2e_json | - | - | 743.01 ms | 743.01 ms | 1 |
| core | search_first | - | common | 24.17 ms | 24.17 ms | 1 |
| core | search_warm | - | common | 19.77 ms | 23.20 ms | 40 |
| core | search_warm | - | rare | 35.90 µs | 39.11 µs | 40 |
| core | search_warm | - | multi | 24.59 ms | 28.12 ms | 40 |
| core | search_warm | - | no_result | 5.49 µs | 6.54 µs | 40 |
| core | search_warm | - | repeated | 22.79 ms | 23.13 ms | 100 |
| lite | dataset_generation | - | - | 82.07 ms | 82.07 ms | 1 |
| lite | index_build | - | - | 140.98 ms | 140.98 ms | 1 |
| lite | index_e2e_json | - | - | 299.26 ms | 299.26 ms | 1 |
| lite | search_first | - | common | 6.74 ms | 6.74 ms | 1 |
| lite | search_warm | - | common | 5.36 ms | 6.39 ms | 40 |
| lite | search_warm | - | rare | 12.90 µs | 14.69 µs | 40 |
| lite | search_warm | - | multi | 7.22 ms | 8.23 ms | 40 |
| lite | search_warm | - | no_result | 2.47 µs | 2.83 µs | 40 |
| lite | search_warm | - | repeated | 6.35 ms | 6.49 ms | 100 |

## Persistence

| Engine | Metric | Backend | Category | Median | p95 | Samples |
|---|---|---|---|---|---|---|
| core | json_save | - | - | 349.09 ms | 349.09 ms | 1 |
| core | json_artifact_size | - | - | 6.06 MiB | 6.06 MiB | 1 |
| core | sqlite_save | - | - | 183.04 ms | 183.04 ms | 1 |
| core | sqlite_artifact_size | - | - | 5.18 MiB | 5.18 MiB | 1 |
| core | yny_write | - | - | 14.54 ms | 14.54 ms | 1 |
| core | yny_artifact_size | - | - | 2.21 MiB | 2.21 MiB | 1 |
| lite | json_save | - | - | 167.63 ms | 167.63 ms | 1 |
| lite | json_artifact_size | - | - | 5.71 MiB | 5.71 MiB | 1 |
| lite | sqlite_save | - | - | 97.85 ms | 97.85 ms | 1 |
| lite | sqlite_artifact_size | - | - | 5.18 MiB | 5.18 MiB | 1 |
| lite | yny_write | - | - | 7.55 ms | 7.55 ms | 1 |
| lite | yny_artifact_size | - | - | 2.14 MiB | 2.14 MiB | 1 |

## Standard loads

| Engine | Metric | Backend | Category | Median | p95 | Samples |
|---|---|---|---|---|---|---|
| core | load_standard | json | - | 196.58 ms | 196.58 ms | 1 |
| core | search_first_after_load | json | common | 23.32 ms | 23.32 ms | 1 |
| core | search_warm_after_load | json | common | 19.07 ms | 22.90 ms | 40 |
| core | search_warm_after_load | json | rare | 35.05 µs | 43.20 µs | 40 |
| core | search_warm_after_load | json | multi | 22.94 ms | 26.03 ms | 40 |
| core | search_warm_after_load | json | no_result | 4.57 µs | 5.02 µs | 40 |
| core | search_warm_after_load | json | repeated | 12.20 ms | 17.04 ms | 100 |
| core | load_standard | sqlite | - | 160.07 ms | 160.07 ms | 1 |
| core | search_first_after_load | sqlite | common | 11.72 ms | 11.72 ms | 1 |
| core | search_warm_after_load | sqlite | common | 9.70 ms | 11.33 ms | 40 |
| core | search_warm_after_load | sqlite | rare | 17.77 µs | 20.16 µs | 40 |
| core | search_warm_after_load | sqlite | multi | 11.58 ms | 13.01 ms | 40 |
| core | search_warm_after_load | sqlite | no_result | 2.81 µs | 3.12 µs | 40 |
| core | search_warm_after_load | sqlite | repeated | 11.05 ms | 11.36 ms | 100 |
| lite | load_standard | json | - | 92.94 ms | 92.94 ms | 1 |
| lite | search_first_after_load | json | common | 6.64 ms | 6.64 ms | 1 |
| lite | search_warm_after_load | json | common | 5.30 ms | 6.29 ms | 40 |
| lite | search_warm_after_load | json | rare | 12.67 µs | 14.60 µs | 40 |
| lite | search_warm_after_load | json | multi | 7.16 ms | 8.07 ms | 40 |
| lite | search_warm_after_load | json | no_result | 2.56 µs | 2.79 µs | 40 |
| lite | search_warm_after_load | json | repeated | 6.15 ms | 6.27 ms | 100 |
| lite | load_standard | sqlite | - | 108.27 ms | 108.27 ms | 1 |
| lite | search_first_after_load | sqlite | common | 6.46 ms | 6.46 ms | 1 |
| lite | search_warm_after_load | sqlite | common | 5.24 ms | 6.26 ms | 40 |
| lite | search_warm_after_load | sqlite | rare | 12.70 µs | 15.13 µs | 40 |
| lite | search_warm_after_load | sqlite | multi | 7.05 ms | 7.99 ms | 40 |
| lite | search_warm_after_load | sqlite | no_result | 2.44 µs | 2.63 µs | 40 |
| lite | search_warm_after_load | sqlite | repeated | 6.34 ms | 6.46 ms | 100 |

## Memory-mapped loads

| Engine | Metric | Backend | Category | Median | p95 | Samples |
|---|---|---|---|---|---|---|
| core | mmap_load | - | - | 3.35 ms | 3.35 ms | 1 |
| core | search_first_mmap | - | common | 22.66 ms | 22.66 ms | 1 |
| core | search_warm_mmap | - | common | 19.92 ms | 22.48 ms | 40 |
| core | search_warm_mmap | - | rare | 29.48 µs | 33.46 µs | 40 |
| core | search_warm_mmap | - | multi | 24.12 ms | 28.83 ms | 40 |
| core | search_warm_mmap | - | no_result | 2.73 µs | 2.98 µs | 40 |
| core | search_warm_mmap | - | repeated | 22.43 ms | 22.87 ms | 100 |
| lite | mmap_load | - | - | 2.14 ms | 2.14 ms | 1 |
| lite | search_first_mmap | - | common | 7.42 ms | 7.42 ms | 1 |
| lite | search_warm_mmap | - | common | 5.69 ms | 6.88 ms | 40 |
| lite | search_warm_mmap | - | rare | 16.70 µs | 18.31 µs | 40 |
| lite | search_warm_mmap | - | multi | 7.21 ms | 8.55 ms | 40 |
| lite | search_warm_mmap | - | no_result | 2.60 µs | 2.79 µs | 40 |
| lite | search_warm_mmap | - | repeated | 6.70 ms | 6.95 ms | 100 |

## Memory

RSS values are process readings, not exclusive ownership. `n/a` marks capabilities unavailable on this host; they are never reported as zero.

| Engine | Phase | Metric | Scope | Value | Status |
|---|---|---|---|---|---|
| core | build | memory_baseline_rss | process_tree | 9.55 MiB | ok |
| core | build | memory_peak_rss | process_tree | 71.46 MiB | ok |
| core | build | memory_peak_rss_delta | process_tree | 61.92 MiB | ok |
| core | build | memory_stable_rss | self_only | 69.31 MiB | ok |
| core | build | memory_max_processes | process_tree | 1 | ok |
| core | load_json | memory_baseline_rss | process_tree | 8.55 MiB | ok |
| core | load_json | memory_peak_rss | process_tree | 46.68 MiB | ok |
| core | load_json | memory_peak_rss_delta | process_tree | 38.13 MiB | ok |
| core | load_json | memory_stable_rss | self_only | 45.66 MiB | ok |
| core | load_json | memory_max_processes | process_tree | 1 | ok |
| core | load_sqlite | memory_baseline_rss | process_tree | 8.59 MiB | ok |
| core | load_sqlite | memory_peak_rss | process_tree | 58.56 MiB | ok |
| core | load_sqlite | memory_peak_rss_delta | process_tree | 49.98 MiB | ok |
| core | load_sqlite | memory_stable_rss | self_only | 52.96 MiB | ok |
| core | load_sqlite | memory_max_processes | process_tree | 1 | ok |
| core | load_mmap | memory_baseline_rss | process_tree | 9.09 MiB | ok |
| core | load_mmap | memory_peak_rss | process_tree | 38.96 MiB | ok |
| core | load_mmap | memory_peak_rss_delta | process_tree | 29.88 MiB | ok |
| core | load_mmap | memory_stable_rss | self_only | 38.11 MiB | ok |
| core | load_mmap | memory_max_processes | process_tree | 1 | ok |
| lite | build | memory_baseline_rss | process_tree | 8.73 MiB | ok |
| lite | build | memory_peak_rss | process_tree | 68.79 MiB | ok |
| lite | build | memory_peak_rss_delta | process_tree | 60.07 MiB | ok |
| lite | build | memory_stable_rss | self_only | 66.52 MiB | ok |
| lite | build | memory_max_processes | process_tree | 1 | ok |
| lite | load_json | memory_baseline_rss | process_tree | 8.38 MiB | ok |
| lite | load_json | memory_peak_rss | process_tree | 46.69 MiB | ok |
| lite | load_json | memory_peak_rss_delta | process_tree | 38.30 MiB | ok |
| lite | load_json | memory_stable_rss | self_only | 44.32 MiB | ok |
| lite | load_json | memory_max_processes | process_tree | 1 | ok |
| lite | load_sqlite | memory_baseline_rss | process_tree | 8.94 MiB | ok |
| lite | load_sqlite | memory_peak_rss | process_tree | 57.33 MiB | ok |
| lite | load_sqlite | memory_peak_rss_delta | process_tree | 48.39 MiB | ok |
| lite | load_sqlite | memory_stable_rss | self_only | 52.72 MiB | ok |
| lite | load_sqlite | memory_max_processes | process_tree | 1 | ok |
| lite | load_mmap | memory_baseline_rss | process_tree | 8.73 MiB | ok |
| lite | load_mmap | memory_peak_rss | process_tree | 38.37 MiB | ok |
| lite | load_mmap | memory_peak_rss_delta | process_tree | 29.64 MiB | ok |
| lite | load_mmap | memory_stable_rss | self_only | 37.55 MiB | ok |
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
