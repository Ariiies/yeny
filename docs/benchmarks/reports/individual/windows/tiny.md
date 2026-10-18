# Yeny benchmark report

> These results describe one machine and one execution environment. They
> are not search-quality measurements or universal performance guarantees.

## Run

| Field | Value |
|---|---|
| Run ID | 20260803T001930Z-f4ea3e |
| Started (UTC) | 2026-08-03T00:19:30.164091+00:00 |
| Finished (UTC) | 2026-08-03T00:19:34.040543+00:00 |
| Schema version | 1.0 |

## Environment

| Field | Value |
|---|---|
| python_version | 3.13.0 |
| python_implementation | CPython |
| platform | Windows-11-10.0.26200-SP0 |
| machine | AMD64 |
| yeny_version | 0.1.0 |
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
| core | dataset_generation | - | - | 4.11 ms | 4.11 ms | 1 |
| core | index_build | - | - | 5.31 ms | 5.31 ms | 1 |
| core | index_e2e_json | - | - | 14.57 ms | 14.57 ms | 1 |
| core | search_first | - | common | 316.00 µs | 316.00 µs | 1 |
| core | search_warm | - | common | 189.00 µs | 268.20 µs | 40 |
| core | search_warm | - | rare | 12.50 µs | 15.30 µs | 40 |
| core | search_warm | - | multi | 219.35 µs | 370.00 µs | 40 |
| core | search_warm | - | no_result | 5.50 µs | 5.80 µs | 40 |
| core | search_warm | - | repeated | 196.45 µs | 332.70 µs | 100 |
| lite | dataset_generation | - | - | 4.63 ms | 4.63 ms | 1 |
| lite | index_build | - | - | 4.46 ms | 4.46 ms | 1 |
| lite | index_e2e_json | - | - | 16.08 ms | 16.08 ms | 1 |
| lite | search_first | - | common | 241.70 µs | 241.70 µs | 1 |
| lite | search_warm | - | common | 108.50 µs | 125.80 µs | 40 |
| lite | search_warm | - | rare | 10.20 µs | 12.50 µs | 40 |
| lite | search_warm | - | multi | 128.80 µs | 160.20 µs | 40 |
| lite | search_warm | - | no_result | 5.10 µs | 5.30 µs | 40 |
| lite | search_warm | - | repeated | 112.25 µs | 175.60 µs | 100 |

## Persistence

| Engine | Metric | Backend | Category | Median | p95 | Samples |
|---|---|---|---|---|---|---|
| core | json_save | - | - | 8.84 ms | 8.84 ms | 1 |
| core | json_artifact_size | - | - | 84.48 KiB | 84.48 KiB | 1 |
| core | sqlite_save | - | - | 17.38 ms | 17.38 ms | 1 |
| core | sqlite_artifact_size | - | - | 196.00 KiB | 196.00 KiB | 1 |
| core | yny_write | - | - | 8.60 ms | 8.60 ms | 1 |
| core | yny_artifact_size | - | - | 77.64 KiB | 77.64 KiB | 1 |
| lite | json_save | - | - | 8.55 ms | 8.55 ms | 1 |
| lite | json_artifact_size | - | - | 81.05 KiB | 81.05 KiB | 1 |
| lite | sqlite_save | - | - | 14.73 ms | 14.73 ms | 1 |
| lite | sqlite_artifact_size | - | - | 196.00 KiB | 196.00 KiB | 1 |
| lite | yny_write | - | - | 4.46 ms | 4.46 ms | 1 |
| lite | yny_artifact_size | - | - | 76.86 KiB | 76.86 KiB | 1 |

## Standard loads

| Engine | Metric | Backend | Category | Median | p95 | Samples |
|---|---|---|---|---|---|---|
| core | load_standard | json | - | 4.71 ms | 4.71 ms | 1 |
| core | search_first_after_load | json | common | 432.40 µs | 432.40 µs | 1 |
| core | search_warm_after_load | json | common | 183.00 µs | 203.00 µs | 40 |
| core | search_warm_after_load | json | rare | 12.90 µs | 13.40 µs | 40 |
| core | search_warm_after_load | json | multi | 205.50 µs | 589.40 µs | 40 |
| core | search_warm_after_load | json | no_result | 5.80 µs | 6.10 µs | 40 |
| core | search_warm_after_load | json | repeated | 195.90 µs | 208.90 µs | 100 |
| core | load_standard | sqlite | - | 11.22 ms | 11.22 ms | 1 |
| core | search_first_after_load | sqlite | common | 433.80 µs | 433.80 µs | 1 |
| core | search_warm_after_load | sqlite | common | 182.55 µs | 202.20 µs | 40 |
| core | search_warm_after_load | sqlite | rare | 12.75 µs | 13.60 µs | 40 |
| core | search_warm_after_load | sqlite | multi | 206.40 µs | 402.20 µs | 40 |
| core | search_warm_after_load | sqlite | no_result | 5.75 µs | 6.00 µs | 40 |
| core | search_warm_after_load | sqlite | repeated | 196.40 µs | 250.00 µs | 100 |
| lite | load_standard | json | - | 4.55 ms | 4.55 ms | 1 |
| lite | search_first_after_load | json | common | 346.20 µs | 346.20 µs | 1 |
| lite | search_warm_after_load | json | common | 106.50 µs | 127.10 µs | 40 |
| lite | search_warm_after_load | json | rare | 18.85 µs | 27.20 µs | 40 |
| lite | search_warm_after_load | json | multi | 126.15 µs | 221.80 µs | 40 |
| lite | search_warm_after_load | json | no_result | 5.40 µs | 7.60 µs | 40 |
| lite | search_warm_after_load | json | repeated | 111.70 µs | 121.60 µs | 100 |
| lite | load_standard | sqlite | - | 7.98 ms | 7.98 ms | 1 |
| lite | search_first_after_load | sqlite | common | 363.00 µs | 363.00 µs | 1 |
| lite | search_warm_after_load | sqlite | common | 103.30 µs | 118.20 µs | 40 |
| lite | search_warm_after_load | sqlite | rare | 10.70 µs | 11.60 µs | 40 |
| lite | search_warm_after_load | sqlite | multi | 129.55 µs | 144.70 µs | 40 |
| lite | search_warm_after_load | sqlite | no_result | 5.40 µs | 5.50 µs | 40 |
| lite | search_warm_after_load | sqlite | repeated | 110.70 µs | 125.10 µs | 100 |

