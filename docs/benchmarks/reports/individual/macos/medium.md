# Lucis benchmark report

> These results describe one machine and one execution environment. They
> are not search-quality measurements or universal performance guarantees.

## Run

| Field | Value |
|---|---|
| Run ID | 20260813T181324Z-f9a50c |
| Started (UTC) | 2026-08-13T18:13:24.881127+00:00 |
| Finished (UTC) | 2026-08-13T18:13:39.895712+00:00 |
| Schema version | 1.0 |

## Environment

| Field | Value |
|---|---|
| python_version | 3.13.2 |
| python_implementation | CPython |
| platform | macOS-26.6.1-arm64-arm-64bit-Mach-O |
| machine | arm64 |
| lucis_version | 0.1.0 |
| cpu_model | Apple M4 |
| logical_cpu_count | 10 |
| total_ram_bytes | 17179869184 (16.00 GiB) |
| memory_mechanisms | resource |
| psutil_version | n/a |
| git_commit | a6ac3de8cf7ca5fdc1e1a07ec539e67660fea61f |
| git_dirty | True |

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
| core | dataset_generation | - | - | 54.47 ms | 54.47 ms | 1 |
| core | index_build | - | - | 106.45 ms | 106.45 ms | 1 |
| core | index_e2e_json | - | - | 260.99 ms | 260.99 ms | 1 |
| core | search_first | - | common | 8.23 ms | 8.23 ms | 1 |
| core | search_warm | - | common | 6.76 ms | 7.98 ms | 40 |
| core | search_warm | - | rare | 10.90 µs | 12.50 µs | 40 |
| core | search_warm | - | multi | 8.32 ms | 9.22 ms | 40 |
| core | search_warm | - | no_result | 1.67 µs | 1.75 µs | 40 |
| core | search_warm | - | repeated | 7.90 ms | 7.95 ms | 100 |
| lite | dataset_generation | - | - | 58.29 ms | 58.29 ms | 1 |
| lite | index_build | - | - | 75.18 ms | 75.18 ms | 1 |
| lite | index_e2e_json | - | - | 210.24 ms | 210.24 ms | 1 |
| lite | search_first | - | common | 5.19 ms | 5.19 ms | 1 |
| lite | search_warm | - | common | 4.33 ms | 5.09 ms | 40 |
| lite | search_warm | - | rare | 8.71 µs | 9.54 µs | 40 |
| lite | search_warm | - | multi | 5.65 ms | 6.25 ms | 40 |
| lite | search_warm | - | no_result | 1.62 µs | 1.71 µs | 40 |
| lite | search_warm | - | repeated | 5.03 ms | 5.13 ms | 100 |

## Persistence

| Engine | Metric | Backend | Category | Median | p95 | Samples |
|---|---|---|---|---|---|---|
| core | json_save | - | - | 141.19 ms | 141.19 ms | 1 |
| core | json_artifact_size | - | - | 6.06 MiB | 6.06 MiB | 1 |
| core | sqlite_save | - | - | 56.11 ms | 56.11 ms | 1 |
| core | sqlite_artifact_size | - | - | 5.18 MiB | 5.18 MiB | 1 |
| core | lcs_write | - | - | 5.31 ms | 5.31 ms | 1 |
| core | lcs_artifact_size | - | - | 2.21 MiB | 2.21 MiB | 1 |
| lite | json_save | - | - | 136.62 ms | 136.62 ms | 1 |
| lite | json_artifact_size | - | - | 5.71 MiB | 5.71 MiB | 1 |
| lite | sqlite_save | - | - | 58.33 ms | 58.33 ms | 1 |
| lite | sqlite_artifact_size | - | - | 5.18 MiB | 5.18 MiB | 1 |
| lite | lcs_write | - | - | 4.91 ms | 4.91 ms | 1 |
| lite | lcs_artifact_size | - | - | 2.14 MiB | 2.14 MiB | 1 |

## Standard loads

