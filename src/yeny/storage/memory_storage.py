"""
Ephemeral in-memory storage backend for Yeny.

Stores all index states, metadata, and aliases in Python heap memory
without touching the filesystem. Ideal for unit tests, ephemeral workers,
quick prototyping, and zero-disk environments.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional
from .base import BaseStorage


class MemoryStorage(BaseStorage):
    """Universal in-memory storage adapter for testing and ephemeral workflows.

    Leaves zero trace on disk: stores engine states, aliases, and registries
    entirely in Python RAM.
    """

    _in_memory: bool = True

    def __init__(self) -> None:
        self._store: Dict[str, Dict[str, Any]] = {}
        self._aliases: Dict[str, str] = {}
        self._shard_registries: Dict[str, List[str]] = {}
        self._source_infos: Dict[str, Dict[str, Any]] = {}

    def save(self, engine_state: Dict[str, Any], name: str) -> None:
        """Persist engine state directly in RAM dictionary."""
        self._store[name] = engine_state

    def load(self, name: str) -> Dict[str, Any]:
        """Load engine state from RAM dictionary."""
        target = self.resolve_alias(name)
        if target not in self._store:
            raise FileNotFoundError(f"Index '{name}' not found in memory storage.")
        return self._store[target]

    def exists(self, name: str) -> bool:
        """Return True if the index exists in RAM."""
        target = self.resolve_alias(name)
        return target in self._store

    def resolve_alias(self, name: str) -> str:
        """Resolve logical alias to target physical index in RAM."""
        return self._aliases.get(name, name)

    def set_alias(self, alias_name: str, target_index: str) -> None:
        """Register or update an alias mapping in RAM."""
        self._aliases[alias_name] = target_index

    def get_alias(self, alias_name: str) -> Optional[str]:
        """Retrieve target physical index for an alias from RAM."""
        return self._aliases.get(alias_name)

    def list_aliases(self) -> Dict[str, str]:
        """Return a copy of registered aliases."""
        return dict(self._aliases)

    def delete_alias(self, alias_name: str) -> None:
        """Remove an alias mapping."""
        self._aliases.pop(alias_name, None)

    def save_source_info(self, name: str, info: Dict[str, Any]) -> None:
        """Store source metadata in RAM."""
        self._source_infos[name] = info

    def load_source_info(self, name: str) -> Optional[Dict[str, Any]]:
        """Load source metadata from RAM."""
        return self._source_infos.get(name)

    def save_shard_registry(self, index_name: str, shard_keys: list) -> None:
        """Store shard keys for an index in RAM."""
        self._shard_registries[index_name] = list(shard_keys)

    def load_shard_registry(self, index_name: str) -> list:
        """Load shard keys for an index from RAM."""
        return list(self._shard_registries.get(index_name, []))

    def get_total_docs(self, name: str) -> int:
        """Query total documents from stored engine state in RAM."""
        target = self.resolve_alias(name)
        if target in self._store:
            return self._store[target].get("total_docs", 0)
        return 0

    def delete(self, name: str) -> None:
        """Delete an index state and related metadata from RAM."""
        target = self.resolve_alias(name)
        self._store.pop(target, None)
        self._store.pop(name, None)
        self._aliases.pop(name, None)
        self._shard_registries.pop(name, None)
        self._source_infos.pop(name, None)

    def list_indices(self) -> List[str]:
        """Return list of physical indices stored in RAM."""
        return list(self._store.keys())

    def close(self) -> None:
        """No-op for in-memory storage. Preserves RAM store across instance lifecycles."""
        pass

    def clear(self) -> None:
        """Explicitly clear all in-memory structures."""
        self._store.clear()
        self._aliases.clear()
        self._shard_registries.clear()
        self._source_infos.clear()

    def __repr__(self) -> str:
        return f"MemoryStorage(indices={len(self._store)})"

