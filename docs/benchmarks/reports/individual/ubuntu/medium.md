# Yeny benchmark report

> These results describe one machine and one execution environment. They
> are not search-quality measurements or universal performance guarantees.

## Run

| Field | Value |
|---|---|
| Run ID | 20260730T212433Z-6cc3f4 |
| Started (UTC) | 2026-07-30T21:24:33.734818+00:00 |
| Finished (UTC) | 2026-07-30T21:25:21.841901+00:00 |
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
| core | dataset_generation | - | - | 265.73 ms | 265.73 ms | 1 |
| core | index_build | - | - | 415.28 ms | 415.28 ms | 1 |
| core | index_e2e_json | - | - | 681.17 ms | 681.17 ms | 1 |
| core | search_first | - | common | 19.93 ms | 19.93 ms | 1 |
| core | search_warm | - | common | 20.44 ms | 29.88 ms | 40 |
| core | search_warm | - | rare | 33.49 µs | 61.48 µs | 40 |
| core | search_warm | - | multi | 21.24 ms | 32.94 ms | 40 |
| core | search_warm | - | no_result | 3.94 µs | 4.33 µs | 40 |
| core | search_warm | - | repeated | 29.69 ms | 37.73 ms | 100 |
| lite | dataset_generation | - | - | 163.16 ms | 163.16 ms | 1 |
| lite | index_build | - | - | 318.61 ms | 318.61 ms | 1 |
| lite | index_e2e_json | - | - | 724.88 ms | 724.88 ms | 1 |
| lite | search_first | - | common | 25.01 ms | 25.01 ms | 1 |
| lite | search_warm | - | common | 10.29 ms | 22.56 ms | 40 |
| lite | search_warm | - | rare | 19.59 µs | 22.32 µs | 40 |
| lite | search_warm | - | multi | 13.76 ms | 29.11 ms | 40 |
| lite | search_warm | - | no_result | 3.58 µs | 3.97 µs | 40 |
| lite | search_warm | - | repeated | 11.94 ms | 20.70 ms | 100 |

## Persistence

| Engine | Metric | Backend | Category | Median | p95 | Samples |
|---|---|---|---|---|---|---|
| core | json_save | - | - | 314.52 ms | 314.52 ms | 1 |
| core | json_artifact_size | - | - | 6.06 MiB | 6.06 MiB | 1 |
| core | sqlite_save | - | - | 174.20 ms | 174.20 ms | 1 |
| core | sqlite_artifact_size | - | - | 4.68 MiB | 4.68 MiB | 1 |
| core | yny_write | - | - | 15.80 ms | 15.80 ms | 1 |
| core | yny_artifact_size | - | - | 2.21 MiB | 2.21 MiB | 1 |
| lite | json_save | - | - | 354.43 ms | 354.43 ms | 1 |
| lite | json_artifact_size | - | - | 5.71 MiB | 5.71 MiB | 1 |
| lite | sqlite_save | - | - | 149.81 ms | 149.81 ms | 1 |
| lite | sqlite_artifact_size | - | - | 4.68 MiB | 4.68 MiB | 1 |
| lite | yny_write | - | - | 14.88 ms | 14.88 ms | 1 |
| lite | yny_artifact_size | - | - | 2.14 MiB | 2.14 MiB | 1 |

## Standard loads

| Engine | Metric | Backend | Category | Median | p95 | Samples |
|---|---|---|---|---|---|---|
| core | load_standard | json | - | 201.96 ms | 201.96 ms | 1 |
| core | search_first_after_load | json | common | 34.21 ms | 34.21 ms | 1 |
| core | search_warm_after_load | json | common | 24.14 ms | 30.36 ms | 40 |
| core | search_warm_after_load | json | rare | 26.26 µs | 28.72 µs | 40 |
| core | search_warm_after_load | json | multi | 20.03 ms | 31.73 ms | 40 |
| core | search_warm_after_load | json | no_result | 3.97 µs | 4.32 µs | 40 |
| core | search_warm_after_load | json | repeated | 21.33 ms | 39.40 ms | 100 |
| core | load_standard | sqlite | - | 369.87 ms | 369.87 ms | 1 |
| core | search_first_after_load | sqlite | common | 31.62 ms | 31.62 ms | 1 |
| core | search_warm_after_load | sqlite | common | 20.24 ms | 47.08 ms | 40 |
| core | search_warm_after_load | sqlite | rare | 42.85 µs | 64.38 µs | 40 |
| core | search_warm_after_load | sqlite | multi | 29.80 ms | 47.69 ms | 40 |
| core | search_warm_after_load | sqlite | no_result | 11.67 µs | 13.02 µs | 40 |
| core | search_warm_after_load | sqlite | repeated | 24.05 ms | 42.94 ms | 100 |
| lite | load_standard | json | - | 257.37 ms | 257.37 ms | 1 |
| lite | search_first_after_load | json | common | 11.43 ms | 11.43 ms | 1 |
| lite | search_warm_after_load | json | common | 10.39 ms | 13.36 ms | 40 |
| lite | search_warm_after_load | json | rare | 19.95 µs | 22.07 µs | 40 |
| lite | search_warm_after_load | json | multi | 14.81 ms | 29.01 ms | 40 |
| lite | search_warm_after_load | json | no_result | 10.56 µs | 13.06 µs | 40 |
| lite | search_warm_after_load | json | repeated | 11.56 ms | 19.20 ms | 100 |
| lite | load_standard | sqlite | - | 275.06 ms | 275.06 ms | 1 |
| lite | search_first_after_load | sqlite | common | 17.52 ms | 17.52 ms | 1 |
| lite | search_warm_after_load | sqlite | common | 15.64 ms | 20.35 ms | 40 |
| lite | search_warm_after_load | sqlite | rare | 54.74 µs | 61.94 µs | 40 |
| lite | search_warm_after_load | sqlite | multi | 18.79 ms | 25.12 ms | 40 |
| lite | search_warm_after_load | sqlite | no_result | 3.69 µs | 4.00 µs | 40 |
| lite | search_warm_after_load | sqlite | repeated | 12.77 ms | 21.63 ms | 100 |