| Engine | Metric | Backend | Category | Median | p95 | Samples |
|---|---|---|---|---|---|---|
| core | load_standard | json | - | 59.74 ms | 59.74 ms | 1 |
| core | search_first_after_load | json | common | 7.82 ms | 7.82 ms | 1 |
| core | search_warm_after_load | json | common | 6.50 ms | 7.74 ms | 40 |
| core | search_warm_after_load | json | rare | 10.67 µs | 11.83 µs | 40 |
| core | search_warm_after_load | json | multi | 7.87 ms | 9.07 ms | 40 |
| core | search_warm_after_load | json | no_result | 1.54 µs | 1.79 µs | 40 |
| core | search_warm_after_load | json | repeated | 7.75 ms | 7.79 ms | 100 |
| core | load_standard | sqlite | - | 110.23 ms | 110.23 ms | 1 |
| core | search_first_after_load | sqlite | common | 7.99 ms | 7.99 ms | 1 |
| core | search_warm_after_load | sqlite | common | 6.57 ms | 7.85 ms | 40 |
| core | search_warm_after_load | sqlite | rare | 10.65 µs | 11.71 µs | 40 |
| core | search_warm_after_load | sqlite | multi | 8.27 ms | 9.16 ms | 40 |
| core | search_warm_after_load | sqlite | no_result | 1.67 µs | 1.83 µs | 40 |
| core | search_warm_after_load | sqlite | repeated | 7.79 ms | 8.21 ms | 100 |
| lite | load_standard | json | - | 58.45 ms | 58.45 ms | 1 |
| lite | search_first_after_load | json | common | 5.10 ms | 5.10 ms | 1 |
| lite | search_warm_after_load | json | common | 4.24 ms | 5.02 ms | 40 |
| lite | search_warm_after_load | json | rare | 8.48 µs | 9.33 µs | 40 |
| lite | search_warm_after_load | json | multi | 5.56 ms | 6.16 ms | 40 |
| lite | search_warm_after_load | json | no_result | 1.58 µs | 1.67 µs | 40 |
| lite | search_warm_after_load | json | repeated | 4.98 ms | 5.08 ms | 100 |
| lite | load_standard | sqlite | - | 67.79 ms | 67.79 ms | 1 |
| lite | search_first_after_load | sqlite | common | 5.11 ms | 5.11 ms | 1 |
| lite | search_warm_after_load | sqlite | common | 4.33 ms | 4.98 ms | 40 |
| lite | search_warm_after_load | sqlite | rare | 8.46 µs | 9.33 µs | 40 |
| lite | search_warm_after_load | sqlite | multi | 5.66 ms | 6.30 ms | 40 |
| lite | search_warm_after_load | sqlite | no_result | 1.58 µs | 1.71 µs | 40 |
| lite | search_warm_after_load | sqlite | repeated | 5.01 ms | 5.11 ms | 100 |

## Memory-mapped loads

| Engine | Metric | Backend | Category | Median | p95 | Samples |
|---|---|---|---|---|---|---|
| core | mmap_load | - | - | 9.15 ms | 9.15 ms | 1 |
| core | search_first_mmap | - | common | 15.19 ms | 15.19 ms | 1 |
| core | search_warm_mmap | - | common | 12.54 ms | 15.09 ms | 40 |
| core | search_warm_mmap | - | rare | 17.73 µs | 19.83 µs | 40 |
| core | search_warm_mmap | - | multi | 16.16 ms | 20.02 ms | 40 |
| core | search_warm_mmap | - | no_result | 1.79 µs | 1.96 µs | 40 |
| core | search_warm_mmap | - | repeated | 14.97 ms | 15.52 ms | 100 |
| lite | mmap_load | - | - | 9.87 ms | 9.87 ms | 1 |
| lite | search_first_mmap | - | common | 5.32 ms | 5.32 ms | 1 |
| lite | search_warm_mmap | - | common | 5.00 ms | 6.45 ms | 40 |
| lite | search_warm_mmap | - | rare | 10.77 µs | 11.83 µs | 40 |
| lite | search_warm_mmap | - | multi | 6.17 ms | 7.66 ms | 40 |
| lite | search_warm_mmap | - | no_result | 1.67 µs | 2.08 µs | 40 |
| lite | search_warm_mmap | - | repeated | 5.83 ms | 6.98 ms | 100 |

