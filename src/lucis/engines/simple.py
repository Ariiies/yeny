from typing import Any, List, Dict, Tuple, Optional, Union
from .base import BaseEngine, DocId

from ..utils.index.core import build_index as build_idx_func
from ..utils.index.stats import get_doc_len
from ..utils.math.core import sort_results
from ..utils.nlp import simple_tokenizer
from ..exceptions import LucisEmptyCorpusError


class SimpleEngine(BaseEngine):
    """
    Lightweight search engine based on normalized Term Frequency.

    Uses only the inverted index and document lengths — no TF-IDF vectors,
    no cosine similarity, no IDF.  This makes it significantly lighter
    on both disk and RAM compared to CoreEngine and is a powefull solution for
    some specific cases.

    Scoring formula:
        score(d, Q) = Σ  tf(t, d) / |d|   for each query term t
    
    Where:
        tf(t, d) = raw count of term t in document d
        |d|      = total number of tokens in document d

    Best suited for:
        - Small to medium corpora where speed matters more than precision.
        - Environments with limited RAM.
        - Use cases where IDF weighting is unnecessary.
    """

    def __init__(self, storage: Optional[Any] = None, preprocessor: Optional[Any] = None):
        super().__init__(storage=storage, preprocessor=preprocessor)

    @property
    def name(self) -> str:
        return "SimpleEngine"

    def build_index(self, corpus: Union[List[str], Dict[str, str]]) -> None:
        """
        Builds the inverted index and document lengths.
        """
        texts, self.id_map = self._normalize_corpus(corpus)

        if not texts:
            raise LucisEmptyCorpusError("Cannot index data: the corpus is empty.")

        self.total_docs = len(texts)
        if self.total_docs == 0:
            return

        # 1. Preprocess with the configured preprocessor.
        tokenized = []
        for doc in texts:
            result = self.preprocessor(doc)
            tokenized.append(simple_tokenizer(result) if isinstance(result, str) else result)

        # 2. Build inverted index with utils function (Core)
        self.index = build_idx_func(tokenized)

        # 3. Calculate document lengths for TF normalization
        self.doc_lengths = get_doc_len(self.index, self.total_docs)

    def search(self, query: Union[str, List[str]], top_k: int = 10) -> List[Tuple[DocId, float]]:
        """
        Finds documents matching the query using normalized term frequency.

        For each candidate document, the score is the sum of
        (term_count / doc_length) for every query term found in it.
        """
        # Preprocess query if it is a raw string
        if isinstance(query, str):
            query = self.preprocessor(query)
            if isinstance(query, str):
                query = simple_tokenizer(query)

        if not query or not self.index:
            return []

        # 1. Find candidate documents (only those sharing at least one token)
        candidate_ids: set = set()
        for token in query:
            if token in self.index:
                candidate_ids.update(self.index[token].keys())

        if not candidate_ids:
            return []

        # 2. Score each candidate: Σ tf(t,d) / |d|
        scores: Dict[int, float] = {}
        for doc_id in candidate_ids:
            doc_len = self.doc_lengths.get(doc_id, 0)
            if doc_len == 0:
                continue

            score = 0.0
            for token in query:
                tf = self.index.get(token, {}).get(doc_id, 0)
                score += tf / doc_len
            
            if score > 0:
                scores[doc_id] = score

        # 3. Sort and limit
        internal_results = sort_results(scores, limit=top_k)

        # 4. Map internal indices back to original document IDs
        return [(self.id_map[doc_id], score) for doc_id, score in internal_results]

    def persist(self, name: str) -> None:
        """
        Packages the current state and sends it to storage.
        """
        if not self.storage:
            raise ValueError("No storage adapter configured in the engine.")

        state = {
            "index": self.index,
            "total_docs": self.total_docs,
            "doc_lengths": self.doc_lengths,
            "id_map": self.id_map,
            "id_type": self.id_type,
            "engine_name": self.name,
            # Explicitly empty — storage adapters handle this gracefully
        }
        self.storage.save(state, name)

    def load_engine(self, name: str) -> None:
        """
        Loads a saved state and reconstructs the engine.

        Only loads index, doc_lengths, total_docs, id_map, id_type.
        """
        if not self.storage:
            raise ValueError("No storage adapter configured in the engine.")

        state = self.storage.load(name)

        self.index = state["index"]
        self.total_docs = state["total_docs"]
        self.doc_lengths = state["doc_lengths"]
        self.id_map = state.get("id_map", {i: i for i in range(self.total_docs)})
        self.id_type = state.get("id_type", "none")
