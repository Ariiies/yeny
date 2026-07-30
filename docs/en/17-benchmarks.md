# Benchmarks

Lucis includes a small, deterministic benchmark suite for answering practical
questions about its two public engines:

- How long does it take to build an index?
- How long do different kinds of searches take?
- How long do JSON, SQLite, and `.lcs` persistence operations take?
- How large are the generated artifacts?
- What happens when an index is loaded normally or through `mmap`?
- Does persistence preserve the same result document IDs?
- How much RSS memory is visible during each worker phase?

The suite does **not** measure search relevance, accuracy, recall, concurrent
throughput, or performance against external search projects.

## Quick start

Run commands from a local clone of the Lucis repository:

```bash
python -m pip install -e .
python -m benchmarks run --profile tiny
```

The standard suite has no mandatory benchmark dependency. For process-tree RSS
sampling, install the optional extra:

```bash
python -m pip install -e ".[benchmark]"
python -m benchmarks run --profile tiny --require-memory
```

The default command runs both engines. Select one engine or another profile
when needed:

```bash
python -m benchmarks run --profile small --engine core
python -m benchmarks run --profile medium --engine lite
python -m benchmarks run --profile small --warmups 5 --repetitions 20
```

`tiny` is the smoke run, `small` is the most useful quick local comparison,
and `medium` is the scaling check.

## Reproducible profiles

| Profile | Documents | Vocabulary | Document length |
|---|---:|---:|---:|
| `tiny` | 100 | 2,048 terms | 12–52 tokens |
| `small` | 1,000 | 2,048 terms | 12–52 tokens |
| `medium` | 10,000 | 2,048 terms | 12–52 tokens |

All profiles use:

- seed `20260117`;
- generator `lexical_zipf_v1`;
- a Zipf-like term distribution with exponent `1.07`;
- a triangular document-length distribution with a mode of 32 tokens;
- 2% intentional duplicate documents;
- 17 deterministic queries: 4 common, 4 rare, 4 multi-token, 4 no-result,
  and 1 repeated query.

The result stores dataset and query SHA-256 hashes. Those hashes prove that two
runs received identical generated inputs; they do not mean the measured time
will be identical.

## A fair Core/Lite comparison

`CoreEngine` uses TF-IDF and cosine similarity. `LiteEngine` uses normalized
term frequency. Their ranking behavior is different, but both are pure-Python
engines exposed by the same `Lucis` facade.

For timing fairness, the benchmark gives both engines the exact same corpus,
query set, `top_k=10`, and `word_tokenizer`. This is important because
`LiteEngine` normally uses character trigrams by default. Comparing each
engine with a different tokenizer would mix engine cost with tokenization and
index-size differences.

Consequently, these numbers compare the two ranking implementations under one
controlled lexical configuration. They do not compare their native defaults
and do not establish which engine produces more relevant results.

## How to read the numbers

The following table is an **illustrative audited run**, not a published
baseline or performance guarantee. It shows the scale and units a user can
expect from the report.

Run `20260729T230354Z-518467` used Lucis 0.1.0, CPython 3.13.5, Linux x86_64,
4 logical CPUs, and the `small` profile. The working tree was dirty, so this
run should not be used as an official release result.

| Measurement | Core | Lite | Samples |
|---|---:|---:|---:|
| Index build | 52.78 ms | 37.29 ms | 1 per engine |
| Build plus automatic JSON persistence | 94.45 ms | 89.13 ms | 1 per engine |
| Warm common-term search, median / p95 | 2.72 / 4.43 ms | 1.71 / 2.11 ms | 40 per engine |
| Warm rare-term search, median / p95 | 22.29 / 41.05 µs | 8.20 / 9.41 µs | 40 per engine |
| JSON load | 39.81 ms | 21.31 ms | 1 per engine |
| `mmap` load | 2.70 ms | 3.45 ms | 1 per engine |
| `.lcs` artifact | 354.05 KiB | 346.24 KiB | 1 per engine |
| Build-phase process-tree peak RSS | 77.91 MiB | 77.40 MiB | 1 phase sample |
| Preserved result ID sets | 17/17 on 3 backends | 17/17 on 3 backends | JSON, SQLite, mmap |

In this particular run, Lite used less time for index construction and the two
shown warm-search categories, while Core had the shorter single `mmap` load.
The `.lcs` files differed by about 8 KiB, and the whole build-worker RSS peaks
were nearly equal. This is a good example of why one run should be read as a
set of trade-offs instead of a single “winner.”

