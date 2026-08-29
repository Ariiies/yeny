# Lucis 0.1.0 benchmark documentation

This package is the publication record for the Lucis 0.1.0 cross-platform
benchmark campaign. It keeps raw evidence separate from generated reports and
editorial material.

## Start here

- [Resumen y conclusiones en español](reports/summary.es.md)
- [English summary and conclusions](reports/summary.en.md)
- [Index of all 16 generated reports](reports/README.md)
- [Presentación en español](presentation/benchmarks.es.md)
- [Benchmark methodology in Spanish](../es/17-benchmarks.md)
- [Benchmark methodology in English](../en/17-benchmarks.md)

## Directory layout

```text
docs/benchmarks/
├── README.md
├── raw/
│   ├── fedora/{tiny,small,medium,large}.json
│   ├── ubuntu/{tiny,small,medium,large}.json
│   ├── windows/{tiny,small,medium,large}.json
│   └── macos/{tiny,small,medium,large}.json
├── reports/
│   ├── README.md
│   ├── summary.es.md
│   ├── summary.en.md
│   └── individual/<platform>/<profile>.md
└── presentation/
    └── benchmarks.es.md
```

`raw/` contains publication copies of the original runner output. Local user
paths in `python_executable` and `output_dir` were replaced with `<redacted>`;
measurements, hashes, environment specifications, run IDs, and timestamps were
not edited. The shorter names reflect the profile declared inside each JSON.
In particular, the original fourth Windows file was named
`windows_4_medium.json` but declares `profile: large` and 100,000 documents,
so it is archived as `raw/windows/large.json`.

## Campaign status

- 4 operating systems and 4 profiles: 16 runs.
- Both public engines (`core`, `lite`) in every run.
- JSON, SQLite, and `.lcs`/`mmap` persistence paths in every run.
- 16/16 JSON files pass `python -m benchmarks validate`.
- Publication copies contain no local user paths.
- 17/17 round-trip queries pass for each engine and backend.
- Dataset and query hashes match across operating systems for each profile.
- All runs target Lucis 0.1.0 commit `a6ac3de8`.

The macOS records are valid but exploratory: their environment reports a
dirty Git tree and no `psutil`. Memory values unavailable on that host remain
`null`, as required by the schema.

## Rebuild and verify the documentation

Validate one raw result:

```bash
python -m benchmarks validate docs/benchmarks/raw/fedora/large.json
```

Regenerate an individual report in a temporary directory, because the report
command deliberately refuses to overwrite an existing file:

```bash
cp docs/benchmarks/raw/fedora/large.json /tmp/lucis-fedora-large.json
python -m benchmarks report /tmp/lucis-fedora-large.json
```

## Publication checklist

- [x] Archive the four profiles from Fedora, Ubuntu, Windows, and macOS.
- [x] Normalize platform and profile names.
- [x] Validate every raw result.
- [x] Generate a full report for every result.
- [x] Document the campaign in Spanish and English.
- [x] Prepare a presentation with the principal findings.
- [x] Link the campaign from the main benchmark documentation.
- [ ] Repeat each profile at least three times before presenting confidence
  intervals or treating cross-machine differences as stable.
- [ ] Re-run macOS from a clean tree with `psutil` before citing its memory
  measurements as part of the official comparison.
