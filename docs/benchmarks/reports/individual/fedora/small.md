# Lucis benchmark report

> These results describe one machine and one execution environment. They
> are not search-quality measurements or universal performance guarantees.

## Run

| Field | Value |
|---|---|
| Run ID | 20260801T192512Z-65cd43 |
| Started (UTC) | 2026-08-01T19:25:12.878719+00:00 |
| Finished (UTC) | 2026-08-01T19:25:18.247847+00:00 |
| Schema version | 1.0 |

## Environment

| Field | Value |
|---|---|
| python_version | 3.14.6 |
| python_implementation | CPython |
| platform | Linux-7.1.3-200.fc44.x86_64-x86_64-with-glibc2.43 |
| machine | x86_64 |
| lucis_version | 0.1.0 |
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
| profile | small |
| engines | ['core', 'lite'] |
| warmups | 3 |
| repetitions | 10 |
| require_memory | True |

## Dataset and queries

| Field | Value |
|---|---|
| profile | small |
| generator_version | lexical_zipf_v1 |
| seed | 20260117 |
| documents | 1000 |
| total_tokens | 32485 |
| vocabulary_nominal | 2048 |
| vocabulary_observed | 1898 |
| intentional_duplicates | 20 |
| sha256 | 83dbd1dceae326ae6e04004dceb3059da821e98eb955dc00e85eb3a98078358f |

| Field | Value |
|---|---|
| query_set_version | queries_v1 |
| query_count | 17 |
| queries_sha256 | dcb1773b3fe2421c3985fd73d7c5081a6a06bae05a4b97ba035bf5b64ae1d0f8 |

## Construction and search after build

| Engine | Metric | Backend | Category | Median | p95 | Samples |
|---|---|---|---|---|---|---|
| core | dataset_generation | - | - | 19.70 ms | 19.70 ms | 1 |
| core | index_build | - | - | 39.26 ms | 39.26 ms | 1 |
| core | index_e2e_json | - | - | 85.43 ms | 85.43 ms | 1 |
| core | search_first | - | common | 2.65 ms | 2.65 ms | 1 |
| core | search_warm | - | common | 1.76 ms | 2.12 ms | 40 |
| core | search_warm | - | rare | 13.19 µs | 14.49 µs | 40 |
| core | search_warm | - | multi | 2.06 ms | 2.40 ms | 40 |
| core | search_warm | - | no_result | 5.44 µs | 7.12 µs | 40 |
| core | search_warm | - | repeated | 2.08 ms | 2.16 ms | 100 |
| lite | dataset_generation | - | - | 19.66 ms | 19.66 ms | 1 |
| lite | index_build | - | - | 29.05 ms | 29.05 ms | 1 |
| lite | index_e2e_json | - | - | 70.56 ms | 70.56 ms | 1 |
| lite | search_first | - | common | 1.36 ms | 1.36 ms | 1 |
| lite | search_warm | - | common | 977.65 µs | 1.11 ms | 40 |
| lite | search_warm | - | rare | 10.78 µs | 11.76 µs | 40 |
| lite | search_warm | - | multi | 1.17 ms | 1.35 ms | 40 |
| lite | search_warm | - | no_result | 4.91 µs | 5.25 µs | 40 |
| lite | search_warm | - | repeated | 1.09 ms | 1.23 ms | 100 |

## Persistence

| Engine | Metric | Backend | Category | Median | p95 | Samples |
|---|---|---|---|---|---|---|
| core | json_save | - | - | 43.94 ms | 43.94 ms | 1 |
| core | json_artifact_size | - | - | 655.74 KiB | 655.74 KiB | 1 |
| core | sqlite_save | - | - | 28.61 ms | 28.61 ms | 1 |
| core | sqlite_artifact_size | - | - | 764.00 KiB | 764.00 KiB | 1 |
| core | lcs_write | - | - | 8.64 ms | 8.64 ms | 1 |
| core | lcs_artifact_size | - | - | 354.05 KiB | 354.05 KiB | 1 |
| lite | json_save | - | - | 40.38 ms | 40.38 ms | 1 |
| lite | json_artifact_size | - | - | 621.75 KiB | 621.75 KiB | 1 |
| lite | sqlite_save | - | - | 27.07 ms | 27.07 ms | 1 |
| lite | sqlite_artifact_size | - | - | 764.00 KiB | 764.00 KiB | 1 |
| lite | lcs_write | - | - | 7.04 ms | 7.04 ms | 1 |
| lite | lcs_artifact_size | - | - | 346.24 KiB | 346.24 KiB | 1 |

