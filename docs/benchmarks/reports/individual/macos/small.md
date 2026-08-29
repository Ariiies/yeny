# Lucis benchmark report

> These results describe one machine and one execution environment. They
> are not search-quality measurements or universal performance guarantees.

## Run

| Field | Value |
|---|---|
| Run ID | 20260813T181314Z-4694ad |
| Started (UTC) | 2026-08-13T18:13:14.050133+00:00 |
| Finished (UTC) | 2026-08-13T18:13:15.844859+00:00 |
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
| core | dataset_generation | - | - | 6.20 ms | 6.20 ms | 1 |
| core | index_build | - | - | 11.28 ms | 11.28 ms | 1 |
| core | index_e2e_json | - | - | 27.65 ms | 27.65 ms | 1 |
| core | search_first | - | common | 746.21 µs | 746.21 µs | 1 |
| core | search_warm | - | common | 580.67 µs | 684.96 µs | 40 |
| core | search_warm | - | rare | 3.67 µs | 3.83 µs | 40 |
| core | search_warm | - | multi | 665.00 µs | 776.21 µs | 40 |
| core | search_warm | - | no_result | 1.67 µs | 1.79 µs | 40 |
| core | search_warm | - | repeated | 681.31 µs | 696.62 µs | 100 |
| lite | dataset_generation | - | - | 6.28 ms | 6.28 ms | 1 |
| lite | index_build | - | - | 8.09 ms | 8.09 ms | 1 |
| lite | index_e2e_json | - | - | 23.64 ms | 23.64 ms | 1 |
| lite | search_first | - | common | 481.79 µs | 481.79 µs | 1 |
| lite | search_warm | - | common | 353.04 µs | 426.79 µs | 40 |
| lite | search_warm | - | rare | 3.04 µs | 3.79 µs | 40 |
| lite | search_warm | - | multi | 426.17 µs | 495.62 µs | 40 |
| lite | search_warm | - | no_result | 1.54 µs | 1.62 µs | 40 |
| lite | search_warm | - | repeated | 417.29 µs | 423.38 µs | 100 |

## Persistence

| Engine | Metric | Backend | Category | Median | p95 | Samples |
|---|---|---|---|---|---|---|
| core | json_save | - | - | 17.08 ms | 17.08 ms | 1 |
| core | json_artifact_size | - | - | 655.74 KiB | 655.74 KiB | 1 |
| core | sqlite_save | - | - | 9.04 ms | 9.04 ms | 1 |
| core | sqlite_artifact_size | - | - | 764.00 KiB | 764.00 KiB | 1 |
| core | lcs_write | - | - | 2.39 ms | 2.39 ms | 1 |
| core | lcs_artifact_size | - | - | 354.05 KiB | 354.05 KiB | 1 |
| lite | json_save | - | - | 16.13 ms | 16.13 ms | 1 |
| lite | json_artifact_size | - | - | 621.75 KiB | 621.75 KiB | 1 |
| lite | sqlite_save | - | - | 9.73 ms | 9.73 ms | 1 |
| lite | sqlite_artifact_size | - | - | 764.00 KiB | 764.00 KiB | 1 |
| lite | lcs_write | - | - | 2.29 ms | 2.29 ms | 1 |
| lite | lcs_artifact_size | - | - | 346.24 KiB | 346.24 KiB | 1 |

## Standard loads

| Engine | Metric | Backend | Category | Median | p95 | Samples |
|---|---|---|---|---|---|---|
| core | load_standard | json | - | 7.55 ms | 7.55 ms | 1 |
| core | search_first_after_load | json | common | 780.75 µs | 780.75 µs | 1 |
| core | search_warm_after_load | json | common | 584.60 µs | 678.67 µs | 40 |
| core | search_warm_after_load | json | rare | 3.67 µs | 3.83 µs | 40 |
| core | search_warm_after_load | json | multi | 673.65 µs | 775.50 µs | 40 |
| core | search_warm_after_load | json | no_result | 1.67 µs | 1.79 µs | 40 |
| core | search_warm_after_load | json | repeated | 681.56 µs | 697.75 µs | 100 |
| core | load_standard | sqlite | - | 14.70 ms | 14.70 ms | 1 |
| core | search_first_after_load | sqlite | common | 788.71 µs | 788.71 µs | 1 |
| core | search_warm_after_load | sqlite | common | 587.50 µs | 699.50 µs | 40 |
| core | search_warm_after_load | sqlite | rare | 3.75 µs | 3.88 µs | 40 |
| core | search_warm_after_load | sqlite | multi | 633.69 µs | 788.92 µs | 40 |
| core | search_warm_after_load | sqlite | no_result | 1.67 µs | 1.79 µs | 40 |
| core | search_warm_after_load | sqlite | repeated | 677.48 µs | 693.12 µs | 100 |
| lite | load_standard | json | - | 7.27 ms | 7.27 ms | 1 |
| lite | search_first_after_load | json | common | 496.04 µs | 496.04 µs | 1 |
| lite | search_warm_after_load | json | common | 346.52 µs | 405.96 µs | 40 |
| lite | search_warm_after_load | json | rare | 3.04 µs | 3.25 µs | 40 |
| lite | search_warm_after_load | json | multi | 418.71 µs | 480.33 µs | 40 |
| lite | search_warm_after_load | json | no_result | 1.58 µs | 1.62 µs | 40 |
| lite | search_warm_after_load | json | repeated | 404.83 µs | 416.46 µs | 100 |
| lite | load_standard | sqlite | - | 10.27 ms | 10.27 ms | 1 |
| lite | search_first_after_load | sqlite | common | 505.33 µs | 505.33 µs | 1 |
| lite | search_warm_after_load | sqlite | common | 352.88 µs | 415.25 µs | 40 |
| lite | search_warm_after_load | sqlite | rare | 3.08 µs | 3.12 µs | 40 |
| lite | search_warm_after_load | sqlite | multi | 418.42 µs | 490.62 µs | 40 |
| lite | search_warm_after_load | sqlite | no_result | 1.58 µs | 1.67 µs | 40 |
| lite | search_warm_after_load | sqlite | repeated | 407.00 µs | 420.17 µs | 100 |

