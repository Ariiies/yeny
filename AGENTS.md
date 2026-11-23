# AGENTS.md — Operational Contract for AI Agents

This document defines the operational rules, architectural boundaries, and quality gates for AI agents contributing to **Yeny**. All instructions are directive and mandatory.

---

## 1. Project Context

- **Yeny** is a pure-Python (3.10+) modular full-text search toolkit featuring zero mandatory core dependencies, optional SQL storage extras, and binary memory-mapped index persistence (`.yny`).
- **Architectural Reference:** Read [`docs/ARCHITECT.md`](docs/ARCHITECT.md) for module boundaries, mixin layouts, and design invariants.
- **Documentation Scope:** Read documentation under [`docs/en/`](docs/en/). **Strictly ignore [`docs/es/`](docs/es/)** (it is a Spanish mirror and consumes context unnecessarily) unless explicitly requested to perform a translation task.

---

## 2. Standard Commands

Execute commands via bash inside the workspace root:

```bash
# Run full test suite (quiet)
python -m pytest -q

# Run targeted test file
python -m pytest -q tests/test_core/test_core_engine.py

# Run single test by expression
python -m pytest -q tests/test_core/test_core_engine.py -k "test_search_returns_ranked_results"

# Run local benchmark suite
python -m benchmarks run --profile tiny
```

---

## 3. Core Engineering Rules

### WIP = 1 (Single-Task Constraint)
- Maintain strict **WIP = 1**: work on exactly one atomic task or subtask at a time.
- Verify and complete the active task before starting the next.
- If `PROGRESS.md` is present, keep it updated after each step.
- **Scope Discipline:** Focus strictly on the task at hand; do not refactor unrelated code or rewrite legacy docstrings outside the active task scope.

### Data Modeling (`dataclass` vs. `Pydantic`)
- **Default:** Always use standard-library `dataclasses` (prefer `@dataclass(frozen=True)` as demonstrated in `src/yeny/config.py`) for configs, internal states, and zero-dependency core modules.
- **Pydantic Policy:** `Pydantic` is **not** a core dependency. If future expansions introduce complex external I/O boundaries, API payloads, or strict schema validation between services, explicitly evaluate whether `Pydantic` is justified. If adopted, it must remain an optional extra (`project.optional-dependencies`) so the core engine stays zero-dependency.

### Mandatory Test Gate & Ephemeral Storage
- Always execute `python -m pytest -q` before declaring any task finished.
- In tests, always use `MemoryStorage`, pass `persist=False`, or utilize pytest's `tmp_path` fixture.
- Never write persistent artifacts (`yeny_meta.db`, `.yny` files) to the project root or tracked directories during test runs.

### Minimal & Pragmatic Documentation Policy
- Author all code, comments, docstrings, and notes in **English**.
- Write concise, high-signal docstrings and comments. Avoid stating the obvious or repeating type annotations.
- Legacy docstrings in parts of the codebase are verbose and scheduled for a separate refactor. **Do not perpetuate or imitate this verbosity** in new or updated code.

### Architecture & Dependency Hygiene
- Respect the Facade + Mixin architecture (`Yeny` in `src/yeny/main.py` orchestrating `mixins/`).
- Shared internal registries and lazy import loaders belong in `src/yeny/_internals.py`.
- Keep heavy external libraries (`sqlalchemy`, `pymysql`, `psutil`) lazily imported behind functions. Never introduce mandatory third-party imports into the core search or indexing path.

### Git Boundaries (Strict Read-Only)
- **NEVER** execute mutating Git commands: `git add`, `git commit`, `git push`, `git checkout`, `git branch -D`, or `git reset`.
- Only read-only inspections (e.g., `git status`, `git diff`) are permitted when necessary.
- Leave all file edits unstaged in the working tree for manual review by the maintainer.

---

## 4. Definition of Done (DoD) Checklist

Before finishing any turn or declaring a task complete, verify:

- [ ] **WIP = 1 Preserved:** Completed exactly one atomic task (and updated `PROGRESS.md` if present).
- [ ] **Scope Discipline:** Touched only files strictly relevant to the active task; no unrelated refactoring.
- [ ] **Zero Core Dependencies:** Core runtime relies solely on Python 3.10+ standard library.
- [ ] **No Disk Artifacts:** Tests and executions use `MemoryStorage` or clean up temporary files.
- [ ] **High Signal, Low Bloat:** Code and docstrings are concise, in English, and free of redundant prose.
- [ ] **Test Gate Passed:** `python -m pytest -q` executed with zero regressions reported.
- [ ] **Git Pristine:** No commits, branches, or pushes executed.
