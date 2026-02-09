from typing import Any, List, Dict, Tuple, Optional, Union
from .base import BaseEngine, DocId

# import utils functions (relative imports to avoid circular dependencies)
from ..utils.index.core import build_index as build_idx_func
from ..utils.index.stats import get_doc_len, compute_tfidf, compute_idf
from ..utils.math.core import sparse_cosine_similarity, sort_results
from ..utils.decorators import doc_input
from ..utils.nlp import word_tokenizer
from ..exceptions import CorpyEmptyCorpusError

class CoreEngine(BaseEngine):
    """
    The heart of CorpyPlus.
    Uses pure Python dictionaries and math for reliable, dependency-free searching.
    """

    def __init__(self, storage: Optional[Any] = None):
        super().__init__(storage=storage)
        # Save vectors to avoid recomputing on each search
        self.doc_vectors: Dict[int, Dict[str, float]] = {}

    @property
    def name(self) -> str:
        return "CoreEngine"

    def build_index(self, corpus: Union[List[str], Dict[str, str]]) -> None:
        """
        Builds the inverted index and pre-calculates all document vectors.
        
        Accepts two input formats:
        - List[str]: Simple list of documents
        - Dict[str, str]: Dictionary with {id: text} for custom IDs
        
        When using Dict input, search results will return the original keys
        instead of sequential integers.
        """
        # Normalize input: separate texts from IDs
        texts, self.id_map = self._normalize_corpus(corpus)

        if not texts:
           raise CorpyEmptyCorpusError("Cannot index data: the corpus is empty.")
        
        self.total_docs = len(texts)
        if self.total_docs == 0:
            return

        # 1. Build the inverted index (Core)
        self.index = build_idx_func(texts)
        
        # 2. Calculate document lengths for TF normalization
        self.doc_lengths = get_doc_len(self.index, self.total_docs)
        
        # 3. Pre-calculate TF-IDF vectors for each document
        # This makes subsequent searches O(n_documents) instead of recalculating everything
        self._precompute_all_vectors()

    def _precompute_all_vectors(self) -> None:
        """Helper to pre-calculate TF-IDF vectors for the entire corpus."""
        for doc_id in range(self.total_docs):
            doc_vector = {}
            # Only iterate over words that actually appear in this document
            # (We know this thanks to the inverted index)
            for word, docs in self.index.items():
                if doc_id in docs:
                    score = compute_tfidf(
                        word, doc_id, self.index, 
                        self.doc_lengths, self.total_docs
                    )
                    doc_vector[word] = score
            self.doc_vectors[doc_id] = doc_vector

    @doc_input(word_tokenizer)
    def search(self, query: List[str], top_k: int = 10) -> List[Tuple[DocId, float]]:
        """
        Finds documents most similar to the query.
        
        Returns a list of tuples (original_doc_id, similarity_score)
        sorted by relevance. The doc_id matches the input format:
        - If indexed with Dict: returns original keys ("doc_001", "doc_002"...)
        - If indexed with List: returns integers (0, 1, 2...)
        """
        if not query or not self.index:
            return []

        # 1. Build the query vector (Query Vector)
        # For the query, we use a simplified TF-IDF based on corpus stats
        query_vector = self._build_query_vector(query)
        
        # 2. Find candidate documents
        # (Only those that share at least one word with the query)
        candidate_ids = set()
        for token in query:
            if token in self.index:
                candidate_ids.update(self.index[token].keys())
        
        # 3. Calculate similarities
        scores = {}
        for doc_id in candidate_ids:
            sim = sparse_cosine_similarity(query_vector, self.doc_vectors[doc_id])
            if sim > 0:
                scores[doc_id] = sim
        
        # 4. Sort and get top results (still using internal indices)
        internal_results = sort_results(scores, limit=top_k)
        
        # 5. Map internal indices back to original document IDs
        return [(self.id_map[doc_id], score) for doc_id, score in internal_results]

    def _build_query_vector(self, query_tokens: List[str]) -> Dict[str, float]:
        """Creates a TF-IDF sparse vector for the query."""
        query_vec = {}
        q_len = len(query_tokens)
        
        # Count terms in the query
        counts = {}
        for t in query_tokens:
            counts[t] = counts.get(t, 0) + 1
            
        for token, count in counts.items():
            if token in self.index:
                # TF of the query / length of the query
                tf = count / q_len
                # compute_idf imported at top of file
                idf = compute_idf(token, self.index, self.total_docs)
                query_vec[token] = tf * idf
                
        return query_vec
    
    def persist(self, name: str) -> None:
        """Packages the current state and sends it to storage."""
        if not self.storage:
            raise ValueError("No storage adapter configured in the engine.")
        
        # Prepare the 'bundle' of data
        state = {
            "index": self.index,
            "total_docs": self.total_docs,
            "doc_lengths": self.doc_lengths,
            "doc_vectors": self.doc_vectors,
            "id_map": self.id_map,  # Essential for returning original IDs after loading
            "id_type": self.id_type
        }
        self.storage.save(state, name)

    def load_engine(self, name: str) -> None:
        """Loads a saved state and reconstructs the engine."""
        if not self.storage:
            raise ValueError("No storage adapter configured in the engine.")
        
        state = self.storage.load(name)
        
        # Reconstruct internal attributes
        # Use .get() for safety or direct assignment
        self.index = state["index"]
        self.total_docs = state["total_docs"]
        self.doc_lengths = state["doc_lengths"]
        self.doc_vectors = state.get("doc_vectors", {})
        # Backward compatibility: if id_map not saved, assume sequential integers
        self.id_map = state.get("id_map", {i: i for i in range(self.total_docs)})
        self.id_type = state.get("id_type", "none")