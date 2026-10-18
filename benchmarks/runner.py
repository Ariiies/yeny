"""Subprocess orchestration for the Yeny benchmark suite.

Each engine runs one build phase plus one load phase per persistence
backend, every phase in a new interpreter inside one unique temporary
directory. This prevents CoreEngine and LiteEngine from sharing Python
state, keeps every backend load process-cold, and avoids accidentally
autoloading an existing ``yeny_data`` directory.
"""


from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple
from uuid import uuid4

from .config import BenchmarkRunConfig
from .environment import PROJECT_ROOT, collect_environment
from .memory import (
    MemoryUnavailableError,
    TreeRssSampler,
    build_memory_measurements,
    memory_mechanisms,
    psutil_available,
)
from .results import validate_result, write_result


LOAD_PHASES: Tuple[str, ...] = ("load_json", "load_sqlite", "load_mmap")
"""Per-backend load phases executed after the build phase, in order."""


class BenchmarkExecutionError(RuntimeError):
    """Raised when an isolated benchmark worker fails."""



def _run_id() -> str:
    """Create a collision-resistant, readable run identifier."""
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"{timestamp}-{uuid4().hex[:6]}"


def _worker_environment() -> Dict[str, str]:
    """Build an environment that can import Yeny and benchmarks."""
    environment = os.environ.copy()
    paths = [str(PROJECT_ROOT), str(PROJECT_ROOT / "src")]
    current = environment.get("PYTHONPATH")
    if current:
        paths.append(current)
    environment["PYTHONPATH"] = os.pathsep.join(paths)
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    return environment


def _run_worker(
    engine: str,
    config: BenchmarkRunConfig,
    workspace: Path,
    phase: str,
    temporary_path: Path,
) -> Dict[str, Any]:
    """Run one worker phase in an isolated process.

    Args:
        engine: Engine key, either ``"core"`` or ``"lite"``.
        config: Validated benchmark run configuration.
        workspace: Per-engine workspace shared by the build and load
            phases.
        phase: Worker phase: ``"build"`` or one of :data:`LOAD_PHASES`.
        temporary_path: Per-engine temporary directory used as the child
            working directory.


    Returns:
        Parsed worker response.

    Raises:
        BenchmarkExecutionError: If the worker exits unsuccessfully or does
            not create a readable response.
    """
    request_path = temporary_path / f"request_{phase}.json"
    response_path = temporary_path / f"response_{phase}.json"
    request = {
        "phase": phase,
        "engine": engine,
        "profile": config.profile,
        "warmups": config.warmups,
        "repetitions": config.repetitions,
        "workspace": str(workspace),
    }
    request_path.write_text(
        json.dumps(request),
        encoding="utf-8",
    )

    process = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "benchmarks.worker",
            str(request_path),
            str(response_path),
        ],
        cwd=str(temporary_path),
        env=_worker_environment(),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    sampler = None
    if psutil_available():
        # 5 ms instead of the nominal 20 ms: the preprocessing pools used
        # by small/medium profiles can live only a few dozen milliseconds,
        # and a coarser interval systematically misses them.
        sampler = TreeRssSampler(process.pid, interval_seconds=0.005)
        sampler.start()
    stdout, stderr = process.communicate()
    tree_summary = None
    if sampler is not None:
        sampler.stop()
        tree_summary = sampler.summary()

    if process.returncode != 0:
        detail = stderr.strip() or stdout.strip()
        raise BenchmarkExecutionError(
            f"{engine} {phase} worker exited with "
            f"{process.returncode}: {detail}"
        )
    try:
        with response_path.open("r", encoding="utf-8") as stream:
            response = json.load(stream)
    except (OSError, json.JSONDecodeError) as exc:
        raise BenchmarkExecutionError(
            f"{engine} {phase} worker produced an invalid response"
        ) from exc
    if not isinstance(response, dict):
        raise BenchmarkExecutionError(
            f"{engine} {phase} worker response must be an object"
        )
    response["memory_tree"] = tree_summary
    return response


