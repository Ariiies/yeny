"""
IndexWorker — automated background index rebuilder.

Monitors a data source and periodically rebuilds the index when
changes are detected, with zero downtime for search operations.

This is the Phase 4 component of the Shadow Indexing system.

Example — periodic rebuild every 60 seconds::

    from lucis import Lucis, IndexWorker

    luc = Lucis.from_dict(data, name="articles", storage_type="sqlite", db_path="app.db")

    def fetch_fresh_data():
        return storage.read_table("articles", text_column="content", id_column="id")

    worker = IndexWorker(
        lucis=luc,
        data_fn=fetch_fresh_data,
        interval=60,
        auto_purge=True,
        keep_versions=3,
    )
    worker.start()

    # ... app runs, search stays fast ...

    worker.stop()  # graceful shutdown

Example — change-detection mode::

    def has_new_data():
        return db.execute("SELECT MAX(updated_at) FROM articles").fetchone()[0] > last_check

    worker = IndexWorker(
        lucis=luc,
        data_fn=fetch_fresh_data,
        interval=30,
        change_detector=has_new_data,  # only rebuild when True
    )
    worker.start()
"""
from __future__ import annotations

import logging
import threading
import time
from typing import Any, Callable, Dict, List, Optional, Union

logger = logging.getLogger("lucis.worker")


