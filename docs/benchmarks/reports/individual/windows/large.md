# Lucis benchmark report

> These results describe one machine and one execution environment. They
> are not search-quality measurements or universal performance guarantees.

## Run

| Field | Value |
|---|---|
| Run ID | 20260803T002140Z-099b15 |
| Started (UTC) | 2026-08-03T00:21:40.399215+00:00 |
| Finished (UTC) | 2026-08-03T00:28:54.720539+00:00 |
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
| core | dataset_generation | - | - | 1.85 s | 1.85 s | 1 |
| core | index_build | - | - | 4.30 s | 4.30 s | 1 |
| core | index_e2e_json | - | - | 7.91 s | 7.91 s | 1 |
| core | search_first | - | common | 238.07 ms | 238.07 ms | 1 |
| core | search_warm | - | common | 229.87 ms | 268.71 ms | 40 |
| core | search_warm | - | rare | 211.50 µs | 267.20 µs | 40 |
| core | search_warm | - | multi | 251.00 ms | 302.01 ms | 40 |
| core | search_warm | - | no_result | 4.10 µs | 4.60 µs | 40 |
| core | search_warm | - | repeated | 255.95 ms | 275.86 ms | 100 |
| lite | dataset_generation | - | - | 1.30 s | 1.30 s | 1 |
| lite | index_build | - | - | 2.15 s | 2.15 s | 1 |
| lite | index_e2e_json | - | - | 5.91 s | 5.91 s | 1 |
| lite | search_first | - | common | 124.29 ms | 124.29 ms | 1 |
| lite | search_warm | - | common | 114.28 ms | 145.67 ms | 40 |
| lite | search_warm | - | rare | 122.50 µs | 208.20 µs | 40 |
| lite | search_warm | - | multi | 141.39 ms | 186.64 ms | 40 |
| lite | search_warm | - | no_result | 7.35 µs | 9.20 µs | 40 |
| lite | search_warm | - | repeated | 141.05 ms | 166.88 ms | 100 |

## Persistence

| Engine | Metric | Backend | Category | Median | p95 | Samples |
|---|---|---|---|---|---|---|
| core | json_save | - | - | 4.02 s | 4.02 s | 1 |
| core | json_artifact_size | - | - | 65.21 MiB | 65.21 MiB | 1 |
| core | sqlite_save | - | - | 1.31 s | 1.31 s | 1 |
| core | sqlite_artifact_size | - | - | 46.55 MiB | 46.55 MiB | 1 |
| core | lcs_write | - | - | 72.20 ms | 72.20 ms | 1 |
| core | lcs_artifact_size | - | - | 20.78 MiB | 20.78 MiB | 1 |
| lite | json_save | - | - | 3.74 s | 3.74 s | 1 |
| lite | json_artifact_size | - | - | 61.61 MiB | 61.61 MiB | 1 |
| lite | sqlite_save | - | - | 1.24 s | 1.24 s | 1 |
| lite | sqlite_artifact_size | - | - | 46.55 MiB | 46.55 MiB | 1 |
| lite | lcs_write | - | - | 55.27 ms | 55.27 ms | 1 |
| lite | lcs_artifact_size | - | - | 20.01 MiB | 20.01 MiB | 1 |

## Standard loads

| Engine | Metric | Backend | Category | Median | p95 | Samples |
|---|---|---|---|---|---|---|
| core | load_standard | json | - | 1.97 s | 1.97 s | 1 |
| core | search_first_after_load | json | common | 233.34 ms | 233.34 ms | 1 |
| core | search_warm_after_load | json | common | 181.51 ms | 241.18 ms | 40 |
| core | search_warm_after_load | json | rare | 219.70 µs | 403.70 µs | 40 |
| core | search_warm_after_load | json | multi | 220.55 ms | 269.05 ms | 40 |
| core | search_warm_after_load | json | no_result | 6.45 µs | 12.60 µs | 40 |
| core | search_warm_after_load | json | repeated | 230.15 ms | 251.52 ms | 100 |
| core | load_standard | sqlite | - | 2.89 s | 2.89 s | 1 |
| core | search_first_after_load | sqlite | common | 256.77 ms | 256.77 ms | 1 |
| core | search_warm_after_load | sqlite | common | 251.23 ms | 286.59 ms | 40 |
| core | search_warm_after_load | sqlite | rare | 218.30 µs | 317.40 µs | 40 |
| core | search_warm_after_load | sqlite | multi | 268.61 ms | 332.43 ms | 40 |
| core | search_warm_after_load | sqlite | no_result | 4.30 µs | 4.90 µs | 40 |
| core | search_warm_after_load | sqlite | repeated | 283.42 ms | 298.05 ms | 100 |
| lite | load_standard | json | - | 1.85 s | 1.85 s | 1 |
| lite | search_first_after_load | json | common | 139.85 ms | 139.85 ms | 1 |
| lite | search_warm_after_load | json | common | 116.03 ms | 149.37 ms | 40 |
| lite | search_warm_after_load | json | rare | 128.55 µs | 203.60 µs | 40 |
| lite | search_warm_after_load | json | multi | 144.71 ms | 188.69 ms | 40 |
| lite | search_warm_after_load | json | no_result | 3.80 µs | 4.20 µs | 40 |
| lite | search_warm_after_load | json | repeated | 141.17 ms | 151.58 ms | 100 |
| lite | load_standard | sqlite | - | 1.58 s | 1.58 s | 1 |
| lite | search_first_after_load | sqlite | common | 134.80 ms | 134.80 ms | 1 |
| lite | search_warm_after_load | sqlite | common | 130.94 ms | 168.55 ms | 40 |
| lite | search_warm_after_load | sqlite | rare | 127.45 µs | 232.00 µs | 40 |
| lite | search_warm_after_load | sqlite | multi | 162.72 ms | 199.84 ms | 40 |
| lite | search_warm_after_load | sqlite | no_result | 3.90 µs | 4.40 µs | 40 |
| lite | search_warm_after_load | sqlite | repeated | 164.19 ms | 175.08 ms | 100 |

