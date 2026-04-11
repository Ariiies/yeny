"""
lucis.mixins — Modular components of the Lucis facade.

Each mixin isolates a distinct responsibility:

- ``LoaderMixin``: factory class methods (``from_dict``, ``from_alchemy_table``, …)
- ``SearchMixin``: search orchestration and shard preloading.
- ``PersistenceMixin``: save, load, versioning, rollback, binary generation.
- ``AutomationMixin``: indexing, reindex, incremental updates, worker creation,
  health monitoring, and source connection.
"""
from .loaders import LoaderMixin
from .search import SearchMixin
from .persistence import PersistenceMixin
from .automation import AutomationMixin

__all__ = [
    "LoaderMixin",
    "SearchMixin",
    "PersistenceMixin",
    "AutomationMixin",
]
