# Lucis benchmarks

Small, deterministic benchmarks for the two public Lucis engines.

For concepts and result interpretation, read the
[English guide](../docs/en/17-benchmarks.md) or the
[Spanish guide](../docs/es/17-benchmarks.md). This file stays next to the
runner as its short operational reference.

## Quick start

From the repository root:

```bash
python -m benchmarks run --profile tiny
```

Run one engine or a larger local profile:

```bash
python -m benchmarks run --profile small --engine core
python -m benchmarks run --profile medium --engine lite
```

Available profiles:

| Profile | Documents |
|---|---:|
| `tiny` | 100 |
| `small` | 1,000 |
| `medium` | 10,000 |

The default command runs CoreEngine and LiteEngine in separate Python
processes. Both receive the same generated corpus, query set, and
`word_tokenizer`, making their measurements comparable.

## Current measurements

- Deterministic dataset generation.
- In-memory index construction without persistence.
- End-to-end index construction with automatic JSON persistence.
- First search after building.
- Warm searches grouped as common, rare, multi-token, no-result, and repeated.
- JSON and SQLite save durations plus on-disk artifact sizes.
- `.lcs` binary serialization duration and file size.
- Standard loads (JSON and SQLite) in a load process separate from the build
  process, with first and warm searches.
- Mmap loads in that same load process, with first and warm searches over
  mapped pages.
- Round-trip verification: every loaded index must return the same document
  ID set collected right after the build, for every query and every backend
  (JSON, SQLite, and mmap). Ranking order and score equality are not checked.

Each engine runs two separate Python processes. The build process constructs
the index, measures searches, and writes all persistence artifacts. A fresh
load process then measures JSON, SQLite, and mmap sequentially. This separates
loading from build-time Python state, but it does not give every backend its
own fresh interpreter, and the operating-system page cache is not controlled.
Both processes share one temporary workspace that is removed when the engine
finishes; mmap handles and SQLite connections are always closed first.

Every duration is recorded as raw nanoseconds. Artifact sizes are recorded
as real bytes; the SQLite size is taken after a commit and includes any
journal sidecar files. The terminal shows median and p95 summaries. The
complete result is saved as timestamped JSON under `benchmarks/results/` by
default.

## Memory measurements

With the optional `psutil` dependency (installable as the `benchmark` extra),
the runner samples the whole worker process tree every 5 ms and reports, per
engine and phase: baseline RSS, peak RSS, peak delta, end-of-phase self RSS
after garbage collection, and the maximum process count observed. Some live
references and allocator arenas can remain at the end of a phase. Tree sums
include fork copy-on-write pages, so they can overstate exclusive usage, and
short-lived worker pools may still fall below the sampling resolution.

Without psutil, Unix runs fall back to self-reported peak RSS via `resource`
(child worker processes excluded) and current RSS via `/proc` on Linux.
Unavailable capabilities are written as explicit `unavailable` measurements
with null summaries — never as zero. Use `--require-memory` to abort with
exit code 3 when no RSS mechanism exists on the host.

## Reporting and validation

Any saved run JSON can be validated and rendered as Markdown:

```bash
python -m benchmarks validate benchmarks/results/<run>.json
python -m benchmarks report benchmarks/results/<run>.json
```

`report` writes a sibling `<run>.md` next to the JSON and refuses to
overwrite an existing report.

Use a different output directory when needed:

```bash
python -m benchmarks run --profile tiny --output /tmp/lucis-results
```

The runner refuses to write benchmark results inside `src/`.

## Reproducibility

Dataset and query manifests contain their generator version, seed, and SHA-256
hash. Engine runs use separate temporary directories and interpreters, and
temporary storage is cleaned after each run.

These results describe one machine and one execution environment. They are not
search-quality measurements and should not be treated as universal performance
guarantees.
