# src/corpyplus/storage/json_storage.py
import json
import os
from typing import Any, Dict
from .base import BaseStorage

class JSONStorage(BaseStorage):
    """
    Lightweight implementation of persistence in JSON format.
    Ideal for debugging, transparency, learning, and very small projects.
    """

    def __init__(self, directory: str = "data"):
        self.directory = directory
        # Create the directory if it doesn't exist to avoid path errors
        if not os.path.exists(self.directory):
            os.makedirs(self.directory)

    def _get_path(self, name: str) -> str:
        """Internal method to construct the file path."""
        return os.path.join(self.directory, f"{name}.json")

    def save(self, data: Dict[str, Any], name: str) -> None:
        """Serializes the dictionary to a human-readable .json file."""
        #path = self._get_path(name)
        with open((path:=self._get_path(name)), 'w', encoding='utf-8') as f:
            # indent=4 makes the file easy to read for a human
            json.dump(data, f, indent=4, ensure_ascii=False)

    def load(self, name: str) -> Dict[str, Any]:
        """Reads the .json file and converts it back into a dictionary."""
        path = self._get_path(name)
        if not self.exists(name):
            raise FileNotFoundError(f"Index not found: {path}")
            
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def exists(self, name: str) -> bool:
        """Checks if the file exists on disk."""
        return os.path.exists(self._get_path(name))