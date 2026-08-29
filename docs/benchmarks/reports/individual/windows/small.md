# Lucis benchmark report

> These results describe one machine and one execution environment. They
> are not search-quality measurements or universal performance guarantees.

## Run

| Field | Value |
|---|---|
| Run ID | 20260803T001942Z-62b135 |
| Started (UTC) | 2026-08-03T00:19:42.145614+00:00 |
| Finished (UTC) | 2026-08-03T00:19:50.047580+00:00 |
| Schema version | 1.0 |

## Environment

| Field | Value |
|---|---|
| python_version | 3.13.0 |
| python_implementation | CPython |
| platform | Windows-11-10.0.26200-SP0 |
| machine | AMD64 |
| lucis_version | 0.1.0 |
| cpu_model | AMD64 Family 25 Model 80 Stepping 0, AuthenticAMD |
| logical_cpu_count | 16 |
| total_ram_bytes | 16474554368 (15.34 GiB) |
| memory_mechanisms | psutil, proc |
| psutil_version | 6.1.0 |
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
| core | dataset_generation | - | - | 18.36 ms | 18.36 ms | 1 |
| core | index_build | - | - | 38.28 ms | 38.28 ms | 1 |
| core | index_e2e_json | - | - | 113.78 ms | 113.78 ms | 1 |
| core | search_first | - | common | 3.01 ms | 3.01 ms | 1 |
| core | search_warm | - | common | 1.84 ms | 2.13 ms | 40 |
| core | search_warm | - | rare | 12.75 µs | 14.60 µs | 40 |
| core | search_warm | - | multi | 2.10 ms | 2.45 ms | 40 |
| core | search_warm | - | no_result | 5.40 µs | 7.10 µs | 40 |
| core | search_warm | - | repeated | 2.23 ms | 4.26 ms | 100 |
| lite | dataset_generation | - | - | 18.42 ms | 18.42 ms | 1 |
| lite | index_build | - | - | 26.32 ms | 26.32 ms | 1 |
| lite | index_e2e_json | - | - | 86.07 ms | 86.07 ms | 1 |
| lite | search_first | - | common | 1.57 ms | 1.57 ms | 1 |
| lite | search_warm | - | common | 1.01 ms | 1.45 ms | 40 |
| lite | search_warm | - | rare | 10.35 µs | 11.30 µs | 40 |
| lite | search_warm | - | multi | 1.20 ms | 1.82 ms | 40 |
| lite | search_warm | - | no_result | 5.05 µs | 5.50 µs | 40 |
| lite | search_warm | - | repeated | 1.14 ms | 1.42 ms | 100 |

## Persistence

| Engine | Metric | Backend | Category | Median | p95 | Samples |
|---|---|---|---|---|---|---|
| core | json_save | - | - | 72.07 ms | 72.07 ms | 1 |
| core | json_artifact_size | - | - | 685.97 KiB | 685.97 KiB | 1 |
| core | sqlite_save | - | - | 49.08 ms | 49.08 ms | 1 |
| core | sqlite_artifact_size | - | - | 704.00 KiB | 704.00 KiB | 1 |
| core | lcs_write | - | - | 10.22 ms | 10.22 ms | 1 |
| core | lcs_artifact_size | - | - | 354.05 KiB | 354.05 KiB | 1 |
| lite | json_save | - | - | 65.99 ms | 65.99 ms | 1 |
| lite | json_artifact_size | - | - | 651.00 KiB | 651.00 KiB | 1 |
| lite | sqlite_save | - | - | 50.32 ms | 50.32 ms | 1 |
| lite | sqlite_artifact_size | - | - | 704.00 KiB | 704.00 KiB | 1 |
| lite | lcs_write | - | - | 11.24 ms | 11.24 ms | 1 |
| lite | lcs_artifact_size | - | - | 346.24 KiB | 346.24 KiB | 1 |

## Standard loads