## Memory-mapped loads

| Engine | Metric | Backend | Category | Median | p95 | Samples |
|---|---|---|---|---|---|---|
| core | mmap_load | - | - | 29.90 ms | 29.90 ms | 1 |
| core | search_first_mmap | - | common | 402.18 ms | 402.18 ms | 1 |
| core | search_warm_mmap | - | common | 344.00 ms | 412.87 ms | 40 |
| core | search_warm_mmap | - | rare | 427.00 µs | 542.30 µs | 40 |
| core | search_warm_mmap | - | multi | 458.91 ms | 542.68 ms | 40 |
| core | search_warm_mmap | - | no_result | 4.40 µs | 5.30 µs | 40 |
| core | search_warm_mmap | - | repeated | 414.64 ms | 540.54 ms | 100 |
| lite | mmap_load | - | - | 15.12 ms | 15.12 ms | 1 |
| lite | search_first_mmap | - | common | 143.29 ms | 143.29 ms | 1 |
| lite | search_warm_mmap | - | common | 122.52 ms | 160.73 ms | 40 |
| lite | search_warm_mmap | - | rare | 134.30 µs | 142.60 µs | 40 |
| lite | search_warm_mmap | - | multi | 173.75 ms | 209.81 ms | 40 |
| lite | search_warm_mmap | - | no_result | 6.00 µs | 7.00 µs | 40 |
| lite | search_warm_mmap | - | repeated | 157.11 ms | 172.95 ms | 100 |

## Memory

RSS values are process readings, not exclusive ownership. `n/a` marks capabilities unavailable on this host; they are never reported as zero.

| Engine | Phase | Metric | Scope | Value | Status |
|---|---|---|---|---|---|
| core | build | memory_baseline_rss | process_tree | 8.63 MiB | ok |
| core | build | memory_peak_rss | process_tree | 407.73 MiB | ok |
| core | build | memory_peak_rss_delta | process_tree | 399.10 MiB | ok |
| core | build | memory_stable_rss | self_only | 218.38 MiB | ok |
| core | build | memory_max_processes | process_tree | 1 | ok |
| core | load_json | memory_baseline_rss | process_tree | 7.34 MiB | ok |
| core | load_json | memory_peak_rss | process_tree | 258.43 MiB | ok |
| core | load_json | memory_peak_rss_delta | process_tree | 251.09 MiB | ok |
| core | load_json | memory_stable_rss | self_only | 95.87 MiB | ok |
| core | load_json | memory_max_processes | process_tree | 1 | ok |
| core | load_sqlite | memory_baseline_rss | process_tree | 8.09 MiB | ok |
| core | load_sqlite | memory_peak_rss | process_tree | 326.11 MiB | ok |
| core | load_sqlite | memory_peak_rss_delta | process_tree | 318.02 MiB | ok |
| core | load_sqlite | memory_stable_rss | self_only | 98.13 MiB | ok |
| core | load_sqlite | memory_max_processes | process_tree | 1 | ok |
| core | load_mmap | memory_baseline_rss | process_tree | 1.96 MiB | ok |
| core | load_mmap | memory_peak_rss | process_tree | 122.66 MiB | ok |
| core | load_mmap | memory_peak_rss_delta | process_tree | 120.71 MiB | ok |
| core | load_mmap | memory_stable_rss | self_only | 95.25 MiB | ok |
| core | load_mmap | memory_max_processes | process_tree | 1 | ok |
| lite | build | memory_baseline_rss | process_tree | 8.83 MiB | ok |
| lite | build | memory_peak_rss | process_tree | 374.93 MiB | ok |
| lite | build | memory_peak_rss_delta | process_tree | 366.10 MiB | ok |
| lite | build | memory_stable_rss | self_only | 177.18 MiB | ok |
| lite | build | memory_max_processes | process_tree | 1 | ok |
| lite | load_json | memory_baseline_rss | process_tree | 8.04 MiB | ok |
| lite | load_json | memory_peak_rss | process_tree | 259.22 MiB | ok |
| lite | load_json | memory_peak_rss_delta | process_tree | 251.18 MiB | ok |
| lite | load_json | memory_stable_rss | self_only | 96.86 MiB | ok |
| lite | load_json | memory_max_processes | process_tree | 1 | ok |
| lite | load_sqlite | memory_baseline_rss | process_tree | 8.02 MiB | ok |
| lite | load_sqlite | memory_peak_rss | process_tree | 308.15 MiB | ok |
| lite | load_sqlite | memory_peak_rss_delta | process_tree | 300.14 MiB | ok |
| lite | load_sqlite | memory_stable_rss | self_only | 93.69 MiB | ok |
| lite | load_sqlite | memory_max_processes | process_tree | 1 | ok |
| lite | load_mmap | memory_baseline_rss | process_tree | 8.43 MiB | ok |
| lite | load_mmap | memory_peak_rss | process_tree | 110.84 MiB | ok |
| lite | load_mmap | memory_peak_rss_delta | process_tree | 102.41 MiB | ok |
| lite | load_mmap | memory_stable_rss | self_only | 94.86 MiB | ok |
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
