# Lucis benchmark report

> These results describe one machine and one execution environment. They
> are not search-quality measurements or universal performance guarantees.

## Run

| Field | Value |
|---|---|
| Run ID | 20260801T192500Z-416a94 |
| Started (UTC) | 2026-08-01T19:25:00.726411+00:00 |
| Finished (UTC) | 2026-08-01T19:25:02.690912+00:00 |
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
| core | dataset_generation | - | - | 4.41 ms | 4.41 ms | 1 |
| core | index_build | - | - | 5.24 ms | 5.24 ms | 1 |
| core | index_e2e_json | - | - | 11.30 ms | 11.30 ms | 1 |
| core | search_first | - | common | 286.77 µs | 286.77 µs | 1 |
| core | search_warm | - | common | 178.93 µs | 202.53 µs | 40 |
| core | search_warm | - | rare | 12.66 µs | 14.24 µs | 40 |
| core | search_warm | - | multi | 199.60 µs | 222.99 µs | 40 |
| core | search_warm | - | no_result | 5.45 µs | 5.90 µs | 40 |
| core | search_warm | - | repeated | 191.56 µs | 206.20 µs | 100 |
| lite | dataset_generation | - | - | 4.24 ms | 4.24 ms | 1 |
| lite | index_build | - | - | 3.88 ms | 3.88 ms | 1 |
| lite | index_e2e_json | - | - | 9.90 ms | 9.90 ms | 1 |
| lite | search_first | - | common | 196.29 µs | 196.29 µs | 1 |
| lite | search_warm | - | common | 100.48 µs | 122.65 µs | 40 |
| lite | search_warm | - | rare | 10.38 µs | 11.00 µs | 40 |
| lite | search_warm | - | multi | 122.10 µs | 132.40 µs | 40 |
| lite | search_warm | - | no_result | 5.20 µs | 5.42 µs | 40 |
| lite | search_warm | - | repeated | 105.32 µs | 115.33 µs | 100 |

## Persistence

| Engine | Metric | Backend | Category | Median | p95 | Samples |
|---|---|---|---|---|---|---|
| core | json_save | - | - | 6.09 ms | 6.09 ms | 1 |
| core | json_artifact_size | - | - | 80.35 KiB | 80.35 KiB | 1 |
| core | sqlite_save | - | - | 6.25 ms | 6.25 ms | 1 |
| core | sqlite_artifact_size | - | - | 200.00 KiB | 200.00 KiB | 1 |
| core | lcs_write | - | - | 2.55 ms | 2.55 ms | 1 |
| core | lcs_artifact_size | - | - | 77.64 KiB | 77.64 KiB | 1 |
| lite | json_save | - | - | 5.88 ms | 5.88 ms | 1 |
| lite | json_artifact_size | - | - | 77.03 KiB | 77.03 KiB | 1 |
| lite | sqlite_save | - | - | 6.18 ms | 6.18 ms | 1 |
| lite | sqlite_artifact_size | - | - | 200.00 KiB | 200.00 KiB | 1 |
| lite | lcs_write | - | - | 2.54 ms | 2.54 ms | 1 |
| lite | lcs_artifact_size | - | - | 76.86 KiB | 76.86 KiB | 1 |

## Standard loads

| Engine | Metric | Backend | Category | Median | p95 | Samples |
|---|---|---|---|---|---|---|
| core | load_standard | json | - | 4.62 ms | 4.62 ms | 1 |
| core | search_first_after_load | json | common | 416.50 µs | 416.50 µs | 1 |
| core | search_warm_after_load | json | common | 176.97 µs | 201.15 µs | 40 |
| core | search_warm_after_load | json | rare | 12.70 µs | 13.32 µs | 40 |
| core | search_warm_after_load | json | multi | 201.82 µs | 316.19 µs | 40 |
| core | search_warm_after_load | json | no_result | 5.38 µs | 5.93 µs | 40 |
| core | search_warm_after_load | json | repeated | 190.08 µs | 202.54 µs | 100 |
| core | load_standard | sqlite | - | 9.44 ms | 9.44 ms | 1 |
| core | search_first_after_load | sqlite | common | 407.70 µs | 407.70 µs | 1 |
| core | search_warm_after_load | sqlite | common | 183.43 µs | 208.44 µs | 40 |
| core | search_warm_after_load | sqlite | rare | 12.79 µs | 13.57 µs | 40 |
| core | search_warm_after_load | sqlite | multi | 204.43 µs | 227.53 µs | 40 |
| core | search_warm_after_load | sqlite | no_result | 5.55 µs | 6.34 µs | 40 |
| core | search_warm_after_load | sqlite | repeated | 192.39 µs | 202.33 µs | 100 |
| lite | load_standard | json | - | 4.98 ms | 4.98 ms | 1 |
| lite | search_first_after_load | json | common | 385.44 µs | 385.44 µs | 1 |
| lite | search_warm_after_load | json | common | 100.20 µs | 128.62 µs | 40 |
| lite | search_warm_after_load | json | rare | 10.55 µs | 12.04 µs | 40 |
| lite | search_warm_after_load | json | multi | 120.84 µs | 130.96 µs | 40 |
| lite | search_warm_after_load | json | no_result | 5.08 µs | 5.30 µs | 40 |
| lite | search_warm_after_load | json | repeated | 103.71 µs | 114.49 µs | 100 |
| lite | load_standard | sqlite | - | 7.76 ms | 7.76 ms | 1 |
| lite | search_first_after_load | sqlite | common | 304.51 µs | 304.51 µs | 1 |
| lite | search_warm_after_load | sqlite | common | 101.71 µs | 116.54 µs | 40 |
| lite | search_warm_after_load | sqlite | rare | 10.81 µs | 11.43 µs | 40 |
| lite | search_warm_after_load | sqlite | multi | 121.99 µs | 137.31 µs | 40 |
| lite | search_warm_after_load | sqlite | no_result | 5.08 µs | 5.31 µs | 40 |
| lite | search_warm_after_load | sqlite | repeated | 104.97 µs | 116.76 µs | 100 |

