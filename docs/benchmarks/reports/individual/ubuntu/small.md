# Yeny benchmark report

> These results describe one machine and one execution environment. They
> are not search-quality measurements or universal performance guarantees.

## Run

| Field | Value |
|---|---|
| Run ID | 20260730T212421Z-42c4d2 |
| Started (UTC) | 2026-07-30T21:24:21.611225+00:00 |
| Finished (UTC) | 2026-07-30T21:24:26.639708+00:00 |
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
| core | dataset_generation | - | - | 23.39 ms | 23.39 ms | 1 |
| core | index_build | - | - | 60.02 ms | 60.02 ms | 1 |
| core | index_e2e_json | - | - | 119.60 ms | 119.60 ms | 1 |
| core | search_first | - | common | 4.72 ms | 4.72 ms | 1 |
| core | search_warm | - | common | 1.48 ms | 2.87 ms | 40 |
| core | search_warm | - | rare | 23.83 µs | 32.17 µs | 40 |
| core | search_warm | - | multi | 1.95 ms | 4.43 ms | 40 |
| core | search_warm | - | no_result | 3.88 µs | 4.14 µs | 40 |
| core | search_warm | - | repeated | 2.43 ms | 4.38 ms | 100 |
| lite | dataset_generation | - | - | 18.19 ms | 18.19 ms | 1 |
| lite | index_build | - | - | 37.80 ms | 37.80 ms | 1 |
| lite | index_e2e_json | - | - | 104.87 ms | 104.87 ms | 1 |
| lite | search_first | - | common | 3.07 ms | 3.07 ms | 1 |
| lite | search_warm | - | common | 884.69 µs | 2.52 ms | 40 |
| lite | search_warm | - | rare | 23.53 µs | 25.39 µs | 40 |
| lite | search_warm | - | multi | 969.87 µs | 3.25 ms | 40 |
| lite | search_warm | - | no_result | 3.73 µs | 4.03 µs | 40 |
| lite | search_warm | - | repeated | 893.81 µs | 1.15 ms | 100 |

## Persistence

| Engine | Metric | Backend | Category | Median | p95 | Samples |
|---|---|---|---|---|---|---|
| core | json_save | - | - | 61.75 ms | 61.75 ms | 1 |
| core | json_artifact_size | - | - | 655.74 KiB | 655.74 KiB | 1 |
| core | sqlite_save | - | - | 36.39 ms | 36.39 ms | 1 |
| core | sqlite_artifact_size | - | - | 704.00 KiB | 704.00 KiB | 1 |
| core | yny_write | - | - | 8.71 ms | 8.71 ms | 1 |
| core | yny_artifact_size | - | - | 354.05 KiB | 354.05 KiB | 1 |
| lite | json_save | - | - | 35.67 ms | 35.67 ms | 1 |
| lite | json_artifact_size | - | - | 621.75 KiB | 621.75 KiB | 1 |
| lite | sqlite_save | - | - | 38.35 ms | 38.35 ms | 1 |
| lite | sqlite_artifact_size | - | - | 704.00 KiB | 704.00 KiB | 1 |
| lite | yny_write | - | - | 8.92 ms | 8.92 ms | 1 |
| lite | yny_artifact_size | - | - | 346.24 KiB | 346.24 KiB | 1 |

## Standard loads

| Engine | Metric | Backend | Category | Median | p95 | Samples |
|---|---|---|---|---|---|---|
| core | load_standard | json | - | 19.43 ms | 19.43 ms | 1 |
| core | search_first_after_load | json | common | 1.89 ms | 1.89 ms | 1 |
| core | search_warm_after_load | json | common | 1.31 ms | 1.49 ms | 40 |
| core | search_warm_after_load | json | rare | 9.48 µs | 11.09 µs | 40 |
| core | search_warm_after_load | json | multi | 1.62 ms | 2.66 ms | 40 |
| core | search_warm_after_load | json | no_result | 9.28 µs | 12.84 µs | 40 |
| core | search_warm_after_load | json | repeated | 1.48 ms | 1.85 ms | 100 |
| core | load_standard | sqlite | - | 31.31 ms | 31.31 ms | 1 |
| core | search_first_after_load | sqlite | common | 1.65 ms | 1.65 ms | 1 |
| core | search_warm_after_load | sqlite | common | 1.44 ms | 2.04 ms | 40 |
| core | search_warm_after_load | sqlite | rare | 9.27 µs | 10.46 µs | 40 |
| core | search_warm_after_load | sqlite | multi | 1.49 ms | 1.88 ms | 40 |
| core | search_warm_after_load | sqlite | no_result | 3.99 µs | 4.23 µs | 40 |
| core | search_warm_after_load | sqlite | repeated | 1.53 ms | 4.15 ms | 100 |
| lite | load_standard | json | - | 19.52 ms | 19.52 ms | 1 |
| lite | search_first_after_load | json | common | 1.03 ms | 1.03 ms | 1 |
| lite | search_warm_after_load | json | common | 791.16 µs | 1.15 ms | 40 |
| lite | search_warm_after_load | json | rare | 7.50 µs | 9.12 µs | 40 |
| lite | search_warm_after_load | json | multi | 935.23 µs | 1.11 ms | 40 |
| lite | search_warm_after_load | json | no_result | 3.63 µs | 4.17 µs | 40 |
| lite | search_warm_after_load | json | repeated | 900.65 µs | 2.71 ms | 100 |
| lite | load_standard | sqlite | - | 23.58 ms | 23.58 ms | 1 |
| lite | search_first_after_load | sqlite | common | 1.34 ms | 1.34 ms | 1 |
| lite | search_warm_after_load | sqlite | common | 790.38 µs | 945.74 µs | 40 |
| lite | search_warm_after_load | sqlite | rare | 7.74 µs | 9.21 µs | 40 |
| lite | search_warm_after_load | sqlite | multi | 937.02 µs | 1.22 ms | 40 |
| lite | search_warm_after_load | sqlite | no_result | 3.79 µs | 4.39 µs | 40 |
| lite | search_warm_after_load | sqlite | repeated | 889.00 µs | 2.61 ms | 100 |