| Engine | Metric | Backend | Category | Median | p95 | Samples |
|---|---|---|---|---|---|---|
| core | load_standard | json | - | 25.59 ms | 25.59 ms | 1 |
| core | search_first_after_load | json | common | 2.48 ms | 2.48 ms | 1 |
| core | search_warm_after_load | json | common | 1.89 ms | 2.30 ms | 40 |
| core | search_warm_after_load | json | rare | 14.10 µs | 31.60 µs | 40 |
| core | search_warm_after_load | json | multi | 2.16 ms | 2.94 ms | 40 |
| core | search_warm_after_load | json | no_result | 5.80 µs | 6.20 µs | 40 |
| core | search_warm_after_load | json | repeated | 2.13 ms | 4.29 ms | 100 |
| core | load_standard | sqlite | - | 47.37 ms | 47.37 ms | 1 |
| core | search_first_after_load | sqlite | common | 3.50 ms | 3.50 ms | 1 |
| core | search_warm_after_load | sqlite | common | 1.94 ms | 3.49 ms | 40 |
| core | search_warm_after_load | sqlite | rare | 12.80 µs | 14.70 µs | 40 |
| core | search_warm_after_load | sqlite | multi | 2.10 ms | 3.48 ms | 40 |
| core | search_warm_after_load | sqlite | no_result | 5.70 µs | 6.20 µs | 40 |
| core | search_warm_after_load | sqlite | repeated | 2.19 ms | 4.34 ms | 100 |
| lite | load_standard | json | - | 29.36 ms | 29.36 ms | 1 |
| lite | search_first_after_load | json | common | 1.47 ms | 1.47 ms | 1 |
| lite | search_warm_after_load | json | common | 1.02 ms | 1.16 ms | 40 |
| lite | search_warm_after_load | json | rare | 10.90 µs | 12.00 µs | 40 |
| lite | search_warm_after_load | json | multi | 1.37 ms | 2.35 ms | 40 |
| lite | search_warm_after_load | json | no_result | 7.80 µs | 16.20 µs | 40 |
| lite | search_warm_after_load | json | repeated | 1.16 ms | 2.08 ms | 100 |
| lite | load_standard | sqlite | - | 55.56 ms | 55.56 ms | 1 |
| lite | search_first_after_load | sqlite | common | 2.01 ms | 2.01 ms | 1 |
| lite | search_warm_after_load | sqlite | common | 1.03 ms | 1.87 ms | 40 |
| lite | search_warm_after_load | sqlite | rare | 10.80 µs | 11.60 µs | 40 |
| lite | search_warm_after_load | sqlite | multi | 1.22 ms | 2.26 ms | 40 |
| lite | search_warm_after_load | sqlite | no_result | 5.40 µs | 11.10 µs | 40 |
| lite | search_warm_after_load | sqlite | repeated | 1.15 ms | 1.92 ms | 100 |

## Memory-mapped loads

| Engine | Metric | Backend | Category | Median | p95 | Samples |
|---|---|---|---|---|---|---|
| core | mmap_load | - | - | 4.26 ms | 4.26 ms | 1 |
| core | search_first_mmap | - | common | 4.95 ms | 4.95 ms | 1 |
| core | search_warm_mmap | - | common | 4.53 ms | 7.16 ms | 40 |
| core | search_warm_mmap | - | rare | 19.45 µs | 22.00 µs | 40 |
| core | search_warm_mmap | - | multi | 5.03 ms | 7.74 ms | 40 |
| core | search_warm_mmap | - | no_result | 5.90 µs | 6.30 µs | 40 |
| core | search_warm_mmap | - | repeated | 4.59 ms | 8.11 ms | 100 |
| lite | mmap_load | - | - | 5.52 ms | 5.52 ms | 1 |
| lite | search_first_mmap | - | common | 1.52 ms | 1.52 ms | 1 |
| lite | search_warm_mmap | - | common | 1.17 ms | 2.20 ms | 40 |
| lite | search_warm_mmap | - | rare | 18.55 µs | 25.80 µs | 40 |
| lite | search_warm_mmap | - | multi | 1.25 ms | 1.44 ms | 40 |
| lite | search_warm_mmap | - | no_result | 5.30 µs | 5.50 µs | 40 |
| lite | search_warm_mmap | - | repeated | 1.15 ms | 1.85 ms | 100 |

