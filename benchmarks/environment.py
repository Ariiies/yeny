"""Environment metadata collection for benchmark result files.

Every field is best effort so that missing platform details never prevent a
benchmark run: an absent capability is recorded as ``None`` (JSON ``null``),
never as zero. Hardware identifiers allow each saved result to be traced back
to the machine that produced it without external notes.
"""

from __future__ import annotations

import os
import platform
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from lucis import __version__ as lucis_version

from .memory import memory_mechanisms, psutil_available

try:
    import psutil
except ImportError:
    psutil = None


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


def _linux_cpu_model() -> Optional[str]:
    """Read the CPU model from ``/proc/cpuinfo``."""
    cpuinfo = Path("/proc/cpuinfo")
    if not cpuinfo.exists():
        return None
    try:
        for line in cpuinfo.read_text(encoding="utf-8").splitlines():
            if line.lower().startswith("model name"):
                _, _, value = line.partition(":")
                if value.strip():
                    return value.strip()
    except OSError:
        return None
    return None


def _macos_cpu_model() -> Optional[str]:
    """Read the CPU model through ``sysctl`` on macOS."""
    try:
        completed = subprocess.run(
            ["sysctl", "-n", "machdep.cpu.brand_string"],
            capture_output=True,
            check=True,
            text=True,
            timeout=2,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return completed.stdout.strip() or None


def cpu_model() -> Optional[str]:
    """Return the host CPU model name when the platform can report it.

    Uses ``/proc/cpuinfo`` on Linux, ``platform.processor`` and
    ``PROCESSOR_IDENTIFIER`` on Windows, and ``sysctl`` on macOS.

    Returns:
        CPU model string, or ``None`` when no mechanism reports one.
    """
    system = platform.system()
    if system == "Linux":
        model = _linux_cpu_model()
        if model:
            return model
    elif system == "Darwin":
        model = _macos_cpu_model()
        if model:
            return model
    elif system == "Windows":
        model = platform.processor() or os.environ.get(
            "PROCESSOR_IDENTIFIER"
        )
        if model:
            return model.strip()
    fallback = platform.processor()
    return fallback.strip() if fallback and fallback.strip() else None


def _linux_total_ram_bytes() -> Optional[int]:
    """Read total RAM from ``/proc/meminfo``."""
    meminfo = Path("/proc/meminfo")
    if not meminfo.exists():
        return None
    try:
        for line in meminfo.read_text(encoding="utf-8").splitlines():
            if line.startswith("MemTotal:"):
                parts = line.split()
                return int(parts[1]) * 1024
    except (OSError, ValueError, IndexError):
        return None
    return None


def _windows_total_ram_bytes() -> Optional[int]:
    """Read total RAM through ``GlobalMemoryStatusEx`` on Windows."""
    try:
        import ctypes

        class _MemoryStatus(ctypes.Structure):
            _fields_ = [
                ("dwLength", ctypes.c_ulong),
                ("dwMemoryLoad", ctypes.c_ulong),
                ("ullTotalPhys", ctypes.c_ulonglong),
                ("ullAvailPhys", ctypes.c_ulonglong),
                ("ullTotalPageFile", ctypes.c_ulonglong),
                ("ullAvailPageFile", ctypes.c_ulonglong),
                ("ullTotalVirtual", ctypes.c_ulonglong),
                ("ullAvailVirtual", ctypes.c_ulonglong),
                ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
            ]

        status = _MemoryStatus()
        status.dwLength = ctypes.sizeof(_MemoryStatus)
        if not ctypes.windll.kernel32.GlobalMemoryStatusEx(
            ctypes.byref(status)
        ):
            return None
        return int(status.ullTotalPhys)
    except (ImportError, AttributeError, ValueError):
        return None


def _macos_total_ram_bytes() -> Optional[int]:
    """Read total RAM through ``sysctl`` on macOS."""
    try:
        completed = subprocess.run(
            ["sysctl", "-n", "hw.memsize"],
            capture_output=True,
            check=True,
            text=True,
            timeout=2,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    try:
        return int(completed.stdout.strip())
    except ValueError:
        return None


def total_ram_bytes() -> Optional[int]:
    """Return total physical RAM in bytes when knowable.

    Prefers ``psutil.virtual_memory`` and falls back to
    ``/proc/meminfo`` on Linux, ``GlobalMemoryStatusEx`` on Windows, and
    ``sysctl`` on macOS.

    Returns:
        Total RAM in bytes, or ``None`` when no mechanism reports it.
    """
    if psutil is not None:
        try:
            return int(psutil.virtual_memory().total)
        except Exception:
            pass
    system = platform.system()
    if system == "Linux":
        return _linux_total_ram_bytes()
    if system == "Windows":
        return _windows_total_ram_bytes()
    if system == "Darwin":
        return _macos_total_ram_bytes()
    return None


def psutil_version() -> Optional[str]:
    """Return the installed psutil version, or ``None`` when absent."""
    if psutil is None:
        return None
    return str(getattr(psutil, "__version__", None) or "") or None


def perf_counter_resolution() -> Optional[float]:
    """Return the resolution of ``time.perf_counter`` in seconds."""
    try:
        return float(time.get_clock_info("perf_counter").resolution)
    except (ValueError, OSError):
        return None


def collect_environment() -> Dict[str, Any]:
    """Collect hardware, software, and repository metadata.

    Returns:
        JSON-compatible dictionary describing the Python interpreter,
        Lucis, the operating system, the CPU model, the logical CPU count,
        total RAM, the psutil version, the usable memory mechanisms, the
        perf_counter resolution, and the current Git revision. Absent
        capabilities are ``None``, never zero.
    """
    git_status = _git_output("status", "--porcelain")
    mechanisms: List[str] = memory_mechanisms()
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
        "cpu_model": cpu_model(),
        "logical_cpu_count": os.cpu_count(),
        "total_ram_bytes": total_ram_bytes(),
        "psutil_version": psutil_version(),
        "psutil_available": psutil_available(),
        "memory_mechanisms": mechanisms,
        "perf_counter_resolution_seconds": perf_counter_resolution(),
        "git_commit": _git_output("rev-parse", "HEAD"),
        "git_dirty": bool(git_status) if git_status is not None else None,
    }
