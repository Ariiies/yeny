# Lucis benchmark report

> These results describe one machine and one execution environment. They
> are not search-quality measurements or universal performance guarantees.

## Run

| Field | Value |
|---|---|
| Run ID | 20260813T181308Z-a7901b |
| Started (UTC) | 2026-08-13T18:13:08.245559+00:00 |
| Finished (UTC) | 2026-08-13T18:13:08.881381+00:00 |
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
| core | dataset_generation | - | - | 1.32 ms | 1.32 ms | 1 |
| core | index_build | - | - | 1.50 ms | 1.50 ms | 1 |
| core | index_e2e_json | - | - | 3.77 ms | 3.77 ms | 1 |
| core | search_first | - | common | 83.04 µs | 83.04 µs | 1 |
| core | search_warm | - | common | 55.17 µs | 60.96 µs | 40 |
| core | search_warm | - | rare | 3.56 µs | 3.71 µs | 40 |
| core | search_warm | - | multi | 63.75 µs | 73.75 µs | 40 |
| core | search_warm | - | no_result | 1.50 µs | 1.62 µs | 40 |
| core | search_warm | - | repeated | 63.08 µs | 64.00 µs | 100 |
| lite | dataset_generation | - | - | 1.40 ms | 1.40 ms | 1 |
| lite | index_build | - | - | 1.14 ms | 1.14 ms | 1 |
| lite | index_e2e_json | - | - | 3.47 ms | 3.47 ms | 1 |
| lite | search_first | - | common | 64.79 µs | 64.79 µs | 1 |
| lite | search_warm | - | common | 35.25 µs | 42.38 µs | 40 |
| lite | search_warm | - | rare | 3.00 µs | 3.12 µs | 40 |
| lite | search_warm | - | multi | 41.67 µs | 46.54 µs | 40 |
| lite | search_warm | - | no_result | 1.54 µs | 1.62 µs | 40 |
| lite | search_warm | - | repeated | 38.50 µs | 39.88 µs | 100 |

## Persistence

| Engine | Metric | Backend | Category | Median | p95 | Samples |
|---|---|---|---|---|---|---|
| core | json_save | - | - | 2.29 ms | 2.29 ms | 1 |
| core | json_artifact_size | - | - | 80.35 KiB | 80.35 KiB | 1 |
| core | sqlite_save | - | - | 2.15 ms | 2.15 ms | 1 |
| core | sqlite_artifact_size | - | - | 200.00 KiB | 200.00 KiB | 1 |
| core | lcs_write | - | - | 856.08 µs | 856.08 µs | 1 |
| core | lcs_artifact_size | - | - | 77.64 KiB | 77.64 KiB | 1 |
| lite | json_save | - | - | 2.22 ms | 2.22 ms | 1 |
| lite | json_artifact_size | - | - | 77.03 KiB | 77.03 KiB | 1 |
| lite | sqlite_save | - | - | 2.31 ms | 2.31 ms | 1 |
| lite | sqlite_artifact_size | - | - | 200.00 KiB | 200.00 KiB | 1 |
| lite | lcs_write | - | - | 833.38 µs | 833.38 µs | 1 |
| lite | lcs_artifact_size | - | - | 76.86 KiB | 76.86 KiB | 1 |

## Standard loads

| Engine | Metric | Backend | Category | Median | p95 | Samples |
|---|---|---|---|---|---|---|
| core | load_standard | json | - | 1.27 ms | 1.27 ms | 1 |
| core | search_first_after_load | json | common | 129.58 µs | 129.58 µs | 1 |
| core | search_warm_after_load | json | common | 57.50 µs | 67.54 µs | 40 |
| core | search_warm_after_load | json | rare | 3.62 µs | 3.92 µs | 40 |
| core | search_warm_after_load | json | multi | 65.92 µs | 74.75 µs | 40 |
| core | search_warm_after_load | json | no_result | 1.50 µs | 1.67 µs | 40 |
| core | search_warm_after_load | json | repeated | 64.08 µs | 64.83 µs | 100 |
| core | load_standard | sqlite | - | 2.77 ms | 2.77 ms | 1 |
| core | search_first_after_load | sqlite | common | 113.58 µs | 113.58 µs | 1 |
| core | search_warm_after_load | sqlite | common | 55.13 µs | 64.54 µs | 40 |
| core | search_warm_after_load | sqlite | rare | 3.62 µs | 3.75 µs | 40 |
| core | search_warm_after_load | sqlite | multi | 64.90 µs | 73.88 µs | 40 |
| core | search_warm_after_load | sqlite | no_result | 1.67 µs | 1.75 µs | 40 |
| core | search_warm_after_load | sqlite | repeated | 63.79 µs | 64.42 µs | 100 |
| lite | load_standard | json | - | 1.24 ms | 1.24 ms | 1 |
| lite | search_first_after_load | json | common | 94.54 µs | 94.54 µs | 1 |
| lite | search_warm_after_load | json | common | 34.50 µs | 39.54 µs | 40 |
| lite | search_warm_after_load | json | rare | 2.96 µs | 3.04 µs | 40 |
| lite | search_warm_after_load | json | multi | 40.75 µs | 47.58 µs | 40 |
| lite | search_warm_after_load | json | no_result | 1.54 µs | 1.58 µs | 40 |
| lite | search_warm_after_load | json | repeated | 38.77 µs | 42.25 µs | 100 |
| lite | load_standard | sqlite | - | 2.23 ms | 2.23 ms | 1 |
| lite | search_first_after_load | sqlite | common | 97.25 µs | 97.25 µs | 1 |
| lite | search_warm_after_load | sqlite | common | 34.90 µs | 39.38 µs | 40 |
| lite | search_warm_after_load | sqlite | rare | 3.00 µs | 3.08 µs | 40 |
| lite | search_warm_after_load | sqlite | multi | 43.33 µs | 46.83 µs | 40 |
| lite | search_warm_after_load | sqlite | no_result | 1.46 µs | 1.54 µs | 40 |
| lite | search_warm_after_load | sqlite | repeated | 38.83 µs | 41.54 µs | 100 |