## Memory-mapped loads

| Engine | Metric | Backend | Category | Median | p95 | Samples |
|---|---|---|---|---|---|---|
| core | mmap_load | - | - | 1.96 ms | 1.96 ms | 1 |
| core | search_first_mmap | - | common | 684.40 µs | 684.40 µs | 1 |
| core | search_warm_mmap | - | common | 414.55 µs | 498.60 µs | 40 |
| core | search_warm_mmap | - | rare | 19.05 µs | 21.60 µs | 40 |
| core | search_warm_mmap | - | multi | 562.60 µs | 973.80 µs | 40 |
| core | search_warm_mmap | - | no_result | 5.90 µs | 6.10 µs | 40 |
| core | search_warm_mmap | - | repeated | 444.40 µs | 809.20 µs | 100 |
| lite | mmap_load | - | - | 1.73 ms | 1.73 ms | 1 |
| lite | search_first_mmap | - | common | 417.80 µs | 417.80 µs | 1 |
| lite | search_warm_mmap | - | common | 125.40 µs | 223.60 µs | 40 |
| lite | search_warm_mmap | - | rare | 13.00 µs | 13.80 µs | 40 |
| lite | search_warm_mmap | - | multi | 152.85 µs | 241.50 µs | 40 |
| lite | search_warm_mmap | - | no_result | 5.65 µs | 7.00 µs | 40 |
| lite | search_warm_mmap | - | repeated | 133.65 µs | 223.80 µs | 100 |

## Memory

RSS values are process readings, not exclusive ownership. `n/a` marks capabilities unavailable on this host; they are never reported as zero.

| Engine | Phase | Metric | Scope | Value | Status |
|---|---|---|---|---|---|
| core | build | memory_baseline_rss | process_tree | 8.03 MiB | ok |
| core | build | memory_peak_rss | process_tree | 30.21 MiB | ok |
| core | build | memory_peak_rss_delta | process_tree | 22.18 MiB | ok |
| core | build | memory_stable_rss | self_only | 30.07 MiB | ok |
| core | build | memory_max_processes | process_tree | 1 | ok |
| core | load_json | memory_baseline_rss | process_tree | 8.07 MiB | ok |
| core | load_json | memory_peak_rss | process_tree | 28.15 MiB | ok |
| core | load_json | memory_peak_rss_delta | process_tree | 20.08 MiB | ok |
| core | load_json | memory_stable_rss | self_only | 28.16 MiB | ok |
| core | load_json | memory_max_processes | process_tree | 1 | ok |
| core | load_sqlite | memory_baseline_rss | process_tree | 8.00 MiB | ok |
| core | load_sqlite | memory_peak_rss | process_tree | 29.11 MiB | ok |
| core | load_sqlite | memory_peak_rss_delta | process_tree | 21.11 MiB | ok |
| core | load_sqlite | memory_stable_rss | self_only | 28.70 MiB | ok |
| core | load_sqlite | memory_max_processes | process_tree | 1 | ok |
| core | load_mmap | memory_baseline_rss | process_tree | 7.16 MiB | ok |
| core | load_mmap | memory_peak_rss | process_tree | 28.21 MiB | ok |
| core | load_mmap | memory_peak_rss_delta | process_tree | 21.05 MiB | ok |
| core | load_mmap | memory_stable_rss | self_only | 28.20 MiB | ok |
| core | load_mmap | memory_max_processes | process_tree | 1 | ok |
| lite | build | memory_baseline_rss | process_tree | 7.81 MiB | ok |
| lite | build | memory_peak_rss | process_tree | 29.92 MiB | ok |
| lite | build | memory_peak_rss_delta | process_tree | 22.11 MiB | ok |
| lite | build | memory_stable_rss | self_only | 29.93 MiB | ok |
| lite | build | memory_max_processes | process_tree | 1 | ok |
| lite | load_json | memory_baseline_rss | process_tree | 6.85 MiB | ok |
| lite | load_json | memory_peak_rss | process_tree | 28.20 MiB | ok |
| lite | load_json | memory_peak_rss_delta | process_tree | 21.35 MiB | ok |
| lite | load_json | memory_stable_rss | self_only | 28.22 MiB | ok |
| lite | load_json | memory_max_processes | process_tree | 1 | ok |
| lite | load_sqlite | memory_baseline_rss | process_tree | 7.53 MiB | ok |
| lite | load_sqlite | memory_peak_rss | process_tree | 29.31 MiB | ok |
| lite | load_sqlite | memory_peak_rss_delta | process_tree | 21.78 MiB | ok |
| lite | load_sqlite | memory_stable_rss | self_only | 29.35 MiB | ok |
| lite | load_sqlite | memory_max_processes | process_tree | 1 | ok |
| lite | load_mmap | memory_baseline_rss | process_tree | 7.48 MiB | ok |
| lite | load_mmap | memory_peak_rss | process_tree | 28.52 MiB | ok |
| lite | load_mmap | memory_peak_rss_delta | process_tree | 21.04 MiB | ok |
| lite | load_mmap | memory_stable_rss | self_only | 28.53 MiB | ok |
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
