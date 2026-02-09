from abc import ABC, abstractmethod
from typing import Any, Dict

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