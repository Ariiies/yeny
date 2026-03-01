"""
Lucis Health Monitor — RAM, timing, and shard diagnostics.

Provides real-time visibility into resource consumption without
modifying the indexing or search pipeline.  Designed to be attached
to a running ``Lucis`` instance via ``Lucis.health_check()`` or
used standalone for periodic monitoring.

Example — one-shot health check::

    from lucis import Lucis

    luc = Lucis(name="email_idx", engine="lite",
                storage_type="alchemy", alchemy_url=DB_URL)
    report = luc.health_check()
    print(report)

Example — continuous monitoring::

    monitor = luc.health_monitor(interval=30)
    monitor.start()
    # ... app runs ...
    monitor.stop()
    monitor.print_summary()
"""
from __future__ import annotations

import array
import gc
import logging
import sys
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger("lucis.health")


# ─── RAM measurement utilities ───────────────────────────────────────

def _deep_getsizeof(obj: Any, seen: Optional[set] = None) -> int:
    """Recursively measure the memory footprint of an object.

    Walks dicts, lists, tuples, sets and their contents.  Avoids
    infinite loops via an ``id()`` seen-set.  This gives a *rough*
    estimate — the real RSS may differ due to allocator overhead,
    but it's accurate enough for monitoring trends.

    Handles compact structures (``CompactPostings``, ``CompactDocLengths``)
    by measuring their internal ``array.array`` buffers directly.
    """
    if seen is None:
        seen = set()
    obj_id = id(obj)
    if obj_id in seen:
        return 0
    seen.add(obj_id)

    size = sys.getsizeof(obj)

    # array.array — sys.getsizeof already includes the buffer for arrays,
    # so just return it directly (no need to recurse into elements).
    if isinstance(obj, array.array):
        return size

    # CompactPostings / CompactDocLengths — measure internal arrays
    if hasattr(obj, "__slots__"):
        for slot in obj.__slots__:
            attr = getattr(obj, slot, None)
            if attr is not None:
                size += _deep_getsizeof(attr, seen)
        return size

    if isinstance(obj, dict):
        for k, v in obj.items():
            size += _deep_getsizeof(k, seen)
            size += _deep_getsizeof(v, seen)
    elif isinstance(obj, (list, tuple, set, frozenset)):
        for item in obj:
            size += _deep_getsizeof(item, seen)

    return size


def _format_bytes(n: int) -> str:
    """Human-readable byte size (KB / MB / GB)."""
    if n < 1024:
        return f"{n} B"
    elif n < 1024 ** 2:
        return f"{n / 1024:.1f} KB"
    elif n < 1024 ** 3:
        return f"{n / (1024 ** 2):.1f} MB"
    else:
        return f"{n / (1024 ** 3):.2f} GB"


def _get_process_rss() -> Optional[int]:
    """Return the current process RSS in bytes, or ``None`` if unavailable.

    Uses ``psutil`` if installed; falls back to ``resource`` on Unix.
    Returns ``None`` on platforms where neither is available.
    """
    try:
        import psutil
        return psutil.Process().memory_info().rss
    except ImportError:
        pass
    try:
        import resource
        # resource.getrusage returns KB on Linux, bytes on macOS
        rusage = resource.getrusage(resource.RUSAGE_SELF)
        return rusage.ru_maxrss * 1024  # convert to bytes (Linux)
    except (ImportError, AttributeError):
        pass
    return None


# Data classes

@dataclass
class ShardHealth:
    """RAM and document stats for a single shard."""
    shard_key: str
    total_docs: int
    index_size_bytes: int
    doc_lengths_size_bytes: int
    id_map_size_bytes: int
    total_size_bytes: int

    @property
    def total_size_human(self) -> str:
        return _format_bytes(self.total_size_bytes)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "shard_key": self.shard_key,
            "total_docs": self.total_docs,
            "index_size": _format_bytes(self.index_size_bytes),
            "doc_lengths_size": _format_bytes(self.doc_lengths_size_bytes),
            "id_map_size": _format_bytes(self.id_map_size_bytes),
            "total_size": self.total_size_human,
            "total_size_bytes": self.total_size_bytes,
        }


