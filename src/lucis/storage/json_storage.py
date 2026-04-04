# src/lucis/storage/json_storage.py
import json
import os
from typing import Any, Dict, List
from .base import BaseStorage

class JSONStorage(BaseStorage):
    """
    Lightweight persistence backend using human-readable JSON files.

    Each index is stored as a single ``.json`` file inside *directory*.
    Ideal for debugging, transparency, learning, and very small projects.
    Not recommended for large datasets (> 50 K documents) due to the
    overhead of serializing and deserializing the entire index at once.

    Args:
        directory: Path to the folder where ``.json`` files are stored.
            Created automatically if it does not exist.  Defaults to
            ``"data"``.
    """

    def __init__(self, directory: str = "data"):
        self.directory = directory
        # Create the directory if it doesn't exist to avoid path errors
        if not os.path.exists(self.directory):
            os.makedirs(self.directory)

    def _get_path(self, name: str) -> str:
        """Construct the absolute file path for *name*.

        Args:
            name: Logical index name (no extension).

        Returns:
            Absolute path string of the form ``"{directory}/{name}.json"``.
        """
        return os.path.join(self.directory, f"{name}.json")

    def save(self, data: Dict[str, Any], name: str) -> None:
        """Serialize *data* to a human-readable ``.json`` file.

        Args:
            data: Engine-state dict produced by ``BaseEngine.persist()``.
            name: Logical index name used as the file stem.

        Raises:
            OSError: If the directory is not writable or the disk is full.
        """
        #path = self._get_path(name)
        with open((path:=self._get_path(name)), 'w', encoding='utf-8') as f:
            # indent=4 makes the file easy to read for a human
            json.dump(data, f, indent=4, ensure_ascii=False)

    def load(self, name: str) -> Dict[str, Any]:
        """Read the ``.json`` file for *name* and return the engine state.

        Args:
            name: Logical index name (same key used in :meth:`save`).

        Returns:
            The engine-state dict as stored on disk.

        Raises:
            FileNotFoundError: If the corresponding ``.json`` file does
                not exist on disk.
        """
        path = self._get_path(name)
        if not self.exists(name):
            raise FileNotFoundError(f"Index not found: {path}")
            
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def exists(self, name: str) -> bool:
        """Return ``True`` if the ``.json`` file for *name* exists on disk.

        Args:
            name: Logical index name to check.

        Returns:
            ``True`` if ``{directory}/{name}.json`` is present on disk.
        """
        return os.path.exists(self._get_path(name))

    # Shard support (temporal partitioning)

    def save_shard_registry(self, index_name: str, shard_keys: list) -> None:
        """Persist shard keys as ``{index_name}__shards.json``.

        Args:
            index_name: The versioned physical name of the parent index.
            shard_keys: List of shard keys (e.g. ``["2026_01", "9999_99"]``).
        """
        path = os.path.join(self.directory, f"{index_name}__shards.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(shard_keys, f)

    def load_shard_registry(self, index_name: str) -> list:
        """Load shard keys from ``{index_name}__shards.json``.

        Args:
            index_name: The versioned physical name of the parent index.

        Returns:
            List of shard keys, or ``[]`` if the registry file is absent.
        """
        path = os.path.join(self.directory, f"{index_name}__shards.json")
        if not os.path.exists(path):
            return []
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)