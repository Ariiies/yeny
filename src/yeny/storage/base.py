from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class BaseStorage(ABC):
    """
    Universal interface for all storage backends.

    Concrete backends (JSON, SQLite, SQLAlchemy) must implement the three
    abstract methods: :meth:`save`, :meth:`load`, and :meth:`exists`.
    Optional methods (alias management, versioning, shard registry) have
    safe no-op defaults so lightweight backends work without changes.
    """
    
    @abstractmethod
    def save(self, engine_state: Dict[str, Any], name: str) -> None:
        """Serialize and persist the engine state under *name*.

        Args:
            engine_state: The dict produced by an engine's ``persist()``
                method.  Contains keys such as *index*, *doc_lengths*,
                *id_map*, *total_docs*, and *id_type*.
            name: Physical storage key (e.g. a file name without extension
                or a database index name).

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        pass

    @abstractmethod
    def load(self, name: str) -> Dict[str, Any]:
        """Deserialize and return the engine state for *name*.

        Args:
            name: Physical storage key previously used with :meth:`save`.
                Aliases are resolved by the caller before this method is
                invoked.

        Returns:
            The engine-state dict (same shape accepted by
            ``BaseEngine.load_engine``).

        Raises:
            FileNotFoundError: If *name* does not exist in this backend.
            NotImplementedError: If not implemented by the subclass.
        """
        pass

    @abstractmethod
    def exists(self, name: str) -> bool:
        """Return ``True`` if *name* is persisted in this storage.

        Implementations should resolve aliases internally so that a
        logical name returns ``True`` as long as its physical target
        exists.

        Args:
            name: Logical or physical index name to check.

        Returns:
            ``True`` if the index (or its alias target) exists.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        pass

    # Alias / versioning support (opt-in)
    # These methods have concrete defaults so that simple backends
    # (e.g. JSONStorage) work without changes.  Database-backed
    # storages override them to enable shadow-index swap.

    def resolve_alias(self, name: str) -> str:
        """Resolve *name* to a physical index name.

        If *name* is a registered alias, return the target it points to.
        Otherwise return *name* unchanged (passthrough).  Simple backends
        that do not support aliases always return *name* as-is.

        Args:
            name: Logical alias or physical index name.

        Returns:
            The physical index name the alias points to, or *name* if
            it is not an alias.
        """
        return name

    def set_alias(self, alias_name: str, target_index: str) -> None:
        """Create or update an alias so it points to *target_index*.

        The operation is idempotent: subsequent calls overwrite the
        previous mapping.  Backends without alias support silently
        ignore this call.

        Args:
            alias_name: Logical name that users and Yeny use to
                reference the index.
            target_index: Physical versioned name the alias should
                point to (e.g. ``"articles__v20260210_143022"``).
        """
        pass  # no-op for backends without alias support

    def get_alias(self, alias_name: str) -> Optional[str]:
        """Return the physical target index for *alias_name*.

        Args:
            alias_name: The logical alias to look up.

        Returns:
            The physical index name the alias points to, or ``None``
            if *alias_name* is not a registered alias.
        """
        return None

    def list_versions(self, base_name: str) -> list:
        """Return all physical index versions derived from *base_name*.

        Results are sorted lexicographically (oldest → newest) based on
        the ``__vYYYYMMDD_HHMMSS`` timestamp suffix.

        Args:
            base_name: The logical/alias name whose versions to list
                (e.g. ``"articles"``).  Shard sub-entries are excluded.

        Returns:
            A list of versioned physical names, e.g.
            ``["articles__v20260210_143022", "articles__v20260210_150545"]``.
            Backends without versioning support return ``[]``.
        """
        return []

    def _generate_versioned_name(self, base_name: str) -> str:
        """Return a timestamped physical name derived from *base_name*.

        The default implementation appends no timestamp and returns
        *base_name* as-is.  Backends that support versioning override
        this to produce ``"{base_name}__vYYYYMMDD_HHMMSS"``.

        Args:
            base_name: The logical index name (e.g. ``"articles"``).

        Returns:
            A physical name string unique to the call time.
        """
        return base_name

    # Source-info persistence (smart worker support)

    def save_source_info(self, name: str, info: Dict[str, Any]) -> None:
        """Persist data-source metadata alongside the index.

        This metadata allows :class:`~yeny.core.worker.IndexWorker` to
        auto-generate ``data_fn`` and ``delta_fn`` without user input.

        Args:
            name: Physical index name to associate the metadata with.
            info: Dict describing the data source.  Recognised keys:
                ``type`` (``"table"`` or ``"query"``), ``table_name``,
                ``text_column`` (str or list), ``id_column``,
                ``date_column``, ``where_clause``, and ``query``.
        """
        pass  # no-op for backends that don't support it

    def load_source_info(self, name: str) -> Optional[Dict[str, Any]]:
        """Load previously-saved data-source metadata for *name*.

        Args:
            name: Physical index name whose metadata to retrieve.

        Returns:
            The source-info dict saved by :meth:`save_source_info`, or
            ``None`` if no metadata was stored (or the backend does not
            support it).
        """
        return None

    def count_rows(self, table_name: str) -> Optional[int]:
        """Return the row count of *table_name* in the underlying database.

        Used by :meth:`~yeny.main.Yeny._auto_change_detector` to
        detect when the source data has grown and a rebuild is needed.

        Args:
            table_name: Name of the user table to count.

        Returns:
            Integer row count, or ``None`` if this backend does not
            have direct database access.
        """
        return None

    # Shard support (temporal partitioning)

    def save_shard_registry(self, index_name: str, shard_keys: list) -> None:
        """Persist the list of shard keys for a sharded index.

        Args:
            index_name: The versioned physical name of the parent index.
            shard_keys: List of shard keys (e.g. ``["2026_01", "9999_99"]``).
        """
        pass  # no-op for backends without shard support

    def load_shard_registry(self, index_name: str) -> list:
        """Return the shard keys for *index_name*.

        Args:
            index_name: The versioned physical name of the parent index.

        Returns:
            Sorted list of shard keys (e.g. ``["2026_01", "9999_99"]``).
            An empty list means the index is monolithic (not sharded).
        """
        return []

    def is_sharded(self, index_name: str) -> bool:
        """Return ``True`` if *index_name* is a sharded (temporal) index.

        Args:
            index_name: The versioned physical name of the parent index.

        Returns:
            ``True`` if at least one shard key is registered for the
            index, ``False`` for monolithic indices.
        """
        return len(self.load_shard_registry(index_name)) > 0