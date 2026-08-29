# Lucis benchmark report

> These results describe one machine and one execution environment. They
> are not search-quality measurements or universal performance guarantees.

## Run

| Field | Value |
|---|---|
| Run ID | 20260803T002038Z-ff47a3 |
| Started (UTC) | 2026-08-03T00:20:38.203762+00:00 |
| Finished (UTC) | 2026-08-03T00:21:21.145991+00:00 |
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
| core | dataset_generation | - | - | 185.19 ms | 185.19 ms | 1 |
| core | index_build | - | - | 417.21 ms | 417.21 ms | 1 |
| core | index_e2e_json | - | - | 1.20 s | 1.20 s | 1 |
| core | search_first | - | common | 28.24 ms | 28.24 ms | 1 |
| core | search_warm | - | common | 26.95 ms | 34.05 ms | 40 |
| core | search_warm | - | rare | 35.55 µs | 38.30 µs | 40 |
| core | search_warm | - | multi | 31.80 ms | 43.40 ms | 40 |
| core | search_warm | - | no_result | 5.35 µs | 6.10 µs | 40 |
| core | search_warm | - | repeated | 29.58 ms | 34.07 ms | 100 |
| lite | dataset_generation | - | - | 123.64 ms | 123.64 ms | 1 |
| lite | index_build | - | - | 214.30 ms | 214.30 ms | 1 |
| lite | index_e2e_json | - | - | 589.42 ms | 589.42 ms | 1 |
| lite | search_first | - | common | 13.96 ms | 13.96 ms | 1 |
| lite | search_warm | - | common | 10.04 ms | 13.13 ms | 40 |
| lite | search_warm | - | rare | 20.15 µs | 22.20 µs | 40 |
| lite | search_warm | - | multi | 12.30 ms | 17.56 ms | 40 |
| lite | search_warm | - | no_result | 3.80 µs | 4.20 µs | 40 |
| lite | search_warm | - | repeated | 10.95 ms | 14.63 ms | 100 |

## Persistence

| Engine | Metric | Backend | Category | Median | p95 | Samples |
|---|---|---|---|---|---|---|
| core | json_save | - | - | 462.38 ms | 462.38 ms | 1 |
| core | json_artifact_size | - | - | 6.31 MiB | 6.31 MiB | 1 |
| core | sqlite_save | - | - | 168.05 ms | 168.05 ms | 1 |
| core | sqlite_artifact_size | - | - | 4.68 MiB | 4.68 MiB | 1 |
| core | lcs_write | - | - | 15.37 ms | 15.37 ms | 1 |
| core | lcs_artifact_size | - | - | 2.21 MiB | 2.21 MiB | 1 |
| lite | json_save | - | - | 373.86 ms | 373.86 ms | 1 |
| lite | json_artifact_size | - | - | 5.96 MiB | 5.96 MiB | 1 |
| lite | sqlite_save | - | - | 142.46 ms | 142.46 ms | 1 |
| lite | sqlite_artifact_size | - | - | 4.68 MiB | 4.68 MiB | 1 |
| lite | lcs_write | - | - | 17.40 ms | 17.40 ms | 1 |
| lite | lcs_artifact_size | - | - | 2.14 MiB | 2.14 MiB | 1 |

## Standard loads

| Engine | Metric | Backend | Category | Median | p95 | Samples |
|---|---|---|---|---|---|---|
| core | load_standard | json | - | 153.15 ms | 153.15 ms | 1 |
| core | search_first_after_load | json | common | 19.09 ms | 19.09 ms | 1 |
| core | search_warm_after_load | json | common | 17.35 ms | 21.91 ms | 40 |
| core | search_warm_after_load | json | rare | 27.45 µs | 30.60 µs | 40 |
| core | search_warm_after_load | json | multi | 21.34 ms | 26.00 ms | 40 |
| core | search_warm_after_load | json | no_result | 4.20 µs | 4.80 µs | 40 |
| core | search_warm_after_load | json | repeated | 18.79 ms | 24.74 ms | 100 |
| core | load_standard | sqlite | - | 270.39 ms | 270.39 ms | 1 |
| core | search_first_after_load | sqlite | common | 20.21 ms | 20.21 ms | 1 |
| core | search_warm_after_load | sqlite | common | 17.24 ms | 24.33 ms | 40 |
| core | search_warm_after_load | sqlite | rare | 26.65 µs | 29.60 µs | 40 |
| core | search_warm_after_load | sqlite | multi | 21.26 ms | 26.69 ms | 40 |
| core | search_warm_after_load | sqlite | no_result | 7.10 µs | 7.70 µs | 40 |
| core | search_warm_after_load | sqlite | repeated | 19.90 ms | 26.56 ms | 100 |
| lite | load_standard | json | - | 173.18 ms | 173.18 ms | 1 |
| lite | search_first_after_load | json | common | 14.03 ms | 14.03 ms | 1 |
| lite | search_warm_after_load | json | common | 9.84 ms | 13.22 ms | 40 |
| lite | search_warm_after_load | json | rare | 20.25 µs | 22.20 µs | 40 |
| lite | search_warm_after_load | json | multi | 13.37 ms | 16.02 ms | 40 |
| lite | search_warm_after_load | json | no_result | 3.80 µs | 4.50 µs | 40 |
| lite | search_warm_after_load | json | repeated | 13.01 ms | 14.71 ms | 100 |
| lite | load_standard | sqlite | - | 165.48 ms | 165.48 ms | 1 |
| lite | search_first_after_load | sqlite | common | 15.41 ms | 15.41 ms | 1 |
| lite | search_warm_after_load | sqlite | common | 9.86 ms | 12.43 ms | 40 |
| lite | search_warm_after_load | sqlite | rare | 32.25 µs | 43.70 µs | 40 |
| lite | search_warm_after_load | sqlite | multi | 12.70 ms | 16.11 ms | 40 |
| lite | search_warm_after_load | sqlite | no_result | 4.10 µs | 4.40 µs | 40 |
| lite | search_warm_after_load | sqlite | repeated | 11.30 ms | 14.68 ms | 100 |