@dataclass
class HealthReport:
    """Full health snapshot of a Lucis instance."""
    timestamp: str
    index_name: str
    engine_name: str
    is_indexed: bool
    is_sharded: bool
    total_docs: int

    # RAM
    index_ram_bytes: int
    process_rss_bytes: Optional[int]

    # Shards
    shard_count: int
    shards: List[ShardHealth] = field(default_factory=list)

    # Worker
    worker_running: bool = False
    worker_cycles: int = 0
    worker_rebuilds: int = 0
    worker_errors: int = 0
    worker_last_rebuild_time: Optional[float] = None

    # Timing (search benchmark)
    search_benchmark_ms: Optional[float] = None

    @property
    def index_ram_human(self) -> str:
        return _format_bytes(self.index_ram_bytes)

    @property
    def process_rss_human(self) -> Optional[str]:
        return _format_bytes(self.process_rss_bytes) if self.process_rss_bytes else None

    def to_dict(self) -> Dict[str, Any]:
        d = {
            "timestamp": self.timestamp,
            "index_name": self.index_name,
            "engine": self.engine_name,
            "is_indexed": self.is_indexed,
            "is_sharded": self.is_sharded,
            "total_docs": self.total_docs,
            "ram": {
                "index_ram": self.index_ram_human,
                "index_ram_bytes": self.index_ram_bytes,
                "process_rss": self.process_rss_human,
                "process_rss_bytes": self.process_rss_bytes,
            },
            "shards": {
                "count": self.shard_count,
                "detail": [s.to_dict() for s in self.shards],
            },
            "worker": {
                "running": self.worker_running,
                "cycles": self.worker_cycles,
                "rebuilds": self.worker_rebuilds,
                "errors": self.worker_errors,
                "last_rebuild_time_s": self.worker_last_rebuild_time,
            },
        }
        if self.search_benchmark_ms is not None:
            d["search_benchmark_ms"] = round(self.search_benchmark_ms, 2)
        return d

    def __str__(self) -> str:
        lines = [
            "=" * 62,
            "  LUCIS HEALTH REPORT",
            "=" * 62,
            f"  Timestamp     : {self.timestamp}",
            f"  Index         : {self.index_name}",
            f"  Engine        : {self.engine_name}",
            f"  Status        : {'indexed' if self.is_indexed else 'empty'}",
            f"  Total Docs    : {self.total_docs:,}",
            "-" * 62,
            "  RAM",
            f"    Index RAM   : {self.index_ram_human}",
        ]
        if self.process_rss_bytes is not None:
            lines.append(f"    Process RSS : {self.process_rss_human}")
        lines.append("-" * 62)

        if self.is_sharded and self.shards:
            lines.append(f"  SHARDS ({self.shard_count})")
            # Sort by size descending for visibility
            sorted_shards = sorted(
                self.shards, key=lambda s: s.total_size_bytes, reverse=True
            )
            for s in sorted_shards:
                lines.append(
                    f"    {s.shard_key}  |  {s.total_docs:>7,} docs  |  {s.total_size_human:>10}"
                )
            total_shard_ram = sum(s.total_size_bytes for s in self.shards)
            lines.append(f"    {'TOTAL':7s}  |  {self.total_docs:>7,} docs  |  {_format_bytes(total_shard_ram):>10}")
            lines.append("-" * 62)

        lines.append("  WORKER")
        lines.append(f"    Running     : {self.worker_running}")
        if self.worker_running or self.worker_cycles > 0:
            lines.append(f"    Cycles      : {self.worker_cycles}")
            lines.append(f"    Rebuilds    : {self.worker_rebuilds}")
            lines.append(f"    Errors      : {self.worker_errors}")
            if self.worker_last_rebuild_time is not None:
                lines.append(f"    Last Rebuild: {self.worker_last_rebuild_time:.3f}s")

        if self.search_benchmark_ms is not None:
            lines.append("-" * 62)
            lines.append(f"  Search Bench  : {self.search_benchmark_ms:.2f}ms")

        lines.append("=" * 62)
        return "\n".join(lines)


