from typing import Any, Callable, List, Dict, Tuple, Optional, Union
from .base import BaseEngine, DocId

from ..utils.index.core import build_index as build_idx_func
from ..utils.index.stats import get_doc_len
from ..utils.math.core import sort_results
from ..utils.nlp import simple_tokenizer, char_ngram_tokenizer
from ..utils.compact import (
    CompactPostings,
    CompactDocLengths,
    freeze_index,
    thaw_index,
    freeze_doc_lengths,
)
from ..utils.parallel import parallel_preprocess
from ..exceptions import LucisEmptyCorpusError


def _default_lite_preprocessor(text: str) -> list[str]:
    """Default preprocessor for LiteEngine: lowercase + char 3-grams."""
    return char_ngram_tokenizer(3)(text.lower())


class LiteEngine(BaseEngine):
    """
    Lightweight search engine based on normalized Term Frequency.

    Uses only the inverted index and document lengths — no TF-IDF vectors,
    no cosine similarity, no IDF.  This makes it significantly lighter
    on both disk and RAM compared to CoreEngine and is a powerful solution for
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

    # LiteEngine defaults to char 3-gram tokenizer with lowercase
    _default_preprocessor: Callable = staticmethod(_default_lite_preprocessor)

    def __init__(self, storage: Optional[Any] = None, preprocessor: Optional[Any] = None):
        super().__init__(storage=storage, preprocessor=preprocessor)

    @property
    def name(self) -> str:
        return "LiteEngine"

    def build_index(self, corpus: Union[List[str], Dict[str, str]]) -> None:
        """
        Builds the inverted index and document lengths.

        After building with fast ``defaultdict``s, the structures are
        *frozen* into compact ``array.array``-backed objects that use
        ~12× less RAM per posting entry.
        """
        texts, self.id_map = self._normalize_corpus(corpus)

        if not texts:
            raise LucisEmptyCorpusError("Cannot index data: the corpus is empty.")

        self.total_docs = len(texts)
        if self.total_docs == 0:
            return

        # 1. Preprocess with the configured preprocessor.
        #    Uses ProcessPoolExecutor when corpus ≥ 500 docs and the
        #    preprocessor is picklable; falls back to sequential otherwise.
        tokenized = parallel_preprocess(
            texts, self.preprocessor, simple_tokenizer,
        )

        # 2. Build inverted index with utils function (fast defaultdict pass)
        raw_index = build_idx_func(tokenized)

        # 3. Calculate document lengths (still using raw dicts)
        raw_doc_lengths = get_doc_len(raw_index, self.total_docs)

        # 4. Freeze to compact structures (RAM optimization)
        self.index = freeze_index(raw_index)
        self.doc_lengths = freeze_doc_lengths(raw_doc_lengths, self.total_docs)

        # Let the raw dicts be garbage-collected immediately
        del raw_index, raw_doc_lengths

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
        #    Uses CompactPostings.get() — O(log n) binary search per lookup,
        #    but ~12× less RAM and better cache locality than dict.
        _EMPTY = CompactPostings.from_dict({})
        scores: Dict[int, float] = {}
        for doc_id in candidate_ids:
            doc_len = self.doc_lengths.get(doc_id, 0)
            if doc_len == 0:
                continue

            score = 0.0
            for token in query:
                tf = self.index.get(token, _EMPTY).get(doc_id, 0)
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

        Compact structures are *thawed* back to regular dicts for
        JSON serialization.  The in-memory engine keeps the compact
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
            "id_map": self.id_map,
            "id_type": self.id_type,
            "engine_name": self.name,
        }
        self.storage.save(state, name)

    def load_engine(self, name: str) -> None:
        """
        Loads a saved state and reconstructs the engine.

        Raw dicts from storage are immediately frozen into compact
        structures to minimise steady-state RAM.
        """
        if not self.storage:
            raise ValueError("No storage adapter configured in the engine.")

        state = self.storage.load(name)

        raw_index = state["index"]
        self.total_docs = state["total_docs"]
        raw_doc_lengths = state["doc_lengths"]
        raw_id_map = state.get("id_map", {i: i for i in range(self.total_docs)})
        self.id_type = state.get("id_type", "none")

        # Normalize id_map keys to int (JSON deserializes keys as str)
        self.id_map = {int(k): v for k, v in raw_id_map.items()}

        # Freeze to compact structures
        self.index = freeze_index(raw_index)
        self.doc_lengths = freeze_doc_lengths(raw_doc_lengths, self.total_docs)
        del raw_index, raw_doc_lengths

    # Incremental indexing

    def add_documents(self, new_docs: Union[List[str], Dict[Any, str]]) -> None:
        """
        Incrementally add new documents to the existing index.

        Builds a temporary dict-based delta, merges it into the
        existing compact postings, and re-freezes.  Because deltas
        are typically small (<1 % of the corpus), the temporary RAM
        spike is negligible.

        Args:
            new_docs: New documents to add. Supports the same formats
                as ``build_index``:

                - ``List[str]``: IDs continue from ``self.total_docs``.
                - ``Dict[Any, str]``: Preserves original keys.

        Note:
            Call ``persist()`` or ``Lucis.save()`` afterwards to
            persist the updated index to storage.
        """
        # Determine the starting internal id for new documents
        start_id = self.total_docs

        # Normalize new documents
        if isinstance(new_docs, dict):
            new_texts = list(new_docs.values())
            new_keys = list(new_docs.keys())
            for i, key in enumerate(new_keys):
                self.id_map[start_id + i] = key
            if self.id_type == "none":
                self.id_type = "custom"
        elif isinstance(new_docs, list):
            new_texts = new_docs
            for i in range(len(new_texts)):
                self.id_map[start_id + i] = start_id + i
            if self.id_type == "none":
                self.id_type = "sequential"
        else:
            raise ValueError("new_docs must be a List[str] or Dict[Any, str].")

        if not new_texts:
            return

        # Preprocess new documents (parallel when large enough)
        tokenized_new = parallel_preprocess(
            new_texts, self.preprocessor, simple_tokenizer,
        )

        # Build a small delta index (regular dicts — fast for mutation)
        delta: Dict[str, Dict[int, int]] = {}
        new_doc_lengths: Dict[int, int] = {}

        for i, tokens in enumerate(tokenized_new):
            doc_id = start_id + i
            new_doc_lengths[doc_id] = len(tokens)
            for token in tokens:
                if token not in delta:
                    delta[token] = {}
                delta[token][doc_id] = delta[token].get(doc_id, 0) + 1

        # Merge delta into existing compact index
        for token, new_postings in delta.items():
            existing = self.index.get(token)
            if existing is None:
                # Brand-new token — freeze directly
                self.index[token] = CompactPostings.from_dict(new_postings)
            else:
                # Merge: thaw existing → update → re-freeze
                merged = existing.to_dict() if isinstance(existing, CompactPostings) else dict(existing)
                merged.update(new_postings)
                self.index[token] = CompactPostings.from_dict(merged)

        # Extend compact doc_lengths
        for doc_id, length in new_doc_lengths.items():
            self.doc_lengths[doc_id] = length

        self.total_docs += len(new_texts)