## Memory-mapped loads

| Engine | Metric | Backend | Category | Median | p95 | Samples |
|---|---|---|---|---|---|---|
| core | mmap_load | - | - | 4.72 ms | 4.72 ms | 1 |
| core | search_first_mmap | - | common | 38.18 ms | 38.18 ms | 1 |
| core | search_warm_mmap | - | common | 33.71 ms | 61.74 ms | 40 |
| core | search_warm_mmap | - | rare | 95.39 µs | 116.48 µs | 40 |
| core | search_warm_mmap | - | multi | 44.81 ms | 63.31 ms | 40 |
| core | search_warm_mmap | - | no_result | 9.62 µs | 11.85 µs | 40 |
| core | search_warm_mmap | - | repeated | 49.03 ms | 99.23 ms | 100 |
| lite | mmap_load | - | - | 3.81 ms | 3.81 ms | 1 |
| lite | search_first_mmap | - | common | 12.76 ms | 12.76 ms | 1 |
| lite | search_warm_mmap | - | common | 15.34 ms | 19.36 ms | 40 |
| lite | search_warm_mmap | - | rare | 67.73 µs | 77.35 µs | 40 |
| lite | search_warm_mmap | - | multi | 13.59 ms | 20.91 ms | 40 |
| lite | search_warm_mmap | - | no_result | 9.16 µs | 13.97 µs | 40 |
| lite | search_warm_mmap | - | repeated | 20.11 ms | 25.78 ms | 100 |

## Memory

RSS values are process readings, not exclusive ownership. `n/a` marks capabilities unavailable on this host; they are never reported as zero.

| Engine | Phase | Metric | Scope | Value | Status |
|---|---|---|---|---|---|
| core | build | memory_baseline_rss | process_tree | 6.89 MiB | ok |
| core | build | memory_peak_rss | process_tree | 191.64 MiB | ok |
| core | build | memory_peak_rss_delta | process_tree | 184.75 MiB | ok |
| core | build | memory_stable_rss | self_only | 80.73 MiB | ok |
| core | build | memory_max_processes | process_tree | 3 | ok |
| core | load_json | memory_baseline_rss | process_tree | 6.96 MiB | ok |
| core | load_json | memory_peak_rss | process_tree | 44.29 MiB | ok |
| core | load_json | memory_peak_rss_delta | process_tree | 37.34 MiB | ok |
| core | load_json | memory_stable_rss | self_only | 43.17 MiB | ok |
| core | load_json | memory_max_processes | process_tree | 1 | ok |
| core | load_sqlite | memory_baseline_rss | process_tree | 6.00 MiB | ok |
| core | load_sqlite | memory_peak_rss | process_tree | 56.30 MiB | ok |
| core | load_sqlite | memory_peak_rss_delta | process_tree | 50.31 MiB | ok |
| core | load_sqlite | memory_stable_rss | self_only | 51.70 MiB | ok |
| core | load_sqlite | memory_max_processes | process_tree | 1 | ok |
| core | load_mmap | memory_baseline_rss | process_tree | 7.66 MiB | ok |
| core | load_mmap | memory_peak_rss | process_tree | 37.14 MiB | ok |
| core | load_mmap | memory_peak_rss_delta | process_tree | 29.47 MiB | ok |
| core | load_mmap | memory_stable_rss | self_only | 36.19 MiB | ok |
| core | load_mmap | memory_max_processes | process_tree | 1 | ok |
| lite | build | memory_baseline_rss | process_tree | 6.90 MiB | ok |
| lite | build | memory_peak_rss | process_tree | 179.88 MiB | ok |
| lite | build | memory_peak_rss_delta | process_tree | 172.97 MiB | ok |
| lite | build | memory_stable_rss | self_only | 76.78 MiB | ok |
| lite | build | memory_max_processes | process_tree | 3 | ok |
| lite | load_json | memory_baseline_rss | process_tree | 7.60 MiB | ok |
| lite | load_json | memory_peak_rss | process_tree | 43.83 MiB | ok |
| lite | load_json | memory_peak_rss_delta | process_tree | 36.23 MiB | ok |
| lite | load_json | memory_stable_rss | self_only | 42.04 MiB | ok |
| lite | load_json | memory_max_processes | process_tree | 1 | ok |
| lite | load_sqlite | memory_baseline_rss | process_tree | 7.57 MiB | ok |
| lite | load_sqlite | memory_peak_rss | process_tree | 54.35 MiB | ok |
| lite | load_sqlite | memory_peak_rss_delta | process_tree | 46.79 MiB | ok |
| lite | load_sqlite | memory_stable_rss | self_only | 50.96 MiB | ok |
| lite | load_sqlite | memory_max_processes | process_tree | 1 | ok |
| lite | load_mmap | memory_baseline_rss | process_tree | 6.86 MiB | ok |
| lite | load_mmap | memory_peak_rss | process_tree | 36.61 MiB | ok |
| lite | load_mmap | memory_peak_rss_delta | process_tree | 29.74 MiB | ok |
| lite | load_mmap | memory_stable_rss | self_only | 35.73 MiB | ok |
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