## Standard loads

| Engine | Metric | Backend | Category | Median | p95 | Samples |
|---|---|---|---|---|---|---|
| core | load_standard | json | - | 23.57 ms | 23.57 ms | 1 |
| core | search_first_after_load | json | common | 2.32 ms | 2.32 ms | 1 |
| core | search_warm_after_load | json | common | 1.71 ms | 2.03 ms | 40 |
| core | search_warm_after_load | json | rare | 13.03 µs | 17.33 µs | 40 |
| core | search_warm_after_load | json | multi | 1.94 ms | 2.26 ms | 40 |
| core | search_warm_after_load | json | no_result | 5.48 µs | 5.82 µs | 40 |
| core | search_warm_after_load | json | repeated | 2.02 ms | 2.08 ms | 100 |
| core | load_standard | sqlite | - | 44.55 ms | 44.55 ms | 1 |
| core | search_first_after_load | sqlite | common | 2.34 ms | 2.34 ms | 1 |
| core | search_warm_after_load | sqlite | common | 1.70 ms | 1.98 ms | 40 |
| core | search_warm_after_load | sqlite | rare | 12.87 µs | 14.58 µs | 40 |
| core | search_warm_after_load | sqlite | multi | 1.94 ms | 2.24 ms | 40 |
| core | search_warm_after_load | sqlite | no_result | 5.39 µs | 5.94 µs | 40 |
| core | search_warm_after_load | sqlite | repeated | 2.00 ms | 2.09 ms | 100 |
| lite | load_standard | json | - | 22.68 ms | 22.68 ms | 1 |
| lite | search_first_after_load | json | common | 1.30 ms | 1.30 ms | 1 |
| lite | search_warm_after_load | json | common | 927.44 µs | 1.07 ms | 40 |
| lite | search_warm_after_load | json | rare | 10.70 µs | 12.25 µs | 40 |
| lite | search_warm_after_load | json | multi | 1.16 ms | 1.31 ms | 40 |
| lite | search_warm_after_load | json | no_result | 5.08 µs | 5.52 µs | 40 |
| lite | search_warm_after_load | json | repeated | 1.08 ms | 1.12 ms | 100 |
| lite | load_standard | sqlite | - | 33.05 ms | 33.05 ms | 1 |
| lite | search_first_after_load | sqlite | common | 1.36 ms | 1.36 ms | 1 |
| lite | search_warm_after_load | sqlite | common | 939.76 µs | 1.09 ms | 40 |
| lite | search_warm_after_load | sqlite | rare | 10.86 µs | 12.43 µs | 40 |
| lite | search_warm_after_load | sqlite | multi | 1.18 ms | 1.35 ms | 40 |
| lite | search_warm_after_load | sqlite | no_result | 5.12 µs | 5.47 µs | 40 |
| lite | search_warm_after_load | sqlite | repeated | 1.10 ms | 1.13 ms | 100 |

## Memory-mapped loads

| Engine | Metric | Backend | Category | Median | p95 | Samples |
|---|---|---|---|---|---|---|
| core | mmap_load | - | - | 4.22 ms | 4.22 ms | 1 |
| core | search_first_mmap | - | common | 4.65 ms | 4.65 ms | 1 |
| core | search_warm_mmap | - | common | 3.60 ms | 4.28 ms | 40 |
| core | search_warm_mmap | - | rare | 19.52 µs | 22.83 µs | 40 |
| core | search_warm_mmap | - | multi | 4.68 ms | 5.47 ms | 40 |
| core | search_warm_mmap | - | no_result | 5.64 µs | 5.93 µs | 40 |
| core | search_warm_mmap | - | repeated | 4.23 ms | 4.31 ms | 100 |
| lite | mmap_load | - | - | 4.03 ms | 4.03 ms | 1 |
| lite | search_first_mmap | - | common | 1.44 ms | 1.44 ms | 1 |
| lite | search_warm_mmap | - | common | 1.03 ms | 1.19 ms | 40 |
| lite | search_warm_mmap | - | rare | 14.15 µs | 20.46 µs | 40 |
| lite | search_warm_mmap | - | multi | 1.28 ms | 1.44 ms | 40 |
| lite | search_warm_mmap | - | no_result | 5.49 µs | 6.04 µs | 40 |
| lite | search_warm_mmap | - | repeated | 1.19 ms | 1.24 ms | 100 |

