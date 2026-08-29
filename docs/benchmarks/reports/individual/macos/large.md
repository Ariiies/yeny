# Lucis benchmark report

> These results describe one machine and one execution environment. They
> are not search-quality measurements or universal performance guarantees.

## Run

| Field | Value |
|---|---|
| Run ID | 20260813T181345Z-ba1ad8 |
| Started (UTC) | 2026-08-13T18:13:45.007185+00:00 |
| Finished (UTC) | 2026-08-13T18:16:27.423617+00:00 |
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
| core | dataset_generation | - | - | 579.75 ms | 579.75 ms | 1 |
| core | index_build | - | - | 1.17 s | 1.17 s | 1 |
| core | index_e2e_json | - | - | 2.58 s | 2.58 s | 1 |
| core | search_first | - | common | 89.99 ms | 89.99 ms | 1 |
| core | search_warm | - | common | 75.04 ms | 93.00 ms | 40 |
| core | search_warm | - | rare | 96.31 µs | 98.08 µs | 40 |
| core | search_warm | - | multi | 90.09 ms | 114.44 ms | 40 |
| core | search_warm | - | no_result | 1.67 µs | 1.83 µs | 40 |
| core | search_warm | - | repeated | 88.18 ms | 90.44 ms | 100 |
| lite | dataset_generation | - | - | 564.31 ms | 564.31 ms | 1 |
| lite | index_build | - | - | 774.07 ms | 774.07 ms | 1 |
| lite | index_e2e_json | - | - | 2.19 s | 2.19 s | 1 |
| lite | search_first | - | common | 57.02 ms | 57.02 ms | 1 |
| lite | search_warm | - | common | 48.69 ms | 59.90 ms | 40 |
| lite | search_warm | - | rare | 60.19 µs | 61.17 µs | 40 |
| lite | search_warm | - | multi | 60.50 ms | 75.22 ms | 40 |
| lite | search_warm | - | no_result | 1.62 µs | 1.75 µs | 40 |
| lite | search_warm | - | repeated | 56.65 ms | 61.56 ms | 100 |

## Persistence

| Engine | Metric | Backend | Category | Median | p95 | Samples |
|---|---|---|---|---|---|---|
| core | json_save | - | - | 1.50 s | 1.50 s | 1 |
| core | json_artifact_size | - | - | 62.65 MiB | 62.65 MiB | 1 |
| core | sqlite_save | - | - | 509.68 ms | 509.68 ms | 1 |
| core | sqlite_artifact_size | - | - | 51.16 MiB | 51.16 MiB | 1 |
| core | lcs_write | - | - | 28.36 ms | 28.36 ms | 1 |
| core | lcs_artifact_size | - | - | 20.78 MiB | 20.78 MiB | 1 |
| lite | json_save | - | - | 1.34 s | 1.34 s | 1 |
| lite | json_artifact_size | - | - | 59.15 MiB | 59.15 MiB | 1 |
| lite | sqlite_save | - | - | 502.06 ms | 502.06 ms | 1 |
| lite | sqlite_artifact_size | - | - | 51.16 MiB | 51.16 MiB | 1 |
| lite | lcs_write | - | - | 23.44 ms | 23.44 ms | 1 |
| lite | lcs_artifact_size | - | - | 20.01 MiB | 20.01 MiB | 1 |

## Standard loads

| Engine | Metric | Backend | Category | Median | p95 | Samples |
|---|---|---|---|---|---|---|
| core | load_standard | json | - | 624.64 ms | 624.64 ms | 1 |
| core | search_first_after_load | json | common | 86.99 ms | 86.99 ms | 1 |
| core | search_warm_after_load | json | common | 71.17 ms | 89.88 ms | 40 |
| core | search_warm_after_load | json | rare | 93.92 µs | 95.50 µs | 40 |
| core | search_warm_after_load | json | multi | 90.17 ms | 106.72 ms | 40 |
| core | search_warm_after_load | json | no_result | 1.67 µs | 2.04 µs | 40 |
| core | search_warm_after_load | json | repeated | 85.96 ms | 90.28 ms | 100 |
| core | load_standard | sqlite | - | 1.24 s | 1.24 s | 1 |
| core | search_first_after_load | sqlite | common | 92.00 ms | 92.00 ms | 1 |
| core | search_warm_after_load | sqlite | common | 76.56 ms | 92.34 ms | 40 |
| core | search_warm_after_load | sqlite | rare | 96.27 µs | 104.46 µs | 40 |
| core | search_warm_after_load | sqlite | multi | 92.12 ms | 111.48 ms | 40 |
| core | search_warm_after_load | sqlite | no_result | 1.75 µs | 1.88 µs | 40 |
| core | search_warm_after_load | sqlite | repeated | 94.35 ms | 107.65 ms | 100 |
| lite | load_standard | json | - | 773.04 ms | 773.04 ms | 1 |
| lite | search_first_after_load | json | common | 64.72 ms | 64.72 ms | 1 |
| lite | search_warm_after_load | json | common | 49.71 ms | 60.06 ms | 40 |
| lite | search_warm_after_load | json | rare | 58.40 µs | 60.00 µs | 40 |
| lite | search_warm_after_load | json | multi | 61.17 ms | 76.28 ms | 40 |
| lite | search_warm_after_load | json | no_result | 1.58 µs | 1.71 µs | 40 |
| lite | search_warm_after_load | json | repeated | 57.18 ms | 64.58 ms | 100 |
| lite | load_standard | sqlite | - | 786.50 ms | 786.50 ms | 1 |
| lite | search_first_after_load | sqlite | common | 56.56 ms | 56.56 ms | 1 |
| lite | search_warm_after_load | sqlite | common | 51.62 ms | 66.24 ms | 40 |
| lite | search_warm_after_load | sqlite | rare | 58.98 µs | 60.33 µs | 40 |
| lite | search_warm_after_load | sqlite | multi | 61.62 ms | 75.19 ms | 40 |
| lite | search_warm_after_load | sqlite | no_result | 1.54 µs | 1.62 µs | 40 |
| lite | search_warm_after_load | sqlite | repeated | 59.03 ms | 65.55 ms | 100 |