## Memory-mapped loads

| Engine | Metric | Backend | Category | Median | p95 | Samples |
|---|---|---|---|---|---|---|
| core | mmap_load | - | - | 4.45 ms | 4.45 ms | 1 |
| core | search_first_mmap | - | common | 47.74 ms | 47.74 ms | 1 |
| core | search_warm_mmap | - | common | 35.26 ms | 46.42 ms | 40 |
| core | search_warm_mmap | - | rare | 46.25 µs | 57.90 µs | 40 |
| core | search_warm_mmap | - | multi | 44.45 ms | 61.38 ms | 40 |
| core | search_warm_mmap | - | no_result | 4.30 µs | 5.00 µs | 40 |
| core | search_warm_mmap | - | repeated | 40.84 ms | 47.62 ms | 100 |
| lite | mmap_load | - | - | 3.29 ms | 3.29 ms | 1 |
| lite | search_first_mmap | - | common | 15.56 ms | 15.56 ms | 1 |
| lite | search_warm_mmap | - | common | 10.47 ms | 12.76 ms | 40 |
| lite | search_warm_mmap | - | rare | 52.30 µs | 55.30 µs | 40 |
| lite | search_warm_mmap | - | multi | 13.53 ms | 17.85 ms | 40 |
| lite | search_warm_mmap | - | no_result | 4.20 µs | 4.50 µs | 40 |
| lite | search_warm_mmap | - | repeated | 11.39 ms | 14.81 ms | 100 |

## Memory

RSS values are process readings, not exclusive ownership. `n/a` marks capabilities unavailable on this host; they are never reported as zero.

| Engine | Phase | Metric | Scope | Value | Status |
|---|---|---|---|---|---|
| core | build | memory_baseline_rss | process_tree | 8.04 MiB | ok |
| core | build | memory_peak_rss | process_tree | 71.84 MiB | ok |
| core | build | memory_peak_rss_delta | process_tree | 63.80 MiB | ok |
| core | build | memory_stable_rss | self_only | 59.80 MiB | ok |
| core | build | memory_max_processes | process_tree | 1 | ok |
| core | load_json | memory_baseline_rss | process_tree | 7.95 MiB | ok |
| core | load_json | memory_peak_rss | process_tree | 47.59 MiB | ok |
| core | load_json | memory_peak_rss_delta | process_tree | 39.64 MiB | ok |
| core | load_json | memory_stable_rss | self_only | 37.20 MiB | ok |
| core | load_json | memory_max_processes | process_tree | 1 | ok |
| core | load_sqlite | memory_baseline_rss | process_tree | 8.02 MiB | ok |
| core | load_sqlite | memory_peak_rss | process_tree | 59.29 MiB | ok |
| core | load_sqlite | memory_peak_rss_delta | process_tree | 51.26 MiB | ok |
| core | load_sqlite | memory_stable_rss | self_only | 41.04 MiB | ok |
| core | load_sqlite | memory_max_processes | process_tree | 1 | ok |
| core | load_mmap | memory_baseline_rss | process_tree | 8.02 MiB | ok |
| core | load_mmap | memory_peak_rss | process_tree | 37.29 MiB | ok |
| core | load_mmap | memory_peak_rss_delta | process_tree | 29.28 MiB | ok |
| core | load_mmap | memory_stable_rss | self_only | 35.24 MiB | ok |
| core | load_mmap | memory_max_processes | process_tree | 1 | ok |
| lite | build | memory_baseline_rss | process_tree | 8.03 MiB | ok |
| lite | build | memory_peak_rss | process_tree | 67.98 MiB | ok |
| lite | build | memory_peak_rss_delta | process_tree | 59.95 MiB | ok |
| lite | build | memory_stable_rss | self_only | 55.70 MiB | ok |
| lite | build | memory_max_processes | process_tree | 1 | ok |
| lite | load_json | memory_baseline_rss | process_tree | 8.91 MiB | ok |
| lite | load_json | memory_peak_rss | process_tree | 45.16 MiB | ok |
| lite | load_json | memory_peak_rss_delta | process_tree | 36.25 MiB | ok |
| lite | load_json | memory_stable_rss | self_only | 36.61 MiB | ok |
| lite | load_json | memory_max_processes | process_tree | 1 | ok |
| lite | load_sqlite | memory_baseline_rss | process_tree | 8.02 MiB | ok |
| lite | load_sqlite | memory_peak_rss | process_tree | 58.06 MiB | ok |
| lite | load_sqlite | memory_peak_rss_delta | process_tree | 50.04 MiB | ok |
| lite | load_sqlite | memory_stable_rss | self_only | 40.32 MiB | ok |
| lite | load_sqlite | memory_max_processes | process_tree | 1 | ok |
| lite | load_mmap | memory_baseline_rss | process_tree | 8.01 MiB | ok |
| lite | load_mmap | memory_peak_rss | process_tree | 36.05 MiB | ok |
| lite | load_mmap | memory_peak_rss_delta | process_tree | 28.05 MiB | ok |
| lite | load_mmap | memory_stable_rss | self_only | 34.71 MiB | ok |
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