## Memory

RSS values are process readings, not exclusive ownership. `n/a` marks capabilities unavailable on this host; they are never reported as zero.

| Engine | Phase | Metric | Scope | Value | Status |
|---|---|---|---|---|---|
| core | build | memory_baseline_rss | process_tree | 8.37 MiB | ok |
| core | build | memory_peak_rss | process_tree | 34.86 MiB | ok |
| core | build | memory_peak_rss_delta | process_tree | 26.49 MiB | ok |
| core | build | memory_stable_rss | self_only | 35.28 MiB | ok |
| core | build | memory_max_processes | process_tree | 1 | ok |
| core | load_json | memory_baseline_rss | process_tree | 8.14 MiB | ok |
| core | load_json | memory_peak_rss | process_tree | 29.62 MiB | ok |
| core | load_json | memory_peak_rss_delta | process_tree | 21.48 MiB | ok |
| core | load_json | memory_stable_rss | self_only | 29.63 MiB | ok |
| core | load_json | memory_max_processes | process_tree | 1 | ok |
| core | load_sqlite | memory_baseline_rss | process_tree | 8.03 MiB | ok |
| core | load_sqlite | memory_peak_rss | process_tree | 32.54 MiB | ok |
| core | load_sqlite | memory_peak_rss_delta | process_tree | 24.51 MiB | ok |
| core | load_sqlite | memory_stable_rss | self_only | 31.14 MiB | ok |
| core | load_sqlite | memory_max_processes | process_tree | 1 | ok |
| core | load_mmap | memory_baseline_rss | process_tree | 7.78 MiB | ok |
| core | load_mmap | memory_peak_rss | process_tree | 29.27 MiB | ok |
| core | load_mmap | memory_peak_rss_delta | process_tree | 21.49 MiB | ok |
| core | load_mmap | memory_stable_rss | self_only | 29.21 MiB | ok |
| core | load_mmap | memory_max_processes | process_tree | 1 | ok |
| lite | build | memory_baseline_rss | process_tree | 7.75 MiB | ok |
| lite | build | memory_peak_rss | process_tree | 35.64 MiB | ok |
| lite | build | memory_peak_rss_delta | process_tree | 27.88 MiB | ok |
| lite | build | memory_stable_rss | self_only | 35.02 MiB | ok |
| lite | build | memory_max_processes | process_tree | 1 | ok |
| lite | load_json | memory_baseline_rss | process_tree | 8.03 MiB | ok |
| lite | load_json | memory_peak_rss | process_tree | 30.11 MiB | ok |
| lite | load_json | memory_peak_rss_delta | process_tree | 22.08 MiB | ok |
| lite | load_json | memory_stable_rss | self_only | 29.78 MiB | ok |
| lite | load_json | memory_max_processes | process_tree | 1 | ok |
| lite | load_sqlite | memory_baseline_rss | process_tree | 7.85 MiB | ok |
| lite | load_sqlite | memory_peak_rss | process_tree | 32.50 MiB | ok |
| lite | load_sqlite | memory_peak_rss_delta | process_tree | 24.65 MiB | ok |
| lite | load_sqlite | memory_stable_rss | self_only | 30.98 MiB | ok |
| lite | load_sqlite | memory_max_processes | process_tree | 1 | ok |
| lite | load_mmap | memory_baseline_rss | process_tree | 8.02 MiB | ok |
| lite | load_mmap | memory_peak_rss | process_tree | 29.39 MiB | ok |
| lite | load_mmap | memory_peak_rss_delta | process_tree | 21.37 MiB | ok |
| lite | load_mmap | memory_stable_rss | self_only | 29.34 MiB | ok |
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