## Memory-mapped loads

| Engine | Metric | Backend | Category | Median | p95 | Samples |
|---|---|---|---|---|---|---|
| core | mmap_load | - | - | 2.69 ms | 2.69 ms | 1 |
| core | search_first_mmap | - | common | 3.46 ms | 3.46 ms | 1 |
| core | search_warm_mmap | - | common | 2.81 ms | 3.26 ms | 40 |
| core | search_warm_mmap | - | rare | 15.15 µs | 16.96 µs | 40 |
| core | search_warm_mmap | - | multi | 3.71 ms | 7.23 ms | 40 |
| core | search_warm_mmap | - | no_result | 4.10 µs | 4.57 µs | 40 |
| core | search_warm_mmap | - | repeated | 3.22 ms | 4.47 ms | 100 |
| lite | mmap_load | - | - | 2.56 ms | 2.56 ms | 1 |
| lite | search_first_mmap | - | common | 1.20 ms | 1.20 ms | 1 |
| lite | search_warm_mmap | - | common | 885.35 µs | 1.07 ms | 40 |
| lite | search_warm_mmap | - | rare | 9.94 µs | 11.49 µs | 40 |
| lite | search_warm_mmap | - | multi | 1.04 ms | 1.25 ms | 40 |
| lite | search_warm_mmap | - | no_result | 3.86 µs | 4.19 µs | 40 |
| lite | search_warm_mmap | - | repeated | 988.78 µs | 1.40 ms | 100 |

## Memory

RSS values are process readings, not exclusive ownership. `n/a` marks capabilities unavailable on this host; they are never reported as zero.

| Engine | Phase | Metric | Scope | Value | Status |
|---|---|---|---|---|---|
| core | build | memory_baseline_rss | process_tree | 6.61 MiB | ok |
| core | build | memory_peak_rss | process_tree | 79.83 MiB | ok |
| core | build | memory_peak_rss_delta | process_tree | 73.21 MiB | ok |
| core | build | memory_stable_rss | self_only | 35.04 MiB | ok |
| core | build | memory_max_processes | process_tree | 3 | ok |
| core | load_json | memory_baseline_rss | process_tree | 6.84 MiB | ok |
| core | load_json | memory_peak_rss | process_tree | 27.66 MiB | ok |
| core | load_json | memory_peak_rss_delta | process_tree | 20.82 MiB | ok |
| core | load_json | memory_stable_rss | self_only | 27.66 MiB | ok |
| core | load_json | memory_max_processes | process_tree | 1 | ok |
| core | load_sqlite | memory_baseline_rss | process_tree | 6.96 MiB | ok |
| core | load_sqlite | memory_peak_rss | process_tree | 30.12 MiB | ok |
| core | load_sqlite | memory_peak_rss_delta | process_tree | 23.17 MiB | ok |
| core | load_sqlite | memory_stable_rss | self_only | 30.12 MiB | ok |
| core | load_sqlite | memory_max_processes | process_tree | 1 | ok |
| core | load_mmap | memory_baseline_rss | process_tree | 6.93 MiB | ok |
| core | load_mmap | memory_peak_rss | process_tree | 26.96 MiB | ok |
| core | load_mmap | memory_peak_rss_delta | process_tree | 20.04 MiB | ok |
| core | load_mmap | memory_stable_rss | self_only | 26.47 MiB | ok |
| core | load_mmap | memory_max_processes | process_tree | 1 | ok |
| lite | build | memory_baseline_rss | process_tree | 7.48 MiB | ok |
| lite | build | memory_peak_rss | process_tree | 52.58 MiB | ok |
| lite | build | memory_peak_rss_delta | process_tree | 45.10 MiB | ok |
| lite | build | memory_stable_rss | self_only | 34.72 MiB | ok |
| lite | build | memory_max_processes | process_tree | 3 | ok |
| lite | load_json | memory_baseline_rss | process_tree | 7.52 MiB | ok |
| lite | load_json | memory_peak_rss | process_tree | 27.63 MiB | ok |
| lite | load_json | memory_peak_rss_delta | process_tree | 20.11 MiB | ok |
| lite | load_json | memory_stable_rss | self_only | 27.63 MiB | ok |
| lite | load_json | memory_max_processes | process_tree | 1 | ok |
| lite | load_sqlite | memory_baseline_rss | process_tree | 7.54 MiB | ok |
| lite | load_sqlite | memory_peak_rss | process_tree | 30.03 MiB | ok |
| lite | load_sqlite | memory_peak_rss_delta | process_tree | 22.49 MiB | ok |
| lite | load_sqlite | memory_stable_rss | self_only | 30.03 MiB | ok |
| lite | load_sqlite | memory_max_processes | process_tree | 1 | ok |
| lite | load_mmap | memory_baseline_rss | process_tree | 7.34 MiB | ok |
| lite | load_mmap | memory_peak_rss | process_tree | 26.92 MiB | ok |
| lite | load_mmap | memory_peak_rss_delta | process_tree | 19.58 MiB | ok |
| lite | load_mmap | memory_stable_rss | self_only | 26.47 MiB | ok |
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
