from typing import Any, List, Dict, Tuple, Optional, Union
from .base import BaseEngine, DocId

# import utils functions 
from ..utils.index.core import build_index as build_idx_func
from ..utils.index.stats import get_doc_len, compute_tfidf, compute_idf
from ..utils.math.core import sparse_cosine_similarity, sort_results
from ..utils.nlp import simple_tokenizer
from ..utils.compact import (
    CompactPostings,
    CompactDocLengths,
    freeze_index,
    thaw_index,
    freeze_doc_lengths,
)
from ..exceptions import LucisEmptyCorpusError

class CoreEngine(BaseEngine):
    """
    The heart of Lucis.
    Uses pure Python dictionaries and math for reliable, dependency-free searching.
    """

    # CoreEngine defaults to word_tokenizer (inherited from BaseEngine fallback)
    _default_preprocessor = None  # → falls through to word_tokenizer in BaseEngine

    def __init__(self, storage: Optional[Any] = None, preprocessor: Optional[Any] = None):
        super().__init__(storage=storage, preprocessor=preprocessor)
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
           raise LucisEmptyCorpusError("Cannot index data: the corpus is empty.")
        
        self.total_docs = len(texts)
        if self.total_docs == 0:
            return

        # 1. Preprocess with the configured preprocessor.
        # If it returns str (text-only preprocessor), apply simple_tokenizer as fallback.
        tokenized = []
        for doc in texts:
            result = self.preprocessor(doc)
            tokenized.append(simple_tokenizer(result) if isinstance(result, str) else result)

        # 2. Build the inverted index (Core)
        raw_index = build_idx_func(tokenized)
        
        # 3. Calculate document lengths for TF normalization
        raw_doc_lengths = get_doc_len(raw_index, self.total_docs)

        # 4. Pre-calculate TF-IDF vectors (uses raw dicts for speed)
        #    Must happen BEFORE freezing because compute_tfidf
        #    iterates the full index.
        self.index = raw_index
        self.doc_lengths = raw_doc_lengths
        self._precompute_all_vectors()

        # 5. Freeze to compact structures (RAM optimization)
        self.index = freeze_index(raw_index)
        self.doc_lengths = freeze_doc_lengths(raw_doc_lengths, self.total_docs)
        del raw_index, raw_doc_lengths

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

    def search(self, query: Union[str, List[str]], top_k: int = 10) -> List[Tuple[DocId, float]]:
        """
        Finds documents most similar to the query.
        
        Returns a list of tuples (original_doc_id, similarity_score)
        sorted by relevance. The doc_id matches the input format:
        - If indexed with Dict: returns original keys ("doc_001", "doc_002"...)
        - If indexed with List: returns integers (0, 1, 2...)
        """
        # Preprocess query if it is a raw string
        if isinstance(query, str):
            query = self.preprocessor(query)
            # Fallback: if preprocessor returned str instead of list[str], apply simple_tokenizer
            if isinstance(query, str):
                query = simple_tokenizer(query)

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
        """Packages the current state and sends it to storage.

        Compact structures are *thawed* back to regular dicts for
        serialization.  The in-memory engine keeps the compact
        versions — only the serialization copy is inflated.
        """
        if not self.storage:
            raise ValueError("No storage adapter configured in the engine.")

        # Thaw compact structures → regular dicts for storage
        serializable_index = (
            thaw_index(self.index)
            if self.index and isinstance(next(iter(self.index.values())), CompactPostings)
            else self.index
        )
        serializable_doc_lengths = (
            self.doc_lengths.to_dict()
            if isinstance(self.doc_lengths, CompactDocLengths)
            else self.doc_lengths
        )

        state = {
            "index": serializable_index,
            "total_docs": self.total_docs,
            "doc_lengths": serializable_doc_lengths,
            "doc_vectors": self.doc_vectors,
            "id_map": self.id_map,
            "id_type": self.id_type,
            "engine_name": self.name,
        }
        self.storage.save(state, name)

    def load_engine(self, name: str) -> None:
        """Loads a saved state and reconstructs the engine.

        Raw dicts from storage are frozen into compact structures
        to minimise steady-state RAM.
        """
        if not self.storage:
            raise ValueError("No storage adapter configured in the engine.")

        state = self.storage.load(name)

        raw_index = state["index"]
        self.total_docs = state["total_docs"]
        raw_doc_lengths = state["doc_lengths"]
        raw_doc_vectors = state.get("doc_vectors", {})
        raw_id_map = state.get("id_map", {i: i for i in range(self.total_docs)})
        self.id_type = state.get("id_type", "none")

        # Normalize keys to int (JSON deserializes dict keys as str)
        self.id_map = {int(k): v for k, v in raw_id_map.items()}
        self.doc_vectors = {int(k): v for k, v in raw_doc_vectors.items()}

        # Freeze to compact structures
        self.index = freeze_index(raw_index)
        self.doc_lengths = freeze_doc_lengths(raw_doc_lengths, self.total_docs)
        del raw_index, raw_doc_lengths