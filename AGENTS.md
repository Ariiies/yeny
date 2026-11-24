# AGENTS.md — Yeny

Pure-Python (3.10+) modular full-text search toolkit with zero mandatory core dependencies, optional SQL extras, and `.yny` (`mmap`) binary persistence.

## 1. Context Routing
- **Architecture & module map (read first when modifying code):** [`docs/ARCHITECT.md`](docs/ARCHITECT.md)
- **Active task state (read if present):** `PROGRESS.md`
- **Human guides (on-demand only — do NOT preload):** [`docs/en/`](docs/en/) — inspect specific files only when clarifying public API behavior.
- **Ignore:** [`docs/es/`](docs/es/) (Spanish mirror; never read unless explicitly asked to translate).

---

## 2. Standard Commands

Execute commands via bash from the workspace root using the project's active Python 3.10+ environment (package lives under `src/yeny/` and assumes editable install):

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

### Data Modeling & Typing
Default: Use standard-library dataclasses (prefer @dataclass(frozen=True) as in src/yeny/config.py) for configs, internal states, and core modules.

Pydantic Policy: Never add Pydantic or third-party validation libraries to the core runtime; they may only be introduced as optional extras (project.optional-dependencies) if explicitly approved for complex external I/O boundaries.

Type Annotations: Add concise Python 3.10+ type hints on all new or modified public signatures and avoid repeating them in docstrings.

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
