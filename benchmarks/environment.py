"""Environment metadata collection for benchmark result files.

Only standard-library information is collected. Every field is best effort so
that missing platform details never prevent a benchmark run.
"""

from __future__ import annotations

import os
import platform
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, Optional

from lucis import __version__ as lucis_version


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _git_output(*args: str) -> Optional[str]:
    """Return one short Git command result, or ``None`` when unavailable."""
    try:
        completed = subprocess.run(
            ["git", *args],
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            check=True,
            text=True,
            timeout=2,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return completed.stdout.strip()


def collect_environment() -> Dict[str, Any]:
    """Collect hardware, software, and repository metadata.

    Returns:
        JSON-compatible dictionary describing the Python interpreter, Lucis,
        operating system, CPU count, and current Git revision.
    """
    git_status = _git_output("status", "--porcelain")
    return {
        "python_version": platform.python_version(),
        "python_implementation": platform.python_implementation(),
        "python_executable": sys.executable,
        "lucis_version": lucis_version,
        "platform": platform.platform(),
        "system": platform.system(),
        "release": platform.release(),
        "machine": platform.machine(),
        "processor": platform.processor() or None,
        "logical_cpu_count": os.cpu_count(),
        "git_commit": _git_output("rev-parse", "HEAD"),
        "git_dirty": bool(git_status) if git_status is not None else None,
    }