## Memory-mapped loads

| Engine | Metric | Backend | Category | Median | p95 | Samples |
|---|---|---|---|---|---|---|
| core | mmap_load | - | - | 1.77 ms | 1.77 ms | 1 |
| core | search_first_mmap | - | common | 679.04 µs | 679.04 µs | 1 |
| core | search_warm_mmap | - | common | 401.85 µs | 439.20 µs | 40 |
| core | search_warm_mmap | - | rare | 20.61 µs | 22.02 µs | 40 |
| core | search_warm_mmap | - | multi | 517.14 µs | 574.91 µs | 40 |
| core | search_warm_mmap | - | no_result | 5.75 µs | 6.00 µs | 40 |
| core | search_warm_mmap | - | repeated | 429.20 µs | 439.80 µs | 100 |
| lite | mmap_load | - | - | 1.77 ms | 1.77 ms | 1 |
| lite | search_first_mmap | - | common | 361.48 µs | 361.48 µs | 1 |
| lite | search_warm_mmap | - | common | 120.17 µs | 135.53 µs | 40 |
| lite | search_warm_mmap | - | rare | 14.02 µs | 15.67 µs | 40 |
| lite | search_warm_mmap | - | multi | 142.23 µs | 159.24 µs | 40 |
| lite | search_warm_mmap | - | no_result | 5.51 µs | 6.75 µs | 40 |
| lite | search_warm_mmap | - | repeated | 121.34 µs | 132.56 µs | 100 |

## Memory

RSS values are process readings, not exclusive ownership. `n/a` marks capabilities unavailable on this host; they are never reported as zero.

| Engine | Phase | Metric | Scope | Value | Status |
|---|---|---|---|---|---|
| core | build | memory_baseline_rss | process_tree | 10.50 MiB | ok |
| core | build | memory_peak_rss | process_tree | 30.34 MiB | ok |
| core | build | memory_peak_rss_delta | process_tree | 19.84 MiB | ok |
| core | build | memory_stable_rss | self_only | 30.34 MiB | ok |
| core | build | memory_max_processes | process_tree | 1 | ok |
| core | load_json | memory_baseline_rss | process_tree | 8.74 MiB | ok |
| core | load_json | memory_peak_rss | process_tree | 28.32 MiB | ok |
| core | load_json | memory_peak_rss_delta | process_tree | 19.58 MiB | ok |
| core | load_json | memory_stable_rss | self_only | 28.32 MiB | ok |
| core | load_json | memory_max_processes | process_tree | 1 | ok |
| core | load_sqlite | memory_baseline_rss | process_tree | 8.82 MiB | ok |
| core | load_sqlite | memory_peak_rss | process_tree | 29.21 MiB | ok |
| core | load_sqlite | memory_peak_rss_delta | process_tree | 20.39 MiB | ok |
| core | load_sqlite | memory_stable_rss | self_only | 29.19 MiB | ok |
| core | load_sqlite | memory_max_processes | process_tree | 1 | ok |
| core | load_mmap | memory_baseline_rss | process_tree | 8.83 MiB | ok |
| core | load_mmap | memory_peak_rss | process_tree | 28.34 MiB | ok |
| core | load_mmap | memory_peak_rss_delta | process_tree | 19.51 MiB | ok |
| core | load_mmap | memory_stable_rss | self_only | 28.27 MiB | ok |
| core | load_mmap | memory_max_processes | process_tree | 1 | ok |
| lite | build | memory_baseline_rss | process_tree | 8.57 MiB | ok |
| lite | build | memory_peak_rss | process_tree | 30.23 MiB | ok |
| lite | build | memory_peak_rss_delta | process_tree | 21.66 MiB | ok |
| lite | build | memory_stable_rss | self_only | 30.23 MiB | ok |
| lite | build | memory_max_processes | process_tree | 1 | ok |
| lite | load_json | memory_baseline_rss | process_tree | 8.56 MiB | ok |
| lite | load_json | memory_peak_rss | process_tree | 28.28 MiB | ok |
| lite | load_json | memory_peak_rss_delta | process_tree | 19.72 MiB | ok |
| lite | load_json | memory_stable_rss | self_only | 28.28 MiB | ok |
| lite | load_json | memory_max_processes | process_tree | 1 | ok |
| lite | load_sqlite | memory_baseline_rss | process_tree | 8.94 MiB | ok |
| lite | load_sqlite | memory_peak_rss | process_tree | 29.27 MiB | ok |
| lite | load_sqlite | memory_peak_rss_delta | process_tree | 20.32 MiB | ok |
| lite | load_sqlite | memory_stable_rss | self_only | 29.27 MiB | ok |
| lite | load_sqlite | memory_max_processes | process_tree | 1 | ok |
| lite | load_mmap | memory_baseline_rss | process_tree | 8.77 MiB | ok |
| lite | load_mmap | memory_peak_rss | process_tree | 28.15 MiB | ok |
| lite | load_mmap | memory_peak_rss_delta | process_tree | 19.38 MiB | ok |
| lite | load_mmap | memory_stable_rss | self_only | 28.15 MiB | ok |
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