## Memory-mapped loads

| Engine | Metric | Backend | Category | Median | p95 | Samples |
|---|---|---|---|---|---|---|
| core | mmap_load | - | - | 17.12 ms | 17.12 ms | 1 |
| core | search_first_mmap | - | common | 185.71 ms | 185.71 ms | 1 |
| core | search_warm_mmap | - | common | 141.10 ms | 163.03 ms | 40 |
| core | search_warm_mmap | - | rare | 177.87 µs | 181.50 µs | 40 |
| core | search_warm_mmap | - | multi | 174.99 ms | 216.14 ms | 40 |
| core | search_warm_mmap | - | no_result | 1.77 µs | 1.96 µs | 40 |
| core | search_warm_mmap | - | repeated | 160.55 ms | 184.76 ms | 100 |
| lite | mmap_load | - | - | 10.57 ms | 10.57 ms | 1 |
| lite | search_first_mmap | - | common | 62.38 ms | 62.38 ms | 1 |
| lite | search_warm_mmap | - | common | 47.58 ms | 58.34 ms | 40 |
| lite | search_warm_mmap | - | rare | 64.69 µs | 65.79 µs | 40 |
| lite | search_warm_mmap | - | multi | 67.08 ms | 86.42 ms | 40 |
| lite | search_warm_mmap | - | no_result | 1.62 µs | 1.67 µs | 40 |
| lite | search_warm_mmap | - | repeated | 57.77 ms | 60.61 ms | 100 |

## Memory

RSS values are process readings, not exclusive ownership. `n/a` marks capabilities unavailable on this host; they are never reported as zero.

| Engine | Phase | Metric | Scope | Value | Status |
|---|---|---|---|---|---|
| core | build | memory_baseline_rss | process_tree | n/a | unavailable |
| core | build | memory_peak_rss | self_only | 519.50 MiB | ok |
| core | build | memory_peak_rss_delta | process_tree | n/a | unavailable |
| core | build | memory_stable_rss | self_only | n/a | unavailable |
| core | build | memory_max_processes | process_tree | n/a | unavailable |
| core | load_json | memory_baseline_rss | process_tree | n/a | unavailable |
| core | load_json | memory_peak_rss | self_only | 402.27 MiB | ok |
| core | load_json | memory_peak_rss_delta | process_tree | n/a | unavailable |
| core | load_json | memory_stable_rss | self_only | n/a | unavailable |
| core | load_json | memory_max_processes | process_tree | n/a | unavailable |
| core | load_sqlite | memory_baseline_rss | process_tree | n/a | unavailable |
| core | load_sqlite | memory_peak_rss | self_only | 397.25 MiB | ok |
| core | load_sqlite | memory_peak_rss_delta | process_tree | n/a | unavailable |
| core | load_sqlite | memory_stable_rss | self_only | n/a | unavailable |
| core | load_sqlite | memory_max_processes | process_tree | n/a | unavailable |
| core | load_mmap | memory_baseline_rss | process_tree | n/a | unavailable |
| core | load_mmap | memory_peak_rss | self_only | 171.89 MiB | ok |
| core | load_mmap | memory_peak_rss_delta | process_tree | n/a | unavailable |
| core | load_mmap | memory_stable_rss | self_only | n/a | unavailable |
| core | load_mmap | memory_max_processes | process_tree | n/a | unavailable |
| lite | build | memory_baseline_rss | process_tree | n/a | unavailable |
| lite | build | memory_peak_rss | self_only | 483.17 MiB | ok |
| lite | build | memory_peak_rss_delta | process_tree | n/a | unavailable |
| lite | build | memory_stable_rss | self_only | n/a | unavailable |
| lite | build | memory_max_processes | process_tree | n/a | unavailable |
| lite | load_json | memory_baseline_rss | process_tree | n/a | unavailable |
| lite | load_json | memory_peak_rss | self_only | 377.73 MiB | ok |
| lite | load_json | memory_peak_rss_delta | process_tree | n/a | unavailable |
| lite | load_json | memory_stable_rss | self_only | n/a | unavailable |
| lite | load_json | memory_max_processes | process_tree | n/a | unavailable |
| lite | load_sqlite | memory_baseline_rss | process_tree | n/a | unavailable |
| lite | load_sqlite | memory_peak_rss | self_only | 370.81 MiB | ok |
| lite | load_sqlite | memory_peak_rss_delta | process_tree | n/a | unavailable |
| lite | load_sqlite | memory_stable_rss | self_only | n/a | unavailable |
| lite | load_sqlite | memory_max_processes | process_tree | n/a | unavailable |
| lite | load_mmap | memory_baseline_rss | process_tree | n/a | unavailable |
| lite | load_mmap | memory_peak_rss | self_only | 161.77 MiB | ok |
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
