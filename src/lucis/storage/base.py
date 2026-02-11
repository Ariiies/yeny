from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class BaseStorage(ABC):
    """
    Universal interface for storage backends. 
    """
    
    @abstractmethod
    def save(self, engine_state: Dict[str, Any], name: str) -> None:
        """Serializes and saves the engine state."""
        pass

    @abstractmethod
    def load(self, name: str) -> Dict[str, Any]:
        """Loads the engine state."""
        pass

    @abstractmethod
    def exists(self, name: str) -> bool:
        """Checks if the data already exists in this storage."""
        pass

    # Alias / versioning support (opt-in)
    # These methods have concrete defaults so that simple backends
    # (e.g. JSONStorage) work without changes.  Database-backed
    # storages override them to enable shadow-index swap.

    def resolve_alias(self, name: str) -> str:
        """Resolve *name* to a physical index name.

        If *name* is a registered alias, return the target it points to.
        Otherwise return *name* unchanged (passthrough).
        """
        return name

    def set_alias(self, alias_name: str, target_index: str) -> None:
        """Create or update an alias so it points to *target_index*."""
        pass  # no-op for backends without alias support

    def get_alias(self, alias_name: str) -> Optional[str]:
        """Return the target index for *alias_name*, or ``None``."""
        return None

    def list_versions(self, base_name: str) -> list:
        """Return all physical index names that are versions of *base_name*.

        Results are sorted lexicographically (oldest → newest) based on
        the ``__vYYYYMMDD_HHMMSS`` suffix.

        Backends that don't support versioning return an empty list.
        """
        return []

    def _generate_versioned_name(self, base_name: str) -> str:
        """Return a timestamped physical name derived from *base_name*.

        Backends that don't support versioning simply return *base_name*.
        """
        return base_name