## Memory

RSS values are process readings, not exclusive ownership. `n/a` marks capabilities unavailable on this host; they are never reported as zero.

| Engine | Phase | Metric | Scope | Value | Status |
|---|---|---|---|---|---|
| core | build | memory_baseline_rss | process_tree | n/a | unavailable |
| core | build | memory_peak_rss | self_only | 84.61 MiB | ok |
| core | build | memory_peak_rss_delta | process_tree | n/a | unavailable |
| core | build | memory_stable_rss | self_only | n/a | unavailable |
| core | build | memory_max_processes | process_tree | n/a | unavailable |
| core | load_json | memory_baseline_rss | process_tree | n/a | unavailable |
| core | load_json | memory_peak_rss | self_only | 62.42 MiB | ok |
| core | load_json | memory_peak_rss_delta | process_tree | n/a | unavailable |
| core | load_json | memory_stable_rss | self_only | n/a | unavailable |
| core | load_json | memory_max_processes | process_tree | n/a | unavailable |
| core | load_sqlite | memory_baseline_rss | process_tree | n/a | unavailable |
| core | load_sqlite | memory_peak_rss | self_only | 62.86 MiB | ok |
| core | load_sqlite | memory_peak_rss_delta | process_tree | n/a | unavailable |
| core | load_sqlite | memory_stable_rss | self_only | n/a | unavailable |
| core | load_sqlite | memory_max_processes | process_tree | n/a | unavailable |
| core | load_mmap | memory_baseline_rss | process_tree | n/a | unavailable |
| core | load_mmap | memory_peak_rss | self_only | 42.62 MiB | ok |
| core | load_mmap | memory_peak_rss_delta | process_tree | n/a | unavailable |
| core | load_mmap | memory_stable_rss | self_only | n/a | unavailable |
| core | load_mmap | memory_max_processes | process_tree | n/a | unavailable |
| lite | build | memory_baseline_rss | process_tree | n/a | unavailable |
| lite | build | memory_peak_rss | self_only | 82.70 MiB | ok |
| lite | build | memory_peak_rss_delta | process_tree | n/a | unavailable |
| lite | build | memory_stable_rss | self_only | n/a | unavailable |
| lite | build | memory_max_processes | process_tree | n/a | unavailable |
| lite | load_json | memory_baseline_rss | process_tree | n/a | unavailable |
| lite | load_json | memory_peak_rss | self_only | 60.83 MiB | ok |
| lite | load_json | memory_peak_rss_delta | process_tree | n/a | unavailable |
| lite | load_json | memory_stable_rss | self_only | n/a | unavailable |
| lite | load_json | memory_max_processes | process_tree | n/a | unavailable |
| lite | load_sqlite | memory_baseline_rss | process_tree | n/a | unavailable |
| lite | load_sqlite | memory_peak_rss | self_only | 61.20 MiB | ok |
| lite | load_sqlite | memory_peak_rss_delta | process_tree | n/a | unavailable |
| lite | load_sqlite | memory_stable_rss | self_only | n/a | unavailable |
| lite | load_sqlite | memory_max_processes | process_tree | n/a | unavailable |
| lite | load_mmap | memory_baseline_rss | process_tree | n/a | unavailable |
| lite | load_mmap | memory_peak_rss | self_only | 42.25 MiB | ok |
| lite | load_mmap | memory_peak_rss_delta | process_tree | n/a | unavailable |
| lite | load_mmap | memory_stable_rss | self_only | n/a | unavailable |
| lite | load_mmap | memory_max_processes | process_tree | n/a | unavailable |

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
- current RSS is unavailable on this platform without psutil
- peak is a process-lifetime maximum, not a phase reading
- process counting requires the optional psutil dependency
- process-tree baseline requires the optional psutil dependency
- process-tree sampling requires the optional psutil dependency
- self-only peak excludes child worker processes