# Core health-check function

def health_check(
    lucis: Any,
    worker: Optional[Any] = None,
    benchmark_query: Optional[str] = None,
) -> HealthReport:
    """Generate a full health report for a Lucis instance.

    Args:
        lucis: A ``Lucis`` instance.
        worker: An optional ``IndexWorker`` to include worker stats.
        benchmark_query: If provided, runs a timed search and includes
            the latency in the report.

    Returns:
        A :class:`HealthReport` with all diagnostics.
    """
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # ── Measure index RAM ──
    index_ram = 0
    shard_details: List[ShardHealth] = []
    shard_count = 0

    if lucis._shard_manager is not None and lucis._shard_manager.shards:
        shard_count = len(lucis._shard_manager.shards)
        for key, engine in lucis._shard_manager.shards.items():
            idx_size = _deep_getsizeof(engine.index) if hasattr(engine, "index") else 0
            dl_size = _deep_getsizeof(engine.doc_lengths) if hasattr(engine, "doc_lengths") else 0
            im_size = _deep_getsizeof(engine.id_map) if hasattr(engine, "id_map") else 0
            total = idx_size + dl_size + im_size
            index_ram += total
            shard_details.append(ShardHealth(
                shard_key=key,
                total_docs=engine.total_docs,
                index_size_bytes=idx_size,
                doc_lengths_size_bytes=dl_size,
                id_map_size_bytes=im_size,
                total_size_bytes=total,
            ))
    elif lucis._is_indexed:
        engine = lucis.engine
        idx_size = _deep_getsizeof(engine.index) if hasattr(engine, "index") else 0
        dl_size = _deep_getsizeof(engine.doc_lengths) if hasattr(engine, "doc_lengths") else 0
        im_size = _deep_getsizeof(engine.id_map) if hasattr(engine, "id_map") else 0
        dv_size = _deep_getsizeof(engine.doc_vectors) if hasattr(engine, "doc_vectors") else 0
        index_ram = idx_size + dl_size + im_size + dv_size

    # Process RSS
    process_rss = _get_process_rss()

    # Worker stats
    w_running = False
    w_cycles = 0
    w_rebuilds = 0
    w_errors = 0
    w_last = None
    if worker is not None:
        w_running = worker.is_running()
        w_cycles = worker.cycles
        w_rebuilds = worker.rebuilds
        w_errors = worker.errors
        w_last = worker.last_rebuild_time

    # Search benchmark
    bench_ms = None
    if benchmark_query and lucis._is_indexed:
        start = time.perf_counter()
        lucis.search(benchmark_query, top_k=5)
        bench_ms = (time.perf_counter() - start) * 1000

    return HealthReport(
        timestamp=now,
        index_name=lucis.name,
        engine_name=lucis.engine.name,
        is_indexed=lucis._is_indexed,
        is_sharded=lucis.is_sharded,
        total_docs=lucis.total_docs,
        index_ram_bytes=index_ram,
        process_rss_bytes=process_rss,
        shard_count=shard_count,
        shards=shard_details,
        worker_running=w_running,
        worker_cycles=w_cycles,
        worker_rebuilds=w_rebuilds,
        worker_errors=w_errors,
        worker_last_rebuild_time=w_last,
        search_benchmark_ms=bench_ms,
    )


# Continuous monitor