## Memory

RSS values are process readings, not exclusive ownership. `n/a` marks capabilities unavailable on this host; they are never reported as zero.

| Engine | Phase | Metric | Scope | Value | Status |
|---|---|---|---|---|---|
| core | build | memory_baseline_rss | process_tree | 8.85 MiB | ok |
| core | build | memory_peak_rss | process_tree | 36.32 MiB | ok |
| core | build | memory_peak_rss_delta | process_tree | 27.47 MiB | ok |
| core | build | memory_stable_rss | self_only | 36.32 MiB | ok |
| core | build | memory_max_processes | process_tree | 1 | ok |
| core | load_json | memory_baseline_rss | process_tree | 8.48 MiB | ok |
| core | load_json | memory_peak_rss | process_tree | 30.03 MiB | ok |
| core | load_json | memory_peak_rss_delta | process_tree | 21.54 MiB | ok |
| core | load_json | memory_stable_rss | self_only | 30.03 MiB | ok |
| core | load_json | memory_max_processes | process_tree | 1 | ok |
| core | load_sqlite | memory_baseline_rss | process_tree | 8.62 MiB | ok |
| core | load_sqlite | memory_peak_rss | process_tree | 32.75 MiB | ok |
| core | load_sqlite | memory_peak_rss_delta | process_tree | 24.12 MiB | ok |
| core | load_sqlite | memory_stable_rss | self_only | 32.75 MiB | ok |
| core | load_sqlite | memory_max_processes | process_tree | 1 | ok |
| core | load_mmap | memory_baseline_rss | process_tree | 8.46 MiB | ok |
| core | load_mmap | memory_peak_rss | process_tree | 29.47 MiB | ok |
| core | load_mmap | memory_peak_rss_delta | process_tree | 21.01 MiB | ok |
| core | load_mmap | memory_stable_rss | self_only | 28.82 MiB | ok |
| core | load_mmap | memory_max_processes | process_tree | 1 | ok |
| lite | build | memory_baseline_rss | process_tree | 8.57 MiB | ok |
| lite | build | memory_peak_rss | process_tree | 35.98 MiB | ok |
| lite | build | memory_peak_rss_delta | process_tree | 27.41 MiB | ok |
| lite | build | memory_stable_rss | self_only | 35.98 MiB | ok |
| lite | build | memory_max_processes | process_tree | 1 | ok |
| lite | load_json | memory_baseline_rss | process_tree | 8.64 MiB | ok |
| lite | load_json | memory_peak_rss | process_tree | 30.03 MiB | ok |
| lite | load_json | memory_peak_rss_delta | process_tree | 21.39 MiB | ok |
| lite | load_json | memory_stable_rss | self_only | 30.03 MiB | ok |
| lite | load_json | memory_max_processes | process_tree | 1 | ok |
| lite | load_sqlite | memory_baseline_rss | process_tree | 8.64 MiB | ok |
| lite | load_sqlite | memory_peak_rss | process_tree | 32.59 MiB | ok |
| lite | load_sqlite | memory_peak_rss_delta | process_tree | 23.95 MiB | ok |
| lite | load_sqlite | memory_stable_rss | self_only | 32.57 MiB | ok |
| lite | load_sqlite | memory_max_processes | process_tree | 1 | ok |
| lite | load_mmap | memory_baseline_rss | process_tree | 8.63 MiB | ok |
| lite | load_mmap | memory_peak_rss | process_tree | 29.45 MiB | ok |
| lite | load_mmap | memory_peak_rss_delta | process_tree | 20.82 MiB | ok |
| lite | load_mmap | memory_stable_rss | self_only | 29.03 MiB | ok |
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
