"""
AutomationMixin — Indexing, incremental updates, worker creation,
health monitoring, and source connection.

Provides the operational methods that modify the index (``index``,
``reindex``, ``add_documents``, ``remove_documents``), the background
rebuild facility (``reindex_async``), the ``IndexWorker`` factory
(``create_worker``), and health diagnostics.
"""
import threading
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional, Union

from ..exceptions import YenyEngineError
from ..sync.source_spec import SourceSpec
from ..sync.data_providers import build_data_fn, build_streaming_fn
from ..sync.delta_providers import build_delta_fn
from ..sync.change_detectors import build_change_detector
from ..core.health import health_check as _health_check, HealthMonitor
from .._internals import _get_database_reader_class, _ENGINE_REGISTRY

if TYPE_CHECKING:
    from ..core.worker import IndexWorker


class AutomationMixin:
    """Mixin that provides indexing, sync automation, and health monitoring."""

    # ── Core ingestion ──

    def index(self, data: Union[List[str], Dict[Any, str]], persist: bool = True) -> None:
        """
        The "all-terrain" ingestion method.
        
        Detects whether data is a Dict or List and delegates to the engine.
        This is the single entry point for all data ingestion — the engine's
        _normalize_corpus handles the rest.

        Args:
            data: Either a Dict[id, text] or List[text] to index.
            persist: Whether to save the index to storage after building.
        """
        self.engine.build_index(data)
        self._is_indexed = True
        if persist:
            self.save()

    # ── Shadow Rebuild ──

    def reindex(
        self,
        data: Union[List[str], Dict[Any, str]],
        dates: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Rebuild the index with fresh data, creating a new version.

        The previous version remains in storage so you can ``rollback()``
        if needed.  The alias is swapped atomically to the new version.

        When the index is sharded and *dates* is provided, documents are
        re-routed to their correct temporal shards.

        Args:
            data: New corpus — ``Dict[id, text]`` or ``List[text]``.
            dates: Optional ``{doc_id: date_value}`` for shard routing.
                Required for sharded indices; ignored otherwise.

        Example::

            new_data = storage.read_table("articles", text_column="content", id_column="id")
            yn.reindex(new_data)
            # → alias now points to the new version
        """
        if self._shard_manager and dates is not None:
            self._shard_manager.shards.clear()
            self._shard_manager.build_shards(data, dates)
        else:
            self.engine.build_index(data)
        self._is_indexed = True
        self.save()
        # Reload from storage to shed build-time RAM overhead
        if self._shard_manager:
            self._post_index_cleanup(self.name)

    def reindex_streaming(
        self,
        row_iter,
        batch_size: int = 5_000,
    ) -> None:
        """Rebuild the sharded index from a **streaming** row iterator.

        This is the memory-efficient counterpart to :meth:`reindex`.
        Instead of materialising the entire corpus in RAM (via
        ``fetchall``), rows are consumed in *batch_size* chunks and
        routed directly to their temporal shards.

        Peak RAM during rebuild ≈ steady-state index RAM + one batch
        (a few MB), instead of steady-state + full raw corpus (~1 GB
        extra for a 2 M-row email dataset).

        Args:
            row_iter: Any iterable that yields ``(doc_id_str, text, date_val)``
                triples.  Typical source:
                ``storage.stream_table_with_dates(...)``.
            batch_size: Per-shard buffer size.  Default 5 000 rows.

        Raises:
            YenyEngineError: If the index is not sharded (no
                ``_shard_manager``).  Use :meth:`reindex` for
                non-sharded indices.

        Example::

            row_iter = storage.stream_table_with_dates(
                "emails", "body", id_column="id", date_column="sent_at"
            )
            yn.reindex_streaming(row_iter)
        """
        if self._shard_manager is None:
            raise YenyEngineError(
                engine_name=self.engine.name,
                detail=(
                    "reindex_streaming() requires a sharded index. "
                    "Use reindex() for non-sharded indices."
                ),
            )
        self._shard_manager.build_shards_streaming(row_iter, batch_size=batch_size)
        self._is_indexed = True
        self.save()
        # Reload from storage to shed build-time RAM overhead
        self._post_index_cleanup(self.name)

    # ── Incremental updates ──

    def add_documents(
        self,
        new_docs: Union[List[str], Dict[Any, str]],
        dates: Optional[Dict[str, Any]] = None,
        persist: bool = True,
    ) -> None:
        """
        Incrementally add new documents to the current index.

        When the index is sharded, new documents are routed to the
        correct shard based on *dates*.

        Args:
            new_docs: New documents — ``Dict[id, text]`` or ``List[text]``.
            dates: Optional ``{doc_id: date_value}`` for shard routing.
            persist: Whether to save the updated index to storage.

        Raises:
            YenyEngineError: If the engine does not support incremental
                indexing and index is not sharded.

        Example::

            yn.add_documents({"new_doc": "some text"})
            yn.add_documents(["another document"])
        """
        if self._shard_manager and dates is not None:
            self._shard_manager.add_documents(new_docs, dates)
        elif hasattr(self.engine, "add_documents"):
            self.engine.add_documents(new_docs)
        else:
            raise YenyEngineError(
                engine_name=self.engine.name,
                detail=(
                    f"'{self.engine.name}' does not support incremental indexing. "
                    "Use reindex() for a full rebuild, or switch to engine='lite'."
                ),
            )

        self._is_indexed = True
        if persist:
            self.save()
            # Reload from mmap to shed the materialized in-memory dicts
            # created by _ensure_mutable(). Same cleanup path used by
            # from_table() and reindex().
            if self._shard_manager is not None:
                self._post_index_cleanup(self.name)

    def remove_documents(
        self,
        doc_ids: List[Any],
        persist: bool = True,
        fallback_rebuild: bool = True,
    ) -> int:
        """Remove documents by original IDs.

        Preferred path (LiteEngine): in-place removal from postings.
        Universal fallback: full rebuild from source metadata.

        Args:
            doc_ids: Original document IDs to remove.
            persist: Whether to save after removal.
            fallback_rebuild: If in-place removal is unavailable,
                run a full rebuild from source metadata.

        Returns:
            Number of removed documents (best-effort count).
        """
        if not doc_ids:
            return 0

        removed = 0

        if self._shard_manager is not None and hasattr(self._shard_manager, "remove_documents"):
            removed = self._shard_manager.remove_documents(doc_ids)
        elif hasattr(self.engine, "remove_documents"):
            removed = self.engine.remove_documents(doc_ids)
        elif fallback_rebuild:
            self._rebuild_from_source_info()
            return len(doc_ids)
        else:
            raise YenyEngineError(
                engine_name=self.engine.name,
                detail=(
                    f"'{self.engine.name}' does not support in-place remove_documents(). "
                    "Enable fallback_rebuild=True or call reindex() manually."
                ),
            )

        if removed <= 0:
            return 0

        self._is_indexed = True
        if persist:
            self.save()
            if self._shard_manager is not None:
                self._post_index_cleanup(self.name)

        return removed

    def _rebuild_from_source_info(self) -> None:
        """Run a full rebuild using auto-generated source metadata readers."""
        if self._source_info is None:
            raise YenyEngineError(
                engine_name=self.engine.name,
                detail=(
                    "Cannot auto-rebuild: source metadata is missing. "
                    "Provide data manually via reindex(data, dates=...)."
                ),
            )

        data_fn = build_data_fn(
            self._source_info, self._reader, self.storage, self.engine.name
        )

        result = data_fn()
        if isinstance(result, tuple) and len(result) == 2:
            data, dates = result
            self.reindex(data, dates=dates)
        else:
            self.reindex(result)

    # ── Background Rebuild (Phase 3) ──

    def reindex_async(
        self,
        data: Union[List[str], Dict[Any, str]],
        on_complete: Optional[Callable[[str], None]] = None,
        on_error: Optional[Callable[[Exception], None]] = None,
        auto_swap: bool = True,
    ) -> None:
        """
        Rebuild the index in a background thread.

        While the rebuild is running, ``search()`` continues to use the
        current (active) engine with **zero downtime**.  When the new
        index is ready it is persisted, the alias is swapped, and
        (optionally) the live engine is replaced atomically.

        Args:
            data: New corpus — ``Dict[id, text]`` or ``List[text]``.
            on_complete: Callback ``fn(physical_name)`` invoked when the
                rebuild finishes successfully.
            on_error: Callback ``fn(exception)`` invoked if the rebuild fails.
            auto_swap: If ``True`` (default), the live engine is
                swapped to the new version automatically.  If ``False``,
                the alias is updated but you must call ``load()`` yourself
                to pick up the new version.

        Raises:
            YenyEngineError: If a rebuild is already in progress.

        Example::

            yn.reindex_async(new_data)

            while yn.is_rebuilding():
                results = yn.search("query")   # ← uses active index
                time.sleep(0.5)

            yn.wait_for_reindex()               # ← ensures completion
            results = yn.search("query")        # ← uses new index
        """
        if self.is_rebuilding():
            raise YenyEngineError(
                engine_name=self.engine.name,
                detail="A background rebuild is already in progress. "
                       "Call wait_for_reindex() before starting another.",
            )

        self._rebuild_error = None

        # Capture references for the worker closure
        engine_class = type(self.engine)
        storage = self.storage
        index_name = self.name
        preprocessor = self.preprocessor

        def _worker() -> None:
            try:
                # 1. Build in an isolated engine (no impact on live searches)
                shadow_engine = engine_class(storage=storage, preprocessor=preprocessor)
                shadow_engine.build_index(data)

                # 2. Persist with a new versioned name + swap alias
                physical_name = storage._generate_versioned_name(index_name)
                shadow_engine.persist(physical_name)
                storage.set_alias(index_name, physical_name)

                # 3. Hot-swap the live engine (GIL makes reference swap atomic)
                if auto_swap:
                    self.engine = shadow_engine
                    self._is_indexed = True

                if on_complete:
                    on_complete(physical_name)

            except Exception as exc:
                self._rebuild_error = exc
                if on_error:
                    on_error(exc)

        self._rebuild_thread = threading.Thread(
            target=_worker,
            name=f"yeny-reindex-{index_name}",
            daemon=True,
        )
        self._rebuild_thread.start()

    def is_rebuilding(self) -> bool:
        """Return ``True`` if a background rebuild is currently in progress.

        Returns:
            ``True`` while the rebuild thread started by
            :meth:`reindex_async` is alive.

        Example::

            if yn.is_rebuilding():
                print("Rebuild in progress…")
        """
        return (
            self._rebuild_thread is not None
            and self._rebuild_thread.is_alive()
        )

    def wait_for_reindex(self, timeout: Optional[float] = None) -> None:
        """
        Block until the background rebuild finishes.

        If the rebuild raised an exception, it is re-raised here so the
        caller can handle it.

        Args:
            timeout: Maximum seconds to wait.  ``None`` means wait
                indefinitely.

        Raises:
            YenyEngineError: If no rebuild has been started.
            Exception: Re-raises the original error from the worker thread.

        Example::

            yn.reindex_async(new_data)
            yn.wait_for_reindex(timeout=30)
            print("Rebuild done!")
        """
        if self._rebuild_thread is None:
            raise YenyEngineError(
                engine_name=self.engine.name,
                detail="No background rebuild to wait for.",
            )

        self._rebuild_thread.join(timeout=timeout)

        if self._rebuild_error is not None:
            raise self._rebuild_error

    # ── Worker / Automation (Phase 4) ──

    def create_worker(
        self,
        data_fn: Optional[Callable[[], Union[List[str], Dict[Any, str]]]] = None,
        interval: float = 60,
        change_detector: Optional[Callable[[], bool]] = None,
        incremental: Optional[bool] = None,
        delta_fn: Optional[Callable[[], Union[List[str], Dict[Any, str]]]] = None,
        auto_purge: bool = True,
        keep_versions: int = 2,
        on_rebuild: Optional[Callable[[str], None]] = None,
        on_error: Optional[Callable[[Exception], None]] = None,
        on_cycle: Optional[Callable[[int, bool], None]] = None,
        streaming: bool = True,
        connection_url: Optional[str] = None,
    ) -> "IndexWorker":
        """
        Create an ``IndexWorker`` bound to this Yeny instance.

        The worker runs a daemon loop that periodically fetches fresh
        data, rebuilds the index, swaps the alias, and (optionally)
        purges old versions — all with **zero downtime** for searches.

        If the index was created from a database table/query (via
        ``from_table``, ``from_sqlite_table``, etc.), both
        ``data_fn`` and ``change_detector`` are **auto-generated**
        when not provided — the worker just works out of the box.

        **Incremental mode** (LiteEngine):
        When ``incremental=True`` (or auto-detected), the worker uses
        ``delta_fn`` instead of ``data_fn`` to fetch only new rows and
        calls ``add_documents()`` instead of ``reindex()``.  This is
        significantly faster for append-heavy workloads.

        **Full rebuild mode** (CoreEngine):
        When ``incremental=False`` (or auto-detected for CoreEngine),
        the worker calls ``reindex()`` each cycle.  This ensures IDF
        scores stay accurate at the cost of a full rebuild.

        If ``incremental`` is not specified:
        - Auto-enabled when engine name is ``"lite"`` (exact incremental).
        - Falls back to full rebuild for ``"core"`` (IDF drift with
          incremental → prefer full rebuild).

        Args:
            data_fn: Callable that returns fresh data each cycle.
                If ``None``, auto-generated from source metadata.
            interval: Seconds between cycles (default 60).
            change_detector: Optional ``() → bool``.  When provided,
                the rebuild only runs if this returns ``True``.
                If ``None`` and source is a table, auto-generated
                using ``COUNT(*)`` comparison.
            incremental: Enable incremental mode.  ``None`` = auto-detect.
            delta_fn: Callable returning only *new* documents since last
                call.  Auto-generated for table sources with id_column.
            auto_purge: Automatically clean old versions (default True).
            keep_versions: Versions to retain when purging (default 2).
            on_rebuild: Callback ``fn(physical_name)`` on success.
            on_error: Callback ``fn(exception)`` on failure.
            on_cycle: Callback ``fn(cycle_number, skipped)`` every cycle.
            streaming: Enable streaming full-rebuild mode (default ``True``).
                When ``True`` and the source is a sharded database table, the
                worker calls :meth:`reindex_streaming` instead of loading the
                entire corpus into RAM via ``data_fn``.  This keeps peak RAM
                at ≈ steady-state index RAM rather than doubling it during each
                rebuild cycle.  Set to ``False`` to force the classic
                ``fetchall`` path.
            connection_url: Connection URL for the source database.
                When provided, calls :meth:`connect_source` internally so the
                worker can auto-generate ``data_fn`` / ``delta_fn`` from the
                source.  This avoids a separate ``connect_source()`` call.

        Returns:
            An ``IndexWorker`` instance (not yet started).
            Call ``.start()`` to begin the loop.

        Example — zero config (auto data_fn + auto incremental)::

            from yeny.config import TableSource

            source = TableSource(
                table="articles",
                connection_url=URL,
                text_columns="content",
                id_column="article_id",
            )
            yn = Yeny.from_table(
                source, name="articles_idx", engine="lite"
            )
            worker = yn.create_worker(interval=60)
            worker.start()

        Example — reload with a connection URL (auto-discovery)::

            yn = Yeny(name="articles_idx", engine="lite")
            worker = yn.create_worker(interval=60, connection_url=URL)
            worker.start()

        Example — explicit incremental with custom delta_fn::

            worker = yn.create_worker(
                incremental=True,
                delta_fn=my_delta_fetcher,
                interval=30,
            )
            worker.start()

        Example — full rebuild (default for CoreEngine)::

            worker = yn.create_worker(data_fn=my_fetch, interval=30)
            worker.start()
        """
        # Connect to source DB if URL provided
        if connection_url is not None:
            self.connect_source(connection_url)

        # Auto-detect incremental mode based on engine scoring model:
        # LiteEngine (registry key "lite"): TF scoring, exact incremental — no precision loss
        # CoreEngine (registry key "core"): TF-IDF cosine, IDF drifts with incremental → full rebuild
        if incremental is None:
            incremental = isinstance(self.engine, _ENGINE_REGISTRY["lite"])

        # Auto-generate delta_fn for incremental mode (via sync layer)
        if incremental and delta_fn is None:
            delta_fn = build_delta_fn(
                self._source_info,
                self._reader,
                self.storage,
                self._shard_manager,
                self.engine,
            )
            if delta_fn is None:
                # No source info at all — cannot auto-generate
                import logging
                logging.getLogger("yeny.worker").warning(
                    "Cannot auto-generate delta_fn for incremental mode; "
                    "falling back to full rebuild."
                )
                incremental = False

        # Auto-generate data_fn (always needed as fallback)
        if data_fn is None:
            if self._source_info is None:
                if not incremental:
                    raise YenyEngineError(
                        engine_name=self.engine.name,
                        detail=(
                            "Cannot auto-generate data_fn: no source info available. "
                            "Either create the index with from_table / "
                            "from_sqlite_table, or provide data_fn explicitly."
                        ),
                    )
                # Incremental-only: data_fn not strictly needed,
                # but we still create a no-op for the worker signature.
                data_fn = lambda: {}
            else:
                data_fn = build_data_fn(
                    self._source_info, self._reader,
                    self.storage, self.engine.name,
                )

        # Auto-generate change_detector if not provided (via sync layer)
        if change_detector is None and self._source_info is not None:
            change_detector = build_change_detector(
                self._source_info,
                self._reader,
                self.storage,
                self._shard_manager,
                self.engine,
                self._is_indexed,
            )

        # Auto-generate streaming_fn for sharded+alchemy full-rebuild mode.
        # When available, the worker streams rows from the DB without fetchall,
        # keeping peak RAM ≈ steady-state index RAM instead of doubling it.
        streaming_fn: Optional[Callable] = None
        if streaming and not incremental:
            streaming_fn = build_streaming_fn(
                self._source_info, self._reader, self.storage,
            )

        from ..core.worker import IndexWorker
        return IndexWorker(
            yeny=self,
            data_fn=data_fn,
            interval=interval,
            change_detector=change_detector,
            incremental=incremental,
            delta_fn=delta_fn,
            auto_purge=auto_purge,
            keep_versions=keep_versions,
            on_rebuild=on_rebuild,
            on_error=on_error,
            on_cycle=on_cycle,
            streaming_fn=streaming_fn,
        )

    # ── Health monitoring ──

    def health_check(
        self,
        worker: Optional[Any] = None,
        benchmark_query: Optional[str] = None,
    ) -> Any:
        """
        Generate a full health report: RAM usage, shard sizes, worker
        status, and optional search benchmark.

        Args:
            worker: An ``IndexWorker`` to include in the report (optional).
            benchmark_query: If provided, runs a timed search and includes
                the latency in the report.

        Returns:
            A :class:`HealthReport` with all diagnostics.

        Example::

            report = yn.health_check(worker=worker, benchmark_query="test")
            print(report)          # pretty table
            print(report.to_dict())  # JSON-ready dict
        """
        return _health_check(self, worker=worker, benchmark_query=benchmark_query)

    def health_monitor(
        self,
        worker: Optional[Any] = None,
        interval: float = 30,
        benchmark_query: Optional[str] = None,
        on_report: Optional[Any] = None,
        ram_warning_mb: float = 512,
    ) -> "HealthMonitor":
        """
        Create a continuous health monitor that collects periodic snapshots.

        The monitor runs in a daemon thread and stores a history of
        :class:`HealthReport` objects for trend analysis.

        Args:
            worker: An ``IndexWorker`` to include in reports.
            interval: Seconds between snapshots (default 30).
            benchmark_query: If provided, benchmarks search each cycle.
            on_report: Optional callback ``fn(HealthReport)`` per cycle.
            ram_warning_mb: Log a warning if index RAM exceeds this
                threshold (default 512 MB).

        Returns:
            A :class:`HealthMonitor` instance (not yet started).
            Call ``.start()`` to begin monitoring.

        Example::

            monitor = yn.health_monitor(worker=worker, interval=30)
            monitor.start()
            # ... app runs ...
            monitor.stop()
            monitor.print_summary()
        """
        return HealthMonitor(
            yeny=self,
            worker=worker,
            interval=interval,
            benchmark_query=benchmark_query,
            on_report=on_report,
            ram_warning_mb=ram_warning_mb,
        )

    # ── Lifecycle Management ──

    def connect_source(self, connection_url: str) -> None:
        """Attach a :class:`DatabaseReader` so the worker can sync with
        the production database.

        This is the **only** step needed after a simple autoload reload::

            yn = Yeny(name="my_idx", engine="lite")
            yn.connect_source(
                connection_url="mysql+pymysql://user:pass@host/db"
            )
            worker = yn.create_worker(interval=60)

        The URL is intentionally **not** persisted (security) — so the
        caller must supply it each time the worker is needed.

        Args:
            connection_url: Connection URL for the source database.
        """
        DatabaseReader = _get_database_reader_class()
        if self._reader is not None:
            close_fn = getattr(self._reader, "close", None)
            if close_fn is not None:
                close_fn()
        self._reader = DatabaseReader(connection_url=connection_url)