def _run_engine(
    engine: str,
    config: BenchmarkRunConfig,
    *,
    progress: Optional[Callable[[str], None]] = None,
) -> Dict[str, Any]:
    """Run all four worker phases for one engine in one workspace.

    The build phase and the three per-backend load phases share the
    workspace but never an interpreter, so every backend load starts from
    a process-cold Python state. The workspace is always removed when the
    engine finishes, including after worker failures.

    Args:
        engine: Engine key, either ``"core"`` or ``"lite"``.
        config: Validated benchmark run configuration.
        progress: Optional callback receiving one ``[engine/phase]``
            message per phase.

    Returns:
        Combined dataset manifest, query manifest, and measurements from
        all four phases, with memory records labeled by phase.

    Raises:
        BenchmarkExecutionError: If a worker fails or a load phase reports
            a dataset hash different from the build phase.
    """
    with tempfile.TemporaryDirectory(
        prefix=f"yeny-benchmark-{engine}-"
    ) as temporary:
        temporary_path = Path(temporary)
        workspace = temporary_path / "workspace"
        phases = ("build", *LOAD_PHASES)
        measurements: List[Dict[str, Any]] = []
        dataset: Optional[Dict[str, Any]] = None
        queries: Optional[Dict[str, Any]] = None

        for phase in phases:
            if progress is not None:
                progress(f"[{engine}/{phase}]")
            response = _run_worker(
                engine, config, workspace, phase, temporary_path
            )
            if phase == "build":
                dataset = response["dataset"]
                queries = response["queries"]
            elif response["dataset_sha256"] != dataset["sha256"]:
                raise BenchmarkExecutionError(
                    f"{engine} {phase} worker reported a dataset hash "
                    f"different from the build phase"
                )
            measurements.extend(response["measurements"])
            measurements.extend(
                build_memory_measurements(
                    engine,
                    phase,
                    response.get("memory", {}),
                    response.get("memory_tree"),
                )
            )

        return {
            "dataset": dataset,
            "queries": queries,
            "measurements": measurements,
        }



def run_benchmarks(
    config: BenchmarkRunConfig,
    *,
    progress: Optional[Callable[[str], None]] = None,
) -> Tuple[Dict[str, Any], Path]:
    """Run all configured engines and persist one combined result.

    Args:
        config: Profile, engines, repetitions, and output configuration.
        progress: Optional callback receiving short progress messages.

    Returns:
        Tuple containing the result dictionary and written JSON path.

    Raises:
        ValueError: If configuration or output path is invalid.
        MemoryUnavailableError: If memory measurement was required but no
            RSS mechanism exists on this host.
        BenchmarkExecutionError: If an engine worker fails.
        OSError: If the result cannot be written.
    """
    config.validate()
    if config.require_memory and not memory_mechanisms():
        raise MemoryUnavailableError(
            "--require-memory was requested but no RSS mechanism is "
            "available (install psutil or use a Unix platform)"
        )
    started = datetime.now(timezone.utc)
    run_id = _run_id()
    responses: List[Dict[str, Any]] = []

    for engine in config.engines:
        if progress is not None:
            progress(
                f"[{engine}] running profile {config.profile} "
                f"in isolated processes..."
            )
        response = _run_engine(engine, config, progress=progress)
        responses.append(response)
        if progress is not None:
            progress(f"[{engine}] complete")


    measurements = [
        measurement
        for response in responses
        for measurement in response["measurements"]
    ]
    result: Dict[str, Any] = {
        "schema_version": "1.0",
        "run_id": run_id,
        "started_at_utc": started.isoformat(),
        "finished_at_utc": datetime.now(timezone.utc).isoformat(),
        "environment": collect_environment(),
        "configuration": config.to_dict(),
        "datasets": [responses[0]["dataset"]],
        "queries": responses[0]["queries"],
        "measurements": measurements,
    }
    validate_result(result)
    output_path = write_result(result, config.resolved_output_dir())
    return result, output_path