## Memory-mapped loads

| Engine | Metric | Backend | Category | Median | p95 | Samples |
|---|---|---|---|---|---|---|
| core | mmap_load | - | - | 7.89 ms | 7.89 ms | 1 |
| core | search_first_mmap | - | common | 1.42 ms | 1.42 ms | 1 |
| core | search_warm_mmap | - | common | 1.16 ms | 1.38 ms | 40 |
| core | search_warm_mmap | - | rare | 5.29 µs | 5.46 µs | 40 |
| core | search_warm_mmap | - | multi | 1.50 ms | 1.78 ms | 40 |
| core | search_warm_mmap | - | no_result | 1.75 µs | 1.83 µs | 40 |
| core | search_warm_mmap | - | repeated | 1.38 ms | 1.41 ms | 100 |
| lite | mmap_load | - | - | 6.01 ms | 6.01 ms | 1 |
| lite | search_first_mmap | - | common | 494.83 µs | 494.83 µs | 1 |
| lite | search_warm_mmap | - | common | 373.02 µs | 439.17 µs | 40 |
| lite | search_warm_mmap | - | rare | 3.73 µs | 3.88 µs | 40 |
| lite | search_warm_mmap | - | multi | 446.42 µs | 519.96 µs | 40 |
| lite | search_warm_mmap | - | no_result | 1.62 µs | 1.67 µs | 40 |
| lite | search_warm_mmap | - | repeated | 437.44 µs | 451.29 µs | 100 |

## Memory

RSS values are process readings, not exclusive ownership. `n/a` marks capabilities unavailable on this host; they are never reported as zero.

| Engine | Phase | Metric | Scope | Value | Status |
|---|---|---|---|---|---|
| core | build | memory_baseline_rss | process_tree | n/a | unavailable |
| core | build | memory_peak_rss | self_only | 39.14 MiB | ok |
| core | build | memory_peak_rss_delta | process_tree | n/a | unavailable |
| core | build | memory_stable_rss | self_only | n/a | unavailable |
| core | build | memory_max_processes | process_tree | n/a | unavailable |
| core | load_json | memory_baseline_rss | process_tree | n/a | unavailable |
| core | load_json | memory_peak_rss | self_only | 33.73 MiB | ok |
| core | load_json | memory_peak_rss_delta | process_tree | n/a | unavailable |
| core | load_json | memory_stable_rss | self_only | n/a | unavailable |
| core | load_json | memory_max_processes | process_tree | n/a | unavailable |
| core | load_sqlite | memory_baseline_rss | process_tree | n/a | unavailable |
| core | load_sqlite | memory_peak_rss | self_only | 34.56 MiB | ok |
| core | load_sqlite | memory_peak_rss_delta | process_tree | n/a | unavailable |
| core | load_sqlite | memory_stable_rss | self_only | n/a | unavailable |
| core | load_sqlite | memory_max_processes | process_tree | n/a | unavailable |
| core | load_mmap | memory_baseline_rss | process_tree | n/a | unavailable |
| core | load_mmap | memory_peak_rss | self_only | 31.36 MiB | ok |
| core | load_mmap | memory_peak_rss_delta | process_tree | n/a | unavailable |
| core | load_mmap | memory_stable_rss | self_only | n/a | unavailable |
| core | load_mmap | memory_max_processes | process_tree | n/a | unavailable |
| lite | build | memory_baseline_rss | process_tree | n/a | unavailable |
| lite | build | memory_peak_rss | self_only | 39.02 MiB | ok |
| lite | build | memory_peak_rss_delta | process_tree | n/a | unavailable |
| lite | build | memory_stable_rss | self_only | n/a | unavailable |
| lite | build | memory_max_processes | process_tree | n/a | unavailable |
| lite | load_json | memory_baseline_rss | process_tree | n/a | unavailable |
| lite | load_json | memory_peak_rss | self_only | 33.64 MiB | ok |
| lite | load_json | memory_peak_rss_delta | process_tree | n/a | unavailable |
| lite | load_json | memory_stable_rss | self_only | n/a | unavailable |
| lite | load_json | memory_max_processes | process_tree | n/a | unavailable |
| lite | load_sqlite | memory_baseline_rss | process_tree | n/a | unavailable |
| lite | load_sqlite | memory_peak_rss | self_only | 34.44 MiB | ok |
| lite | load_sqlite | memory_peak_rss_delta | process_tree | n/a | unavailable |
| lite | load_sqlite | memory_stable_rss | self_only | n/a | unavailable |
| lite | load_sqlite | memory_max_processes | process_tree | n/a | unavailable |
| lite | load_mmap | memory_baseline_rss | process_tree | n/a | unavailable |
| lite | load_mmap | memory_peak_rss | self_only | 31.27 MiB | ok |
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
