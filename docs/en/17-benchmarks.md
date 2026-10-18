# Benchmarks

Yeny includes a small, deterministic benchmark suite for answering practical
questions about its two public engines:

- How long does it take to build an index?
- How long do different kinds of searches take?
- How long do JSON, SQLite, and `.yny` persistence operations take?
- How large are the generated artifacts?
- What happens when an index is loaded normally or through `mmap`?
- Does persistence preserve result IDs, ranking order, and scores?
- How much RSS memory is visible during each worker phase?

The suite does **not** measure search relevance, accuracy, recall, concurrent
throughput, or performance against external search projects.

## Quick start

Run commands from a local clone of the Yeny repository:

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
`medium` is the scaling check, and `large` is the opt-in official scaling
limit. `large` never runs by accident: it must be requested explicitly.

## Reproducible profiles

| Profile | Documents | Vocabulary | Document length | Default |
|---|---:|---:|---:|---|
| `tiny` | 100 | 2,048 terms | 12–52 tokens | Yes |
| `small` | 1,000 | 2,048 terms | 12–52 tokens | Opt-in |
| `medium` | 10,000 | 2,048 terms | 12–52 tokens | Opt-in |
| `large` | 100,000 | 2,048 terms | 12–52 tokens | Opt-in |

All profiles use:

- seed `20260117`;
- generator `lexical_zipf_v1`;
- a Zipf-like term distribution with exponent `1.07`;
- a triangular document-length distribution with a mode of 32 tokens;
- 2% intentional duplicate documents;
- 17 deterministic queries: 4 common, 4 rare, 4 multi-token, 4 no-result,
  and 1 repeated query.

Every profile has frozen SHA-256 dataset and query hashes in
`benchmarks/reference_hashes.json`. Before any engine is measured, the build
worker regenerates the corpus and compares both hashes against the frozen
contract. A mismatch aborts the run: it means the deterministic generator
diverged, and the cause must be investigated rather than the reference edited.
The hashes prove that two runs received identical generated inputs; they do
not mean the measured time will be identical.

## A fair Core/Lite comparison

`CoreEngine` uses TF-IDF and cosine similarity. `LiteEngine` uses normalized
term frequency. Their ranking behavior is different, but both are pure-Python
engines exposed by the same `Yeny` facade.

For timing fairness, the benchmark gives both engines the exact same corpus,
query set, `top_k=10`, and `WordTokenizer`. This is important because
`LiteEngine` normally uses character trigrams by default. Comparing each
engine with a different tokenizer would mix engine cost with tokenization and
index-size differences.

Consequently, these numbers compare the two ranking implementations under one
controlled lexical configuration. They do not compare their native defaults
and do not establish which engine produces more relevant results.

## How to read the numbers

Build, save, load, and size measurements have one sample per run. Their
displayed median and p95 are therefore the same value. Search categories
contain several samples per category (40 with the default 10 repetitions),
and the repeated-query category contains 100, so median and p95 are useful
there. Run the command several times and aggregate when comparing one-sample
operations.

One invocation is one machine and one moment. For campaign data, run the same
command several times and combine the results with `aggregate` (below), which
reports the median of per-run medians plus the minimum and maximum as the
variability range.

## Metrics

| Metric | Measured boundary |
|---|---|
| `dataset_generation` | Deterministic corpus generation only |
| `index_build` | `Yeny.index(..., persist=False)` |
| `index_e2e_json` | Construction through `Yeny.from_dict`, including automatic JSON persistence |
| `search_first` | First public `Yeny.search` after building |
| `search_warm` | Public searches after unmeasured warm-ups, grouped by query category |
| `json_save`, `sqlite_save` | Public `Yeny.save` |
| `*_artifact_size` | Real bytes written on disk |
| `yny_write` | Engine `.yny` serialization |
| `load_standard` | Autoloading `Yeny` constructor for JSON or SQLite |
| `mmap_load` | Engine `load_mmap` operation |
| `search_first_*`, `search_warm_*` | Public search after standard or mapped loading |
| `roundtrip_verified` | Number of queries preserving IDs, ranking order, and scores |
| `memory_*` | RSS observations for one complete worker phase |

Search time includes query preprocessing and response construction because the
timer surrounds the public `Yeny.search` call.

Round-trip verification compares, for every query and every backend (JSON,
SQLite, and `mmap`): the number of results, the document ID at each ranking
position, the complete order, and each score within a documented tolerance
(`rel_tol=1e-9`, `abs_tol=1e-12`). Any difference aborts the run instead of
writing a seemingly successful result. It is a persistence-fidelity proof,
not a relevance metric.

## Process and memory model

Core and Lite run separately. Each engine gets **four** fresh Python
interpreters inside one unique temporary workspace:

```text
engine
├── build          generates the corpus, builds, searches, persists everything
├── load_json      reloads the JSON artifact in a cold interpreter
├── load_sqlite    reloads the SQLite artifact in a cold interpreter
└── load_mmap      maps the .yny artifact in a cold interpreter
```

The build process writes the dataset manifest, the query set, the expected
per-query results, and the JSON/SQLite/`.yny` artifacts into the workspace.
Each load process reads that contract — without regenerating the corpus — and
measures exactly one backend, so no backend inherits import caches or engine
state warmed by a previous one. Process creation time stays outside the
measured load boundary. SQLite connections and mmap handles are always closed
before the workspace is removed.

This makes every load "process-cold" with respect to the Python interpreter.
The operating-system page cache is **not** flushed or controlled — there is no
portable, safe way to do so — and that limitation is stated in every report.

