"""
BasicLoadersMixin — Factory methods for simple in-memory data sources.

Contains the ``from_dict`` and ``from_list`` class methods that create
a ready-to-search Yeny instance from a plain ``dict`` or ``list``
already held in memory (no external database involved).
"""
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional

from ...config import YenyOptions

if TYPE_CHECKING:
    from ...main import Yeny


class BasicLoadersMixin:
    """Mixin that provides the ``from_dict`` and ``from_list`` factory methods.

    These methods create a new ``Yeny`` instance, ingest data held
    directly in memory, persist the index, and return it ready to
    search.
    """

    @classmethod
    def from_dict(
        cls,
        data: Dict[Any, str],
        name: str = "default",
        *,
        engine: str = "core",
        preprocessor: Optional[Callable] = None,
        options: Optional[YenyOptions] = None,
    ) -> "Yeny":
        """
        Creates a Yeny instance from a dictionary {id: text}.
        
        Preserves original keys as document IDs in search results.
        This is the recommended format when you have meaningful IDs
        (e.g., database PKs, document codes, email addresses).

        Args:
            data: Dictionary mapping document IDs to their text content.
            name: Identifier for persistence.
            engine: Search engine implementation: ``"core"`` or ``"lite"``.
            preprocessor: Optional shared indexing/search preprocessing function.
            options: Advanced storage, binary, and memory configuration.

        Returns:
            A ready-to-search Yeny instance.

        Example:
            yn = Yeny.from_dict({
                "doc_001": "Python es un lenguaje versátil",
                "doc_002": "El amor por la programación crece cada día"
            })
            results = yn.search("programación python")
        """
        # autoload=False to avoid loading stale data before indexing fresh data
        instance = cls(
            name=name,
            engine=engine,
            preprocessor=preprocessor,
            autoload=False,
            options=options,
        )
        instance.index(data)
        return instance

    @classmethod
    def from_list(
        cls,
        data: List[str],
        name: str = "default",
        *,
        engine: str = "core",
        preprocessor: Optional[Callable] = None,
        options: Optional[YenyOptions] = None,
    ) -> "Yeny":
        """
        Creates a Yeny instance from a list of text documents.
        
        Document IDs will be auto-generated as sequential integers (0, 1, 2...).
        This is the simplest way to get started when IDs don't matter.

        Args:
            data: List of text documents.
            name: Identifier for persistence.
            engine: Search engine implementation: ``"core"`` or ``"lite"``.
            preprocessor: Optional shared indexing/search preprocessing function.
            options: Advanced storage, binary, and memory configuration.

        Returns:
            A ready-to-search Yeny instance.

        Example:
            yn = Yeny.from_list([
                "Python es un lenguaje versátil",
                "El amor por la programación crece cada día"
            ])
            results = yn.search("programación")
        """
        instance = cls(
            name=name,
            engine=engine,
            preprocessor=preprocessor,
            autoload=False,
            options=options,
        )
        instance.index(data)
        return instance