## Memory-mapped loads

| Engine | Metric | Backend | Category | Median | p95 | Samples |
|---|---|---|---|---|---|---|
| core | mmap_load | - | - | 6.87 ms | 6.87 ms | 1 |
| core | search_first_mmap | - | common | 199.62 µs | 199.62 µs | 1 |
| core | search_warm_mmap | - | common | 118.04 µs | 129.50 µs | 40 |
| core | search_warm_mmap | - | rare | 5.25 µs | 5.83 µs | 40 |
| core | search_warm_mmap | - | multi | 158.02 µs | 178.50 µs | 40 |
| core | search_warm_mmap | - | no_result | 1.75 µs | 2.21 µs | 40 |
| core | search_warm_mmap | - | repeated | 133.33 µs | 139.71 µs | 100 |
| lite | mmap_load | - | - | 5.83 ms | 5.83 ms | 1 |
| lite | search_first_mmap | - | common | 109.67 µs | 109.67 µs | 1 |
| lite | search_warm_mmap | - | common | 38.50 µs | 40.79 µs | 40 |
| lite | search_warm_mmap | - | rare | 3.33 µs | 3.71 µs | 40 |
| lite | search_warm_mmap | - | multi | 45.79 µs | 52.58 µs | 40 |
| lite | search_warm_mmap | - | no_result | 1.58 µs | 1.67 µs | 40 |
| lite | search_warm_mmap | - | repeated | 43.58 µs | 46.62 µs | 100 |

## Memory

RSS values are process readings, not exclusive ownership. `n/a` marks capabilities unavailable on this host; they are never reported as zero.

| Engine | Phase | Metric | Scope | Value | Status |
|---|---|---|---|---|---|
| core | build | memory_baseline_rss | process_tree | n/a | unavailable |
| core | build | memory_peak_rss | self_only | 32.30 MiB | ok |
| core | build | memory_peak_rss_delta | process_tree | n/a | unavailable |
| core | build | memory_stable_rss | self_only | n/a | unavailable |
| core | build | memory_max_processes | process_tree | n/a | unavailable |
| core | load_json | memory_baseline_rss | process_tree | n/a | unavailable |
| core | load_json | memory_peak_rss | self_only | 30.44 MiB | ok |
| core | load_json | memory_peak_rss_delta | process_tree | n/a | unavailable |
| core | load_json | memory_stable_rss | self_only | n/a | unavailable |
| core | load_json | memory_max_processes | process_tree | n/a | unavailable |
| core | load_sqlite | memory_baseline_rss | process_tree | n/a | unavailable |
| core | load_sqlite | memory_peak_rss | self_only | 31.25 MiB | ok |
| core | load_sqlite | memory_peak_rss_delta | process_tree | n/a | unavailable |
| core | load_sqlite | memory_stable_rss | self_only | n/a | unavailable |
| core | load_sqlite | memory_max_processes | process_tree | n/a | unavailable |
| core | load_mmap | memory_baseline_rss | process_tree | n/a | unavailable |
| core | load_mmap | memory_peak_rss | self_only | 30.16 MiB | ok |
| core | load_mmap | memory_peak_rss_delta | process_tree | n/a | unavailable |
| core | load_mmap | memory_stable_rss | self_only | n/a | unavailable |
| core | load_mmap | memory_max_processes | process_tree | n/a | unavailable |
| lite | build | memory_baseline_rss | process_tree | n/a | unavailable |
| lite | build | memory_peak_rss | self_only | 32.34 MiB | ok |
| lite | build | memory_peak_rss_delta | process_tree | n/a | unavailable |
| lite | build | memory_stable_rss | self_only | n/a | unavailable |
| lite | build | memory_max_processes | process_tree | n/a | unavailable |
| lite | load_json | memory_baseline_rss | process_tree | n/a | unavailable |
| lite | load_json | memory_peak_rss | self_only | 30.33 MiB | ok |
| lite | load_json | memory_peak_rss_delta | process_tree | n/a | unavailable |
| lite | load_json | memory_stable_rss | self_only | n/a | unavailable |
| lite | load_json | memory_max_processes | process_tree | n/a | unavailable |
| lite | load_sqlite | memory_baseline_rss | process_tree | n/a | unavailable |
| lite | load_sqlite | memory_peak_rss | self_only | 31.27 MiB | ok |
| lite | load_sqlite | memory_peak_rss_delta | process_tree | n/a | unavailable |
| lite | load_sqlite | memory_stable_rss | self_only | n/a | unavailable |
| lite | load_sqlite | memory_max_processes | process_tree | n/a | unavailable |
| lite | load_mmap | memory_baseline_rss | process_tree | n/a | unavailable |
| lite | load_mmap | memory_peak_rss | self_only | 30.38 MiB | ok |
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
