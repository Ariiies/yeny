from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List,  Union
from ..engines.base import DocId


# Response Data Classes - structured, type-safe, and ready for JSON serialization
# Immutable (frozen) dataclasses for structured, type-safe search responses.
# Using dataclass over TypedDict because:
#   - __repr__ for readable debug output
#   - Methods (.to_dict()) for easy JSON serialization
#   - frozen=True guarantees response integrity after creation
#   - Full IDE autocompletion on every field

@dataclass(frozen=True)
class SearchResult:
    """
    A single document match from a search query.
    
    Attributes:
        doc_id: The original document identifier (preserves input format).
        score: Cosine similarity score between query and document (0.0 to 1.0).
        rank: Position in the results list (1-based, most relevant first).
    """
    doc_id: DocId
    score: float
    rank: int


@dataclass(frozen=True)
class SearchResponse:
    """
    Complete structured response from a Corpy search.

    Provides all context needed to understand, display, or further process
    search results — from the original query to timing metadata.

    Attributes:
        query: The raw query as received from the user.
        tokens: The tokenized form actually used for matching.
        engine: Name of the engine that performed the search.
        total_results: Number of documents found.
        search_time_ms: Wall-clock search time in milliseconds.
        results: Ranked list of SearchResult objects.
    """
    query: Union[str, List[str]]
    tokens: List[str]
    engine: str
    total_results: int
    search_time_ms: float
    results: List[SearchResult] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Serializes the response to a plain dict (JSON-ready)."""
        return asdict(self)

    def __getitem__(self, key: str) -> Any:
        """Allows dict-like access: response['results'] for convenience."""
        return getattr(self, key)