class IndexWorker:
    """
    Daemon that periodically rebuilds a Lucis index in the background.

    The worker runs a loop: sleep → check for changes → rebuild → swap.
    During the entire rebuild cycle, the live index continues to serve
    search requests with zero downtime.

    Supports two modes of operation:

    **Full rebuild (default):**
        Fetches the entire corpus via ``data_fn`` and calls
        ``lucis.reindex(data)``.  Best for ``CoreEngine`` or when
        the full dataset is small.

    **Incremental update** (``incremental=True``):
        Fetches only new documents via ``delta_fn`` and calls
        ``lucis.add_documents(delta)``.  Best for ``LiteEngine``
        where existing scores are not invalidated by new documents.
        Falls back to full rebuild via ``data_fn`` if ``delta_fn``
        is not provided.

    Args:
        lucis: The ``Lucis`` instance whose index will be managed.
        data_fn: A callable that returns fresh data
            (``Dict[id, text]`` or ``List[text]``). Called each cycle
            for full rebuilds.
        interval: Seconds between rebuild cycles. Default 60.
        change_detector: Optional callable ``() → bool``. When provided,
            the worker only triggers a rebuild if this returns ``True``.
            If ``None``, a rebuild happens every cycle unconditionally.
        incremental: If ``True``, the worker uses ``delta_fn`` to fetch
            only new documents and calls ``add_documents()`` instead
            of a full ``reindex()``. Default ``False``.
        delta_fn: Callable that returns only the **new** documents
            since the last cycle. Required when ``incremental=True``
            unless you want to fall back to ``data_fn`` + full rebuild.
        auto_purge: If ``True``, old versions are automatically cleaned
            up after each successful rebuild. Default ``True``.
        keep_versions: Number of versions to retain when purging.
            Default 3.
        on_rebuild: Callback ``fn(physical_name)`` after a successful
            rebuild.
        on_error: Callback ``fn(exception)`` when a rebuild fails.
            The worker does **not** stop on errors — it logs them and
            retries on the next cycle.
        on_cycle: Callback ``fn(cycle_number, skipped)`` at the end
            of every cycle. ``skipped`` is ``True`` if the change
            detector said no rebuild was needed.

    Attributes:
        cycles: Total number of cycles completed.
        rebuilds: Total number of successful rebuilds.
        errors: Total number of failed rebuilds.
        last_rebuild_time: Wall-clock seconds of the last rebuild, or ``None``.
    """

    def __init__(
        self,
        lucis: Any,  # Lucis — avoid circular import
        data_fn: Callable[[], Union[List[str], Dict[Any, str]]],
        interval: float = 60,
        change_detector: Optional[Callable[[], bool]] = None,
        incremental: bool = False,
        delta_fn: Optional[Callable[[], Union[List[str], Dict[Any, str]]]] = None,
        auto_purge: bool = True,
        keep_versions: int = 3,
        on_rebuild: Optional[Callable[[str], None]] = None,
        on_error: Optional[Callable[[Exception], None]] = None,
        on_cycle: Optional[Callable[[int, bool], None]] = None,
        streaming_fn: Optional[Callable] = None,
    ):
        self._lucis = lucis
        self._data_fn = data_fn
        self._interval = interval
        self._change_detector = change_detector
        self._incremental = incremental
        self._delta_fn = delta_fn
        self._auto_purge = auto_purge
        self._keep_versions = keep_versions
        self._on_rebuild = on_rebuild
        self._on_error = on_error
        self._on_cycle = on_cycle
        # streaming_fn: no-arg callable that returns a (doc_id, text, date)
        # iterator.  When set, full rebuilds use reindex_streaming() instead
        # of fetching all rows into memory via data_fn().
        self._streaming_fn = streaming_fn

        # Internal state
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

        # Public counters
        self.cycles: int = 0
        self.rebuilds: int = 0
        self.errors: int = 0
        self.last_rebuild_time: Optional[float] = None

    # Public API

    def start(self) -> None:
        """
        Start the worker loop in a daemon thread.

        The worker will immediately begin its first cycle.  Calling
        ``start()`` on an already-running worker is a no-op (a warning
        is logged).

        Raises:
            RuntimeError: Not raised directly, but if the underlying
                thread cannot be started the Python runtime will propagate
                the error.
        """
        if self.is_running():
            logger.warning("IndexWorker is already running — ignoring start()")
            return

        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._loop,
            name=f"lucis-worker-{self._lucis.name}",
            daemon=True,
        )
        self._thread.start()
        logger.info(
            "IndexWorker started for '%s' (interval=%ss)",
            self._lucis.name,
            self._interval,
        )

    def stop(self, timeout: Optional[float] = None) -> None:
        """
        Signal the worker to stop and wait for it to finish.

        The current cycle (if any) will complete before the thread
        exits. This method blocks until the thread has joined or
        *timeout* seconds have elapsed.

        Args:
            timeout: Max seconds to wait for the thread to exit.
                ``None`` waits forever.
        """
        if not self.is_running():
            return

        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=timeout)
        logger.info("IndexWorker stopped for '%s'", self._lucis.name)

    def is_running(self) -> bool:
        """Return ``True`` if the worker thread is currently alive.

        Returns:
            ``True`` while the daemon thread is running, ``False``
            after :meth:`stop` completes or before :meth:`start` is
            called.
        """
        return self._thread is not None and self._thread.is_alive()

    def trigger_now(self) -> None:
        """
        Force an immediate rebuild outside the normal schedule.

        Runs synchronously in the calling thread — useful for testing
        or manual refreshes.

        Raises:
            Exception: Whatever the data function or rebuild raises.
        """
        self._do_rebuild()

    @property
    def stats(self) -> Dict[str, Any]:
        """Return a snapshot of worker statistics.

        Returns:
            Dict with keys ``running``, ``interval``, ``cycles``,
            ``rebuilds``, ``errors``, ``last_rebuild_time``,
            ``index_name``, ``auto_purge``, and ``keep_versions``.
        """
        return {
            "running": self.is_running(),
            "interval": self._interval,
            "cycles": self.cycles,
            "rebuilds": self.rebuilds,
            "errors": self.errors,
            "last_rebuild_time": self.last_rebuild_time,
            "index_name": self._lucis.name,
            "auto_purge": self._auto_purge,
            "keep_versions": self._keep_versions,
        }

    # Internal

    def _loop(self) -> None:
        """Main loop: sleep → check → rebuild → purge → repeat."""
        while not self._stop_event.is_set():
            skipped = False

            try:
                # Check if rebuild is needed
                if self._change_detector is not None:
                    try:
                        needs_rebuild = self._change_detector()
                    except Exception as exc:
                        logger.error(
                            "Change detector raised: %s — skipping cycle", exc
                        )
                        needs_rebuild = False
                else:
                    needs_rebuild = True

                if needs_rebuild:
                    self._do_rebuild()
                else:
                    skipped = True
                    logger.debug(
                        "Cycle %d: no changes detected — skipping rebuild",
                        self.cycles + 1,
                    )

            except Exception as exc:
                self.errors += 1
                logger.error(
                    "Rebuild failed (cycle %d): %s", self.cycles + 1, exc
                )
                if self._on_error:
                    try:
                        self._on_error(exc)
                    except Exception:
                        pass  # never let callback errors kill the worker

            finally:
                self.cycles += 1
                if self._on_cycle:
                    try:
                        self._on_cycle(self.cycles, skipped)
                    except Exception:
                        pass

            # Interruptible sleep — checks every 0.25s if stop was requested
            self._interruptible_sleep(self._interval)

    def _do_rebuild(self) -> None:
        """Fetch data, rebuild or incrementally update index, swap alias, purge.

        When the data/delta functions return ``(data, dates)`` tuples
        (sharded mode), the dates are forwarded to Lucis for shard routing.
        """
        start = time.perf_counter()

        if self._incremental and self._delta_fn is not None:
            # Incremental mode: fetch only new documents and add them
            result = self._delta_fn()

            # Detect sharded mode: delta_fn returns (data, dates)
            if isinstance(result, tuple) and len(result) == 2:
                delta, dates = result
                if not delta:
                    logger.debug("Incremental update: no new documents — skipping")
                    return
                self._lucis.add_documents(delta, dates=dates)
            else:
                delta = result
                if not delta:
                    logger.debug("Incremental update: no new documents — skipping")
                    return
                self._lucis.add_documents(delta)
        else:
            # Full rebuild mode (default)
            # ── Streaming path: server-side cursor, no fetchall ──
            if self._streaming_fn is not None and hasattr(self._lucis, "reindex_streaming"):
                self._lucis.reindex_streaming(self._streaming_fn())
            else:
                # Classic path: data_fn() returns full dict/list in RAM
                result = self._data_fn()

                # Detect sharded mode: data_fn returns (data, dates)
                if isinstance(result, tuple) and len(result) == 2:
                    data, dates = result
                    self._lucis.reindex(data, dates=dates)
                else:
                    self._lucis.reindex(result)

        elapsed = time.perf_counter() - start
        self.last_rebuild_time = round(elapsed, 3)
        self.rebuilds += 1

        # Commit deferred state only after successful rebuild
        if hasattr(self._change_detector, "commit"):
            self._change_detector.commit()
        if self._delta_fn is not None and hasattr(self._delta_fn, "commit"):
            self._delta_fn.commit()

        # Grab the current physical name for the callback
        physical_name = self._lucis.storage.get_alias(self._lucis.name) or "unknown"

        mode = "incremental" if (self._incremental and self._delta_fn) else "full"
        logger.info(
            "Rebuild %d (%s) complete in %.3fs → %s",
            self.rebuilds,
            mode,
            elapsed,
            physical_name,
        )

        if self._on_rebuild:
            try:
                self._on_rebuild(physical_name)
            except Exception:
                pass

        # Auto-cleanup
        if self._auto_purge:
            try:
                deleted = self._lucis.purge_old_versions(keep=self._keep_versions)
                if deleted > 0:
                    logger.info("Purged %d old version(s)", deleted)
            except Exception as exc:
                logger.warning("Auto-purge failed: %s", exc)

    def _interruptible_sleep(self, seconds: float) -> None:
        """Sleep for *seconds*, returning early if ``_stop_event`` is set.

        Args:
            seconds: Total sleep duration in seconds.
        """
        end_time = time.monotonic() + seconds
        while time.monotonic() < end_time:
            if self._stop_event.is_set():
                return
            # Check every 0.25s for stop signal
            remaining = end_time - time.monotonic()
            time.sleep(min(0.25, max(0, remaining)))

    def __repr__(self) -> str:
        """Return an informative string representation of the worker."""
        status = "running" if self.is_running() else "stopped"
        mode = "incremental" if self._incremental else ("streaming" if self._streaming_fn else "full-rebuild")
        return (
            f"IndexWorker(index='{self._lucis.name}', "
            f"mode='{mode}', interval={self._interval}s, "
            f"status='{status}', cycles={self.cycles}, rebuilds={self.rebuilds})"
        )
