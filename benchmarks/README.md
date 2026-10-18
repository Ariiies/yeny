# Yeny benchmarks

Small, deterministic benchmarks for the two public Yeny engines.

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
python -m benchmarks run --profile large --require-memory
```

Available profiles:

| Profile | Documents | Default |
|---|---:|---|
| `tiny` | 100 | Yes (smoke) |
| `small` | 1,000 | Opt-in |
| `medium` | 10,000 | Opt-in |
| `large` | 100,000 | Opt-in (official scaling limit) |

The default command runs CoreEngine and LiteEngine in separate Python
processes. Both receive the same generated corpus, query set, and
`word_tokenizer`, making their measurements comparable. `large` is never part
of the default or smoke run; it must be requested explicitly.

Every profile carries frozen dataset and query SHA-256 hashes in
`reference_hashes.json`. The build worker regenerates the corpus and compares
both hashes before measuring anything; a mismatch aborts the run and must be
investigated, never silenced by editing the reference.

## Current measurements

- Deterministic dataset generation.
- In-memory index construction without persistence.
- End-to-end index construction with automatic JSON persistence.
- First search after building.
- Warm searches grouped as common, rare, multi-token, no-result, and repeated.
- JSON and SQLite save durations plus on-disk artifact sizes.
- `.yny` binary serialization duration and file size.
- Standard loads (JSON and SQLite), each in its own fresh interpreter, with
  first and warm searches.
- Mmap loads in their own fresh interpreter, with first and warm searches
  over mapped pages.
- Round-trip verification: every loaded index must return, for every query
  and every backend (JSON, SQLite, and mmap), the same result count, the same
  document IDs in the same ranking order, and the same scores within the
  documented tolerance (`rel_tol=1e-9`, `abs_tol=1e-12`). Any difference
  aborts the run.

Each engine runs **four** separate Python processes. The build process
generates the corpus, builds and searches the index, writes all persistence
artifacts, and stores the dataset/query contract in a shared workspace. One
fresh process per backend then measures exactly one load path without
regenerating the corpus, so no backend inherits Python state warmed by a
previous one ("process-cold" per backend). The operating-system page cache is
not controlled, and that limitation is printed in every report. All four
processes share one temporary workspace that is removed when the engine
finishes; mmap handles and SQLite connections are always closed first.

Live progress is printed per phase:

```text
[core/build]
[core/load_json]
[core/load_sqlite]
[core/load_mmap]
[lite/build]
...
```

Every duration is recorded as raw nanoseconds. Artifact sizes are recorded
as real bytes; the SQLite size is taken after a commit and includes any
journal sidecar files. The terminal shows median and p95 summaries. The
complete result is saved as timestamped JSON under `benchmarks/results/` by
default.

## Memory measurements

With the optional `psutil` dependency (installable as the `benchmark` extra),
the runner samples the whole worker process tree every 5 ms and reports, per
engine and phase (`build`, `load_json`, `load_sqlite`, `load_mmap`): baseline
RSS, peak RSS, peak delta, end-of-phase self RSS after garbage collection,
and the maximum process count observed. These values describe the whole phase
workflow, not the exclusive size of any engine object. Tree sums include fork
copy-on-write pages, so they can overstate exclusive usage, and short-lived
worker pools may still fall below the sampling resolution.

Without psutil, Unix runs fall back to self-reported peak RSS via `resource`
(child worker processes excluded) and current RSS via `/proc` on Linux.
Unavailable capabilities are written as explicit `unavailable` measurements
with null summaries — never as zero. Use `--require-memory` to abort with
exit code 3 when no RSS mechanism exists on the host.

Each result also records machine metadata: Python version/implementation/
executable, Yeny version, OS fields, CPU model, logical CPUs, total RAM in
bytes, `psutil` version, usable memory mechanisms, `perf_counter` resolution,
Git commit/dirty state, UTC timestamps, the full configuration, and the
dataset/query hashes. Absent capabilities are stored as `null`.

## Reporting and validation

Any saved run JSON can be validated and rendered as Markdown:

```bash
python -m benchmarks validate benchmarks/results/<run>.json
python -m benchmarks report benchmarks/results/<run>.json
```

`validate` checks the full contract: timestamps, frozen dataset/query hashes,
summary-versus-samples coherence, null (not zero) unavailable memory, the
complete per-engine metric matrix, and all 17 round-trip queries per backend.
An altered or incomplete JSON exits with code 4 and an actionable message.

`report` writes a sibling `<run>.md` next to the JSON and refuses to
overwrite an existing report.

Use a different output directory when needed:

```bash
python -m benchmarks run --profile tiny --output /tmp/yeny-results
```

The runner refuses to write benchmark results inside `src/`.

## Aggregating runs

Combine several compatible runs without transcribing numbers:

```bash
python -m benchmarks aggregate benchmarks/results/*.json --output summary.md
```

This writes `summary.md` and a traceable `summary.aggregate.json`; neither is
overwritten. The aggregator deeply validates every input and rejects mixes
that differ in schema version, Yeny version, commit, Python minor version,
profile, dataset or query hash, engines, warm-ups, repetitions, or memory
requirement. Different operating systems or machines stay in separate groups.
Each metric publishes the median of per-run medians, the min/max of those
medians, the median of per-run p95 values, the run count, and the origin run
IDs. Variability above 20%, dirty trees, and missing metadata become
warnings, not automatic failures.

## Reproducibility

Dataset and query manifests contain their generator version, seed, and SHA-256
hash. Engine runs use separate temporary directories and interpreters, and
temporary storage is cleaned after each run.

These results describe one machine and one execution environment. They are not
search-quality measurements and should not be treated as universal performance
guarantees.
