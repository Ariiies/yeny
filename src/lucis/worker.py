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

    Args:
        lucis: The ``Lucis`` instance whose index will be managed.
        data_fn: A callable that returns fresh data
            (``Dict[id, text]`` or ``List[text]``). Called each cycle.
        interval: Seconds between rebuild cycles. Default 60.
        change_detector: Optional callable ``() → bool``. When provided,
            the worker only triggers a rebuild if this returns ``True``.
            If ``None``, a rebuild happens every cycle unconditionally.
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
        auto_purge: bool = True,
        keep_versions: int = 3,
        on_rebuild: Optional[Callable[[str], None]] = None,
        on_error: Optional[Callable[[Exception], None]] = None,
        on_cycle: Optional[Callable[[int, bool], None]] = None,
    ):
        self._lucis = lucis
        self._data_fn = data_fn
        self._interval = interval
        self._change_detector = change_detector
        self._auto_purge = auto_purge
        self._keep_versions = keep_versions
        self._on_rebuild = on_rebuild
        self._on_error = on_error
        self._on_cycle = on_cycle

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

        The worker will immediately begin its first cycle. Calling
        ``start()`` on an already-running worker is a no-op with a
        warning.
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
        """Return ``True`` if the worker thread is alive."""
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
        """Return a snapshot of worker statistics."""
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
        """Fetch data, rebuild index, swap alias, purge."""
        start = time.perf_counter()

        data = self._data_fn()

        # Use the synchronous reindex (builds + saves + swaps alias)
        self._lucis.reindex(data)

        elapsed = time.perf_counter() - start
        self.last_rebuild_time = round(elapsed, 3)
        self.rebuilds += 1

        # Grab the current physical name for the callback
        physical_name = self._lucis.storage.get_alias(self._lucis.name) or "unknown"

        logger.info(
            "Rebuild %d complete in %.3fs → %s",
            self.rebuilds,
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
        """Sleep for *seconds*, waking early if ``_stop_event`` is set."""
        end_time = time.monotonic() + seconds
        while time.monotonic() < end_time:
            if self._stop_event.is_set():
                return
            # Check every 0.25s for stop signal
            remaining = end_time - time.monotonic()
            time.sleep(min(0.25, max(0, remaining)))

    def __repr__(self) -> str:
        status = "running" if self.is_running() else "stopped"
        return (
            f"IndexWorker(index='{self._lucis.name}', "
            f"interval={self._interval}s, status='{status}', "
            f"cycles={self.cycles}, rebuilds={self.rebuilds})"
        )