Build, save, load, and size measurements currently have one sample per run.
Their displayed median and p95 are therefore the same value. Search categories
contain 40 samples, and the repeated-query category contains 100, so median and
p95 are useful there. Run the command several times when comparing one-sample
operations.

## Metrics

| Metric | Measured boundary |
|---|---|
| `dataset_generation` | Deterministic corpus generation only |
| `index_build` | `Lucis.index(..., persist=False)` |
| `index_e2e_json` | Construction through `Lucis.from_dict`, including automatic JSON persistence |
| `search_first` | First public `Lucis.search` after building |
| `search_warm` | Public searches after unmeasured warm-ups, grouped by query category |
| `json_save`, `sqlite_save` | Public `Lucis.save` |
| `*_artifact_size` | Real bytes written on disk |
| `lcs_write` | Engine `.lcs` serialization |
| `load_standard` | Autoloading `Lucis` constructor for JSON or SQLite |
| `mmap_load` | Engine `load_mmap` operation |
| `search_first_*`, `search_warm_*` | Public search after standard or mapped loading |
| `roundtrip_verified` | Number of queries preserving the same sorted result IDs |
| `memory_*` | RSS observations for the complete build or load worker phase |

Search time includes query preprocessing and response construction because the
timer surrounds the public `Lucis.search` call.

Round-trip verification checks the set of top result document IDs after JSON,
SQLite, and `mmap` loading. It does not currently compare ranking order or
floating-point scores.

## Process and memory model

Core and Lite run separately. Each engine gets:

1. A build process that generates data, builds, searches, and writes all
   persistence artifacts.
2. A new load process that measures JSON, SQLite, and `mmap` sequentially.
3. A unique temporary workspace removed after the engine finishes.

The second process prevents build-time Python objects from leaking into load
measurements. It does not give each backend its own fresh interpreter, and the
operating-system page cache is not flushed or controlled.

When `psutil` is installed, the parent samples the complete worker process tree
every 5 ms. It reports baseline RSS, peak RSS, peak delta, end-of-phase self
RSS after garbage collection, and the maximum process count. RSS is not
exclusive ownership: forked copy-on-write pages may be counted more than once,
short-lived peaks may be missed, allocator arenas can remain, and live
references may still exist at phase end.

Without `psutil`, Unix can fall back to self-only peak RSS through `resource`;
Linux can also read current self RSS from `/proc`. Missing capabilities appear
as `unavailable` with null summaries, never as zero.

## Results, validation, and reports

By default, timestamped JSON results are written to
`benchmarks/results/`, which is ignored by Git:

```bash
python -m benchmarks run --profile small
```

Use another output directory if preferred:

```bash
python -m benchmarks run --profile small --output /tmp/lucis-results
```

Validate the internal structural contract:

```bash
python -m benchmarks validate benchmarks/results/<run>.json
```

Create a readable Markdown report next to the JSON:

```bash
python -m benchmarks report benchmarks/results/<run>.json
```

Neither command overwrites an existing result or report. `validate` checks the
suite's top-level structural contract; it is not a full semantic certification
of every measurement.

## Comparing runs responsibly

For a useful local comparison:

1. Use the same commit, Python version, profile, warm-ups, and repetitions.
2. Close unrelated CPU- or disk-intensive applications.
3. Keep the same power and thermal conditions.
4. Compare Core and Lite from the same invocation.
5. Repeat the complete command and compare medians and p95 values, not only
   the fastest result.
6. Treat a result with `git_dirty: true` as exploratory.

Timing varies with CPU scheduling, filesystem cache, interpreter version,
storage, and background load. Dataset and query hashes establish identical
inputs, not identical machine state.

## Current limitations

- The corpus is synthetic and lexical; it does not represent every language or
  production distribution.
- Only `tiny`, `small`, and `medium` are stable profiles.
- There is no relevance ground truth, concurrency, throughput, sharding,
  worker, or external-project comparison.
- Backend load measurements share one load process and an uncontrolled OS page
  cache.
- Build, save, and load operations have one timing sample per invocation.
- Round-trip checks document IDs, not ranking order or scores.
- Environment metadata records platform, logical CPUs, Python, Lucis, and Git,
  but it does not yet record total system RAM; the CPU description can be
  generic on some platforms.
- Live progress is reported per engine rather than for every internal
  benchmark scenario.
- The current audit validated Linux locally: 100 benchmark tests and all 386
  repository tests passed. Cross-platform validation remains pending.

For the short runner-oriented reference, see
[`benchmarks/README.md`](../../benchmarks/README.md).

## Next step

- [Tests](16-tests.md) — Run the project validation suite
- [Search engines](04-engines.md) — Understand the Core and Lite algorithms
