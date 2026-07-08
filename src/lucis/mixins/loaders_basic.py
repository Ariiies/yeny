"""
BasicLoadersMixin — Factory methods for simple in-memory data sources.

Contains the ``from_dict`` and ``from_list`` class methods that create
a ready-to-search Lucis instance from a plain ``dict`` or ``list``
already held in memory (no external database involved).
"""
from typing import TYPE_CHECKING, Any, Dict, List

if TYPE_CHECKING:
    from ..main import Lucis


class BasicLoadersMixin:
    """Mixin that provides the ``from_dict`` and ``from_list`` factory methods.

    These methods create a new ``Lucis`` instance, ingest data held
    directly in memory, persist the index, and return it ready to
    search.
    """

    @classmethod
    def from_dict(
        cls,
        data: Dict[Any, str],
        name: str = "default",
        **kwargs
    ) -> "Lucis":
        """
        Creates a Lucis instance from a dictionary {id: text}.
        
        Preserves original keys as document IDs in search results.
        This is the recommended format when you have meaningful IDs
        (e.g., database PKs, document codes, email addresses).

        Args:
            data: Dictionary mapping document IDs to their text content.
            name: Identifier for persistence.
            **kwargs: Additional arguments passed to __init__ (storage_dir, engine, etc.)

        Returns:
            A ready-to-search Lucis instance.

        Example:
            lu = Lucis.from_dict({
                "doc_001": "Python es un lenguaje versátil",
                "doc_002": "El amor por la programación crece cada día"
            })
            results = lu.search("programación python")
        """
        # autoload=False to avoid loading stale data before indexing fresh data
        instance = cls(name=name, autoload=False, **kwargs)
        instance.index(data)
        return instance

    @classmethod
    def from_list(
        cls,
        data: List[str],
        name: str = "default",
        **kwargs
    ) -> "Lucis":
        """
        Creates a Lucis instance from a list of text documents.
        
        Document IDs will be auto-generated as sequential integers (0, 1, 2...).
        This is the simplest way to get started when IDs don't matter.

        Args:
            data: List of text documents.
            name: Identifier for persistence.
            **kwargs: Additional arguments passed to __init__ (storage_dir, engine, etc.)

        Returns:
            A ready-to-search Lucis instance.

        Example:
            lu = Lucis.from_list([
                "Python es un lenguaje versátil",
                "El amor por la programación crece cada día"
            ])
            results = lu.search("programación")
        """
        instance = cls(name=name, autoload=False, **kwargs)
        instance.index(data)
        return instance