When `psutil` is installed, the parent samples the complete worker process
tree every 5 ms and reports, per engine **and phase** (`build`, `load_json`,
`load_sqlite`, `load_mmap`): baseline RSS, peak RSS, peak delta, end-of-phase
self RSS after garbage collection, and the maximum process count. These
values describe the whole phase workflow, not the exclusive size of any
engine object. RSS is not exclusive ownership: forked copy-on-write pages may
be counted more than once, short-lived peaks may be missed, allocator arenas
can remain, and live references may still exist at phase end.

Without `psutil`, Unix can fall back to self-only peak RSS through `resource`;
Linux can also read current self RSS from `/proc`. Missing capabilities appear
as `unavailable` with null summaries, never as zero. `--require-memory`
aborts with exit code 3 when no mechanism exists on the host.

## Captured metadata

Each result JSON identifies its machine with:

| Metadata | Source |
|---|---|
| Python version, implementation, executable | Standard library |
| Yeny version | Package metadata |
| System, release, platform, architecture | Standard library |
| CPU model | `/proc/cpuinfo`, `PROCESSOR_IDENTIFIER`, or `sysctl` |
| Logical CPUs | `os.cpu_count()` |
| Total RAM bytes | `psutil`, `/proc/meminfo`, `GlobalMemoryStatusEx`, or `sysctl` |
| `psutil` version | Package metadata, when installed |
| Usable memory mechanisms | Detected at runtime |
| `perf_counter` resolution | `time.get_clock_info` |
| Git commit and dirty state | `git`, best effort |
| UTC timestamps and full configuration | The runner itself |
| Dataset and query SHA-256 hashes | The frozen reference contract |

Every collector is best effort: an absent capability is stored as `null`,
never as zero.

## Results, validation, and reports

By default, timestamped JSON results are written to
`benchmarks/results/`, which is ignored by Git:

```bash
python -m benchmarks run --profile small
```

Use another output directory if preferred:

```bash
python -m benchmarks run --profile small --output /tmp/yeny-results
```

Validate the full result contract:

```bash
python -m benchmarks validate benchmarks/results/<run>.json
```

`validate` goes far beyond structure: it checks timestamps, the frozen
dataset/query hashes, that every summary is exactly consistent with its raw
samples, that unavailable memory is null rather than zero, that each
requested engine produced the complete metric matrix, and that every backend
verified all 17 round-trip queries. An altered or incomplete JSON is rejected
with exit code 4 and an actionable message.

Create a readable Markdown report next to the JSON:

```bash
python -m benchmarks report benchmarks/results/<run>.json
```

Neither command overwrites an existing result or report.

## Published Yeny 0.1.0 campaign

The repository includes a complete campaign run on Fedora, Ubuntu, Windows
11, and macOS. It covers the `tiny`, `small`, `medium`, and `large` profiles
for Core and Lite: 16 result JSON files, all validated against schema 1.0 and
with round-trip fidelity confirmed for all 17 queries through JSON, SQLite,
and `mmap`.

The campaign is archived with its original data, individual reports,
editorial summaries, and presentation under
[`docs/benchmarks`](../benchmarks/README.md). Read the
[English summary](../benchmarks/reports/summary.en.md) and its
caveats before quoting a number.

The results were collected at Yeny 0.1.0 commit `a6ac3de8`. Each profile has
one run per machine, while CPU, Python version, and operating system differ.
Core and Lite can therefore be compared within one run, but values across
machines are not an operating-system ranking. The macOS run is explicitly
marked exploratory because it recorded `git_dirty: true` and had no
`psutil` support.

## Aggregating several runs

Combine compatible official runs without transcribing numbers:

```bash
python -m benchmarks aggregate benchmarks/results/*.json --output summary.md
```

This writes `summary.md` plus a traceable `summary.aggregate.json`. The
aggregator first validates every file deeply, then refuses to mix runs that
differ in schema version, Yeny version, commit, Python minor version,
profile, dataset hash, query hash, engines, warm-ups, repetitions, or memory
requirement. Runs from different operating systems or machines are reported
as separate groups, never merged.

For each metric the summary publishes the median of per-run medians, the
minimum and maximum of those medians as the variability range, the median of
per-run p95 values, the number of runs, and the originating run IDs. Nothing
is discarded as an outlier; variability above 20% is listed as a warning for
manual review, along with dirty-tree runs and missing metadata.

## Comparing runs responsibly

For a useful local comparison:

1. Use the same commit, Python version, profile, warm-ups, and repetitions.
2. Close unrelated CPU- or disk-intensive applications.
3. Keep the same power and thermal conditions.
4. Compare Core and Lite from the same invocation.
5. Repeat the complete command and compare aggregated medians, not only the
   fastest result.
6. Treat a result with `git_dirty: true` as exploratory.

Timing varies with CPU scheduling, filesystem cache, interpreter version,
storage, and background load. Dataset and query hashes establish identical
inputs, not identical machine state.

## Current limitations

- The corpus is synthetic and lexical; it does not represent every language or
  production distribution.
- No profile exceeds 100,000 documents for this release.
- There is no relevance ground truth, concurrency, throughput, sharding,
  worker, or external-project comparison.
- Loads are process-cold per backend, but the OS page cache is uncontrolled.
- Build, save, and load operations have one timing sample per invocation;
  aggregate several runs for campaign figures.
- RSS sums shared pages and can overstate exclusive memory; sampling can miss
  short-lived helper processes.
- Cross-platform preflight is tracked separately from this document.

For the short runner-oriented reference, see
[`benchmarks/README.md`](../../benchmarks/README.md).

## Next step

- [Tests](16-tests.md) — Run the project validation suite
- [Search engines](04-engines.md) — Understand the Core and Lite algorithms
