"""
PersistenceMixin — Save, load, versioning, rollback, binary generation, and lifecycle.

Manages everything related to persisting the index to storage and
loading it back: versioned save/load, alias management, shard
registries, rollback, .lcs binary generation, and resource cleanup.
"""
import os
from typing import List, Optional

from ..sync.source_spec import SourceSpec
from ..storage.metadata_storage import MetadataStorage
from ..exceptions import LucisEngineError


class PersistenceMixin:
    """Mixin that provides persistence and lifecycle management."""

    def save(self, name: Optional[str] = None) -> None:
        """
        Persists the current index to storage.
        
        On database-backed storages (SQLite, Alchemy) this creates a
        versioned physical index (e.g. ``my_idx__v20260210_143022``)
        and points the logical alias to it.  On JSON storage the
        behaviour is unchanged (no versioning).

        When sharded, each shard is persisted independently and a
        shard registry is saved alongside the parent metadata.

        Args:
            name: Optional custom name. Falls back to self.name.
        """
        save_name = name or self.name
        physical_name = self.storage._generate_versioned_name(save_name)

        if self._shard_manager:
            # Sharded save
            # 1. Persist each shard engine
            self._shard_manager.persist_all(physical_name)

            # 2. Create parent metadata entry (empty index data, just metadata)
            parent_state = {
                "index": {},
                "total_docs": self._shard_manager.total_docs,
                "doc_lengths": {},
                "id_map": {},
                "id_type": self._shard_manager.id_type,
                "engine_name": self.engine.name,
            }
            self.storage.save(parent_state, physical_name)
        else:
            # Single-engine save
            self.engine.persist(physical_name)

            # When using MetadataStorage, persist() only saves metadata.
            # We must also write the .lcs binary so data is recoverable.
            if isinstance(self.storage, MetadataStorage) and self._binary_dir:
                save_fn = getattr(self.engine, "save_binary", None)
                if save_fn is not None:
                    import os as _os
                    _os.makedirs(self._binary_dir, exist_ok=True)
                    lcs_path = _os.path.join(self._binary_dir, f"{physical_name}.lcs")
                    save_fn(lcs_path)

        # Point the logical alias to the new physical index
        self.storage.set_alias(save_name, physical_name)

        # Persist source info so the worker can auto-generate data_fn
        if self._source_info is not None:
            self.storage.save_source_info(
                physical_name, self._source_info.to_dict()
            )

    def load(self, name: Optional[str] = None) -> None:
        """
        Loads a previously saved index from storage.

        If *name* is an alias, it is resolved to the physical index
        name transparently.  Automatically detects whether the index
        is sharded and loads all shards if so.

        Args:
            name: Optional custom name. Falls back to self.name.
        """
        load_name = name or self.name
        physical_name = self.storage.resolve_alias(load_name)

        # Check if this is a sharded index
        shard_keys = self.storage.load_shard_registry(physical_name)

        if shard_keys:
            # Sharded load 
            self._init_shard_manager()
            lazy = self._max_loaded_shards > 0 or self._memory_limit_mb is not None
            self._shard_manager.load_all(physical_name, shard_keys, lazy=lazy)
            self._is_indexed = True
        else:
            # Single-engine load
            # When using MetadataStorage, prefer .lcs binary (has full data).
            # MetadataStorage.load() only returns metadata — no index data.
            lcs_loaded = False
            if isinstance(self.storage, MetadataStorage) and self._binary_dir:
                from ..utils.mmap_storage import lcs_exists as _lcs_exists
                lcs_path = os.path.join(self._binary_dir, f"{physical_name}.lcs")
                if _lcs_exists(lcs_path) and hasattr(self.engine, "load_mmap"):
                    self.engine.load_mmap(lcs_path)
                    lcs_loaded = True
            if not lcs_loaded:
                self.engine.load_engine(physical_name)
            self._is_indexed = True

        # Restore source info (if available) so create_worker() works
        source = self.storage.load_source_info(physical_name)
        if source is not None:
            self._source_info = SourceSpec.from_dict(source)

    def rollback(self) -> None:
        """
        Roll back the alias to the previous index version.

        Looks at all physical versions for ``self.name``, finds the one
        right before the current target, swaps the alias, and reloads
        the engine.

        Raises:
            LucisEngineError: If there is no alias or no previous version.

        Example::

            luc.rollback()
            # → alias points to the version before the current one
        """
        current_target = self.storage.get_alias(self.name)
        if current_target is None:
            raise LucisEngineError(
                engine_name=self.engine.name,
                detail=f"No alias found for '{self.name}'. Cannot rollback."
            )

        versions = self.storage.list_versions(self.name)
        if len(versions) < 2:
            raise LucisEngineError(
                engine_name=self.engine.name,
                detail=f"No previous version to rollback to for '{self.name}'."
            )

        try:
            current_idx = versions.index(current_target)
        except ValueError:
            raise LucisEngineError(
                engine_name=self.engine.name,
                detail=(
                    f"Current target '{current_target}' not found in "
                    f"versions list. The physical index may have been deleted."
                )
            )

        if current_idx == 0:
            raise LucisEngineError(
                engine_name=self.engine.name,
                detail="Already at the oldest version. Cannot rollback further."
            )

        previous = versions[current_idx - 1]
        self.storage.set_alias(self.name, previous)
        self.load()

    def list_versions(self) -> List[str]:
        """
        List all physical versions of this index.

        Returns a list of physical index names sorted oldest → newest.

        Returns:
            List of versioned physical names.

        Example::

            luc.list_versions()
            # ['articles__v20260210_143022', 'articles__v20260210_150545']
        """
        return self.storage.list_versions(self.name)

    def purge_old_versions(self, keep: int = 2) -> int:
        """
        Delete old index versions, keeping the *keep* most recent ones.

        The version currently pointed to by the alias is **always** kept,
        even if it falls outside the *keep* window.

        Args:
            keep: Number of most-recent versions to retain (default 2).

        Returns:
            Number of versions deleted.

        Example::

            deleted = luc.purge_old_versions(keep=2)
            print(f"Cleaned up {deleted} old versions")
        """
        versions = self.storage.list_versions(self.name)
        if len(versions) <= keep:
            return 0

        # Current alias target must be protected
        current_target = self.storage.get_alias(self.name)

        # Keep the N most recent + the current target
        to_keep = set(versions[-keep:])
        if current_target:
            to_keep.add(current_target)

        to_delete = [v for v in versions if v not in to_keep]
        for v in to_delete:
            self.storage.delete(v)

        return len(to_delete)

    def generate_lcs(self) -> int:
        """Write ``.lcs`` binary cache files for all currently-loaded shards.

        This is the one-time step needed to enable mmap-based loading.
        Call it once after a normal index load, then on subsequent runs
        Lucis will automatically use the ``.lcs`` files (near-zero heap RAM).

        The index in MySQL/SQLite is **not** modified — ``.lcs`` files
        are only a read cache stored in ``binary_dir`` (default:
        ``{storage_dir}/lcs/``).

        Returns:
            Number of ``.lcs`` files written.

        Raises:
            RuntimeError: If the instance is not sharded, not indexed,
                or ``binary_dir`` is ``None``.

        Example::

            luc = Lucis(name="email_idx", ...)
            n = luc.generate_lcs()
            print(f"Generated {n} .lcs files")
            luc.close()
            # Next load will use mmap automatically
        """
        if self._shard_manager is None:
            raise RuntimeError(
                "generate_lcs() is only supported for sharded indexes. "
                "Non-sharded indexes don't benefit from .lcs files."
            )
        if not self._is_indexed:
            raise RuntimeError(
                "generate_lcs() requires a loaded index. "
                "Load or build the index before calling generate_lcs()."
            )
        if self._shard_manager._binary_dir is None:
            raise RuntimeError(
                "generate_lcs() requires binary_dir to be set. "
                "Pass options=LucisOptions(binary_dir='auto') when creating Lucis."
            )
        base_name = self._shard_manager._lazy_base_name or self.name
        return self._shard_manager.write_lcs_files(base_name)

    def close(self) -> None:
        """Release all mmap handles held by loaded shard engines.

        Also closes the DatabaseReader if one is attached.

        Call this before deleting ``.lcs`` files on Windows, or when
        the ``Lucis`` instance is no longer needed and you want to
        free OS-level file handles immediately.
        """
        if self._shard_manager is not None:
            self._shard_manager.close()
        else:
            close_fn = getattr(self.engine, "close_mmap", None)
            if close_fn is not None:
                close_fn()
        if self._reader is not None:
            close_fn = getattr(self._reader, "close", None)
            if close_fn is not None:
                close_fn()
            self._reader = None
