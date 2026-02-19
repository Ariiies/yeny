from abc import ABC, abstractmethod
from typing import Any, Callable, List, Dict, Optional, Union, Tuple
from ..exceptions import LucisInvalidDocumentError
from ..utils.nlp import word_tokenizer

# Type alias for document IDs - can be int, str, or any hashable type
DocId = Any

class BaseEngine(ABC):
    """
    Abstract Base Class for all Lucis engines.
    
    The engine is an orchestrator: it connects NLP processing, 
    indexing logic, and mathematical similarities.
    
    Supports two input formats:
    - List[str]: Simple list of documents, IDs will be 0, 1, 2...
    - Dict[str, str]: Dictionary with {id: text}, preserves original IDs
    """

    def __init__(self, storage: Optional[Any] = None, preprocessor: Optional[Callable[[str], Union[str, List[str]]]] = None):
        self.index: Dict[str, Dict[int, int]] = {}
        self.total_docs: int = 0
        # doc_len is vital for TF calculations
        self.doc_lengths: Dict[int, int] = {}
        self.storage = storage
        # Maps internal index (0, 1, 2...) to original document ID
        # Essential for returning meaningful results to the user
        self.id_map: Dict[int, DocId] = {}
        self.id_type: str = "none"  # "sequential", "custom" o "none"
        # Configurable preprocessor — injected from Lucis or defaults to word_tokenizer.
        # Can return str (Lucis will tokenize with simple_tokenizer as fallback)
        # or list[str] (used directly as tokens).
        self.preprocessor: Callable[[str], Union[str, List[str]]] = preprocessor or word_tokenizer

    @property
    @abstractmethod
    def name(self) -> str:
        """The identifier name of the engine."""
        pass

    @abstractmethod
    def build_index(self, corpus: List[List[str]]) -> None:
        """
        Processes the tokenized corpus and stores the inverted index.
        
        This method should also populate self.doc_lengths and self.total_docs.
        """
        pass

    @abstractmethod
    def search(self, query_tokens: List[str], top_k: int = 10) -> List[Tuple[DocId, float]]:
        """
        Performs a search and returns ranked results (doc_id, score).
        
        Returns original document IDs, not internal indices.
        Example: [("doc_001", 0.85), ("doc_003", 0.72)] for dict input
                 [(0, 0.85), (2, 0.72)] for list input
        """
        pass
    
    def _normalize_corpus(self, corpus: Union[List[str], Dict[Any, str]]) -> Tuple[List[str], Dict[int, DocId]]:
        """
        Normalizes input corpus to a standard format.
        
        Handles two input types:
        - Dict[str, str]: {"doc_001": "text...", "doc_002": "text..."}
          → Returns texts as list, id_map preserves original keys
        - List[str]: ["text...", "text..."]
          → Returns as-is, id_map uses sequential integers
        
        This separation allows the indexing logic to work with simple lists
        while maintaining the mapping to return original IDs in search results.
        """
        if isinstance(corpus, dict):
            # Dict input: extract texts and preserve original IDs
            id_map = {i: key for i, key in enumerate(corpus.keys())}
            texts = list(corpus.values())
            self.id_type = "custom"
        elif isinstance(corpus, list):
            # List input: use sequential integers as IDs
            id_map = {i: i for i in range(len(corpus))}
            texts = corpus
            self.id_type = "sequential"
        else:
            # For safety - should not happen due to type hints
            raise LucisInvalidDocumentError(detail="Corpus must be either a List[str] or Dict[Any, str].")
        
        return texts, id_map