"""External RSS sampling and self-reported memory for benchmark workers.

Three mechanisms, in priority order:

1. psutil tree sampling (primary): the runner samples the whole worker
   process tree every few milliseconds, which captures the
   ``parallel_preprocess`` child workers.
2. ``resource`` self peak (Unix fallback): the worker reports its own
   process-lifetime peak RSS; child workers are excluded and the value is
   a lifetime maximum, not a current reading.
3. ``/proc`` self current RSS (Linux fallback): the worker reports its own
   current RSS at the end of the phase after garbage collection.

Unavailable capabilities become explicit ``unavailable`` measurements with
empty samples and ``null`` summaries, never a fabricated zero.
"""

from __future__ import annotations

import gc
import os
import sys
import threading
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional

from .metrics import make_measurement

try:
    import psutil
except ImportError:
    psutil = None


class MemoryUnavailableError(RuntimeError):
    """Raised when memory measurement was required but cannot run."""


def psutil_available() -> bool:
    """Return ``True`` when the optional psutil dependency is importable.

    Returns:
        Whether psutil-backed tree sampling can run.
    """
    return psutil is not None


def self_peak_rss_bytes() -> Optional[int]:
    """Return the process-lifetime peak RSS of the current process.

    Uses ``resource.getrusage`` on Unix. The reported units are platform
    specific: Linux uses KiB while macOS uses bytes. Windows has no
    ``resource`` module, so the result is ``None`` there.

    Returns:
        Peak RSS in bytes, or ``None`` when the platform cannot report it.
    """
    try:
        import resource
    except ImportError:
        return None
    peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    if sys.platform == "darwin":
        return int(peak)
    return int(peak) * 1024


def self_current_rss_bytes() -> Optional[int]:
    """Return the current RSS of the current process when knowable.

    Prefers psutil and falls back to ``/proc/self/statm`` on Linux. Returns
    ``None`` when no standard mechanism exists, notably on Windows without
    psutil.

    Returns:
        Current RSS in bytes, or ``None`` when unavailable.
    """
    if psutil is not None:
        try:
            return int(psutil.Process().memory_info().rss)
        except Exception:
            return None
    statm = Path("/proc/self/statm")
    if statm.exists():
        try:
            resident_pages = int(statm.read_text().split()[1])
            return resident_pages * os.sysconf("SC_PAGE_SIZE")
        except (OSError, ValueError, IndexError):
            return None
    return None


def collect_self_memory() -> Dict[str, Optional[int]]:
    """Collect the worker's self-reported memory at the end of a phase.

    A garbage collection runs first to clear pending cycles. References still
    held by the phase and memory retained by the allocator may remain, so this
    value must not be interpreted as RSS after a complete teardown.

    Returns:
        Mapping with ``self_peak_rss_bytes`` and ``self_stable_rss_bytes``;
        either value may be ``None`` when the platform cannot report it.
    """
    gc.collect()
    return {
        "self_peak_rss_bytes": self_peak_rss_bytes(),
        "self_stable_rss_bytes": self_current_rss_bytes(),
    }


def memory_mechanisms() -> List[str]:
    """List the memory measurement mechanisms usable on this host.

    Returns:
        Subset of ``psutil``, ``resource``, and ``proc`` that can report
        real values right now.
    """
    mechanisms: List[str] = []
    if psutil_available():
        mechanisms.append("psutil")
    if self_peak_rss_bytes() is not None:
        mechanisms.append("resource")
    if self_current_rss_bytes() is not None:
        mechanisms.append("proc")
    return mechanisms


class TreeRssSampler:
    """Background sampler for the aggregate RSS of a worker process tree.

    A daemon thread polls the worker process and all its descendants every
    ``interval_seconds``. The summary distinguishes the first successful
    sample (baseline), the maximum aggregate (peak), and the largest number
    of simultaneous processes observed.
    """

    def __init__(self, pid: int, interval_seconds: float = 0.02) -> None:
        if psutil is None:
            raise MemoryUnavailableError(
                "TreeRssSampler requires the optional psutil dependency"
            )
        self._pid = pid
        self._interval = interval_seconds
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._baseline: Optional[int] = None
        self._peak: Optional[int] = None
        self._max_processes = 0
        self._sample_count = 0

    def _tree_rss(self) -> tuple:
        """Aggregate RSS and live process count for the whole tree."""
        try:
            process = psutil.Process(self._pid)
            members = [process, *process.children(recursive=True)]
        except psutil.NoSuchProcess:
            return 0, 0
        total = 0
        count = 0
        for member in members:
            try:
                total += member.memory_info().rss
                count += 1
            except psutil.NoSuchProcess:
                continue
        return total, count

    def _run(self) -> None:
        while not self._stop.is_set():
            total, count = self._tree_rss()
            if count:
                self._sample_count += 1
                self._max_processes = max(self._max_processes, count)
                if self._baseline is None:
                    self._baseline = total
                self._peak = (
                    total if self._peak is None else max(self._peak, total)
                )
            self._stop.wait(self._interval)

    def start(self) -> None:
        """Start the background sampling thread."""
        self._thread = threading.Thread(
            target=self._run,
            name="lucis-rss-sampler",
            daemon=True,
        )
        self._thread.start()

    def stop(self) -> None:
        """Stop sampling and wait briefly for the thread to finish."""
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=1.0 + 2 * self._interval)
            self._thread = None

    def summary(self) -> Dict[str, Optional[int]]:
        """Return the collected baseline, peak, and process statistics.

        Returns:
            Mapping with ``baseline_rss_bytes``, ``peak_rss_bytes``,
            ``max_processes``, and ``sample_count``. Values are ``None``
            when no successful sample was collected.
        """
        return {
            "baseline_rss_bytes": self._baseline,
            "peak_rss_bytes": self._peak,
            "max_processes": self._max_processes or None,
            "sample_count": self._sample_count,
        }


def _memory_measurement(
    name: str,
    value: Optional[int],
    *,
    unit: str,
    engine: str,
    phase: str,
    scope: str,
    limitations: List[str],
) -> Dict[str, Any]:
    """Build one memory measurement, unavailable when value is missing."""
    if value is None:
        return {
            "name": name,
            "unit": unit,
            "samples": [],
            "summary": {
                "count": 0,
                "min": None,
                "median": None,
                "p95": None,
                "max": None,
            },
            "status": "unavailable",
            "engine": engine,
            "phase": phase,
            "scope": scope,
            "limitations": limitations,
        }
    measurement = make_measurement(
        name,
        [value],
        unit=unit,
        engine=engine,
        phase=phase,
        scope=scope,
        limitations=limitations,
    )
    measurement["status"] = "ok"
    return measurement


def build_memory_measurements(
    engine: str,
    phase: str,
    self_report: Mapping[str, Optional[int]],
    tree_summary: Optional[Mapping[str, Optional[int]]],
) -> List[Dict[str, Any]]:
    """Convert collected memory data into measurement records.

    Args:
        engine: Engine key attached to the measurements.
        phase: Worker phase label, either ``build`` or ``load``.
        self_report: Worker-reported mapping produced by
            :func:`collect_self_memory`.
        tree_summary: Runner-side sampler summary, or ``None`` when psutil
            is not installed.

    Returns:
        Baseline, peak, peak-delta, stable, and process-count records.
        Missing capabilities keep ``status: unavailable`` and ``null``
        summaries; fallback values always declare their narrower scope.
    """
    baseline = (tree_summary or {}).get("baseline_rss_bytes")
    peak = (tree_summary or {}).get("peak_rss_bytes")
    max_processes = (tree_summary or {}).get("max_processes")
    self_peak = self_report.get("self_peak_rss_bytes")
    self_stable = self_report.get("self_stable_rss_bytes")

    measurements = [
        _memory_measurement(
            "memory_baseline_rss",
            baseline,
            unit="bytes",
            engine=engine,
            phase=phase,
            scope="process_tree",
            limitations=[] if baseline is not None else [
                "process-tree baseline requires the optional psutil dependency"
            ],
        )
    ]

    if peak is not None:
        measurements.append(
            _memory_measurement(
                "memory_peak_rss",
                peak,
                unit="bytes",
                engine=engine,
                phase=phase,
                scope="process_tree",
                limitations=[],
            )
        )
    else:
        fallback_limitations = [
            "process-tree sampling requires the optional psutil dependency",
            "self-only peak excludes child worker processes",
            "peak is a process-lifetime maximum, not a phase reading",
        ]
        measurements.append(
            _memory_measurement(
                "memory_peak_rss",
                self_peak,
                unit="bytes",
                engine=engine,
                phase=phase,
                scope="self_only",
                limitations=(
                    fallback_limitations
                    if self_peak is not None
                    else [
                        "no RSS mechanism available "
                        "(install psutil or use a Unix platform)"
                    ]
                ),
            )
        )

    delta = (
        peak - baseline
        if peak is not None and baseline is not None
        else None
    )
    measurements.append(
        _memory_measurement(
            "memory_peak_rss_delta",
            delta,
            unit="bytes",
            engine=engine,
            phase=phase,
            scope="process_tree",
            limitations=(
                [
                    "Peak RSS delta covers the whole phase and is not "
                    "exclusive to a single operation."
                ]
                if delta is not None
                else [
                    "process-tree sampling requires the optional "
                    "psutil dependency"
                ]
            ),
        )
    )
    measurements.append(
        _memory_measurement(
            "memory_stable_rss",
            self_stable,
            unit="bytes",
            engine=engine,
            phase=phase,
            scope="self_only",
            limitations=(
                [
                    "End-of-phase self RSS is captured after garbage "
                    "collection, but live references and allocator arenas "
                    "can remain."
                ]
                if self_stable is not None
                else [
                    "current RSS is unavailable on this platform "
                    "without psutil"
                ]
            ),
        )
    )
    measurements.append(
        _memory_measurement(
            "memory_max_processes",
            max_processes,
            unit="count",
            engine=engine,
            phase=phase,
            scope="process_tree",
            limitations=(
                []
                if max_processes is not None
                else [
                    "process counting requires the optional psutil dependency"
                ]
            ),
        )
    )
    return measurements