class HealthMonitor:
    """Daemon that periodically collects health reports.

    Runs in a background thread and stores a history of
    :class:`HealthReport` snapshots.  Useful for tracking RAM
    growth over time or detecting anomalies in a long-running
    process.

    Args:
        lucis: The ``Lucis`` instance to monitor.
        worker: Optional ``IndexWorker`` for worker stats.
        interval: Seconds between health checks (default 30).
        benchmark_query: Optional query to benchmark every cycle.
        on_report: Optional callback ``fn(HealthReport)`` after each
            collection.
        ram_warning_mb: If index RAM exceeds this (MB), log a warning.
            Default 512 MB.
    """

    def __init__(
        self,
        lucis: Any,
        worker: Optional[Any] = None,
        interval: float = 30,
        benchmark_query: Optional[str] = None,
        on_report: Optional[Any] = None,
        ram_warning_mb: float = 512,
    ):
        self._lucis = lucis
        self._worker = worker
        self._interval = interval
        self._benchmark_query = benchmark_query
        self._on_report = on_report
        self._ram_warning_mb = ram_warning_mb

        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self.history: List[HealthReport] = []

    def start(self) -> None:
        """Start the monitoring loop in a daemon thread."""
        if self._thread is not None and self._thread.is_alive():
            logger.warning("HealthMonitor already running — ignoring start()")
            return
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._loop,
            name=f"lucis-health-{self._lucis.name}",
            daemon=True,
        )
        self._thread.start()
        logger.info(
            "HealthMonitor started for '%s' (interval=%ss)",
            self._lucis.name, self._interval,
        )

    def stop(self) -> None:
        """Signal the monitor to stop and wait for it."""
        if self._thread is None or not self._thread.is_alive():
            return
        self._stop_event.set()
        self._thread.join(timeout=5)
        logger.info("HealthMonitor stopped for '%s'", self._lucis.name)

    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def collect(self) -> HealthReport:
        """Take a single health snapshot now (synchronous)."""
        report = health_check(
            self._lucis,
            worker=self._worker,
            benchmark_query=self._benchmark_query,
        )
        self.history.append(report)
        return report

    def print_summary(self) -> None:
        """Print a summary of all collected reports."""
        if not self.history:
            print("No health reports collected yet.")
            return

        print("\n" + "=" * 62)
        print("  LUCIS HEALTH MONITOR — SUMMARY")
        print(f"  Reports collected: {len(self.history)}")
        print("=" * 62)

        rams = [r.index_ram_bytes for r in self.history]
        print(f"  Index RAM (min) : {_format_bytes(min(rams))}")
        print(f"  Index RAM (max) : {_format_bytes(max(rams))}")
        print(f"  Index RAM (last): {_format_bytes(rams[-1])}")

        rss_vals = [r.process_rss_bytes for r in self.history if r.process_rss_bytes]
        if rss_vals:
            print(f"  Process RSS (min) : {_format_bytes(min(rss_vals))}")
            print(f"  Process RSS (max) : {_format_bytes(max(rss_vals))}")
            print(f"  Process RSS (last): {_format_bytes(rss_vals[-1])}")

        bench_vals = [r.search_benchmark_ms for r in self.history if r.search_benchmark_ms is not None]
        if bench_vals:
            print(f"  Search latency (min) : {min(bench_vals):.2f}ms")
            print(f"  Search latency (max) : {max(bench_vals):.2f}ms")
            print(f"  Search latency (avg) : {sum(bench_vals) / len(bench_vals):.2f}ms")

        print("=" * 62 + "\n")

    def _loop(self) -> None:
        """Background loop: collect → warn → sleep → repeat."""
        while not self._stop_event.is_set():
            try:
                report = self.collect()

                # RAM warning
                ram_mb = report.index_ram_bytes / (1024 ** 2)
                if ram_mb > self._ram_warning_mb:
                    logger.warning(
                        "⚠️  Index RAM (%.1f MB) exceeds threshold (%.0f MB) "
                        "for '%s'",
                        ram_mb, self._ram_warning_mb, self._lucis.name,
                    )

                if self._on_report:
                    try:
                        self._on_report(report)
                    except Exception:
                        pass

            except Exception as exc:
                logger.error("HealthMonitor error: %s", exc)

            # Interruptible sleep
            end_time = time.monotonic() + self._interval
            while time.monotonic() < end_time:
                if self._stop_event.is_set():
                    return
                remaining = end_time - time.monotonic()
                time.sleep(min(0.5, max(0, remaining)))

    def __repr__(self) -> str:
        status = "running" if self.is_running() else "stopped"
        return (
            f"HealthMonitor(index='{self._lucis.name}', "
            f"interval={self._interval}s, status='{status}', "
            f"reports={len(self.history)})"
        )
