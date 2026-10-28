from math import log, sqrt
from typing import Any, List, Dict, Tuple, Optional, Union
from .base import BaseEngine, DocId

# import utils functions 
from ..utils.index.core import build_index as build_idx_func
from ..utils.index.stats import get_doc_len, compute_idf
from ..utils.math.core import sort_results
from ..utils.nlp import SimpleTokenizer
from ..utils.compact import (
    CompactPostings,
    CompactDocLengths,
    freeze_index,
    thaw_index,
    freeze_doc_lengths,
)
from ..utils.mmap_storage import (
    save_yny, open_yny, YnyHandle,
    MmapIdMap, MmapDocLengths, LazyIndex,
)
from ..utils.parallel import parallel_preprocess
from ..exceptions import YenyEmptyCorpusError

class CoreEngine(BaseEngine):
    """
    The heart of Yeny.
    Uses pure Python dictionaries and math for reliable, dependency-free searching.
    """

    # CoreEngine defaults to WordTokenizer (inherited from BaseEngine fallback)
    _default_preprocessor = None  # → falls through to WordTokenizer in BaseEngine

    def __init__(self, storage: Optional[Any] = None, preprocessor: Optional[Any] = None):
        super().__init__(storage=storage, preprocessor=preprocessor)
        # Store only L2 norms — full vectors are computed on-the-fly
        self.doc_norms: Dict[int, float] = {}
        self._yny_handle: Optional[YnyHandle] = None

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
           raise YenyEmptyCorpusError("Cannot index data: the corpus is empty.")
        
        self.total_docs = len(texts)
        if self.total_docs == 0:
            return

        # 1. Preprocess with the configured preprocessor.
        tokenized = parallel_preprocess(
            texts, self.preprocessor, SimpleTokenizer(),
        )

        # 2. Build compact inverted index directly
        self.index = build_idx_func(tokenized)

        # 3. Calculate document lengths for TF normalization
        raw_doc_lengths = get_doc_len(self.index, self.total_docs)
        self.doc_lengths = raw_doc_lengths

        # 4. Pre-calculate L2 norms of TF-IDF vectors
        self._precompute_norms()

        # 5. Freeze doc_lengths to compact structure
        self.doc_lengths = freeze_doc_lengths(raw_doc_lengths, self.total_docs)
        del raw_doc_lengths

    def _precompute_norms(self, start_id: int = 0) -> None:
        """Compute L2 norms of TF-IDF vectors.  O(Σ|posting entries|).

        Instead of iterating docs x vocab (quadratic), this walks each
        posting list once, accumulating squared TF-IDF scores per doc.
        Only the scalar norm is stored — full vectors are computed
        on-the-fly during search.

        Args:
            start_id: Only compute norms for doc_ids >= start_id
                (used by incremental ``add_documents``).
        """
        norm_sq: Dict[int, float] = {}
        for word, postings in self.index.items():
            idf = compute_idf(word, self.index, self.total_docs)
            for doc_id, freq in postings.items():
                if doc_id < start_id:
                    continue
                dl = self.doc_lengths.get(doc_id, 0)
                if dl == 0:
                    continue
                tf = freq / dl
                score = tf * idf
                if doc_id in norm_sq:
                    norm_sq[doc_id] += score * score
                else:
                    norm_sq[doc_id] = score * score
        for doc_id, sq in norm_sq.items():
            self.doc_norms[doc_id] = sqrt(sq)

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
            # Fallback: if preprocessor returned str instead of list[str], apply SimpleTokenizer
            if isinstance(query, str):
                query = SimpleTokenizer()(query)

        if not query or not self.index:
            return []

        # 1. Build the query vector (Query Vector)
        # For the query, we use a simplified TF-IDF based on corpus stats
        query_vector = self._build_query_vector(query)
        if not query_vector:
            return []

        # 2. Find candidate documents
        # (Only those that share at least one word with the query)
        candidate_ids = set()
        for token in query_vector:
            if token in self.index:
                candidate_ids.update(self.index[token].keys())

        # Pre-compute query norm (once per search)
        query_norm = sqrt(sum(v * v for v in query_vector.values()))
        if query_norm == 0:
            return []

        # 3. On-the-fly cosine similarity using pre-stored doc norms
        scores = {}
        for doc_id in candidate_ids:
            doc_norm = self.doc_norms.get(doc_id, 0.0)
            if doc_norm == 0:
                continue
            # Dot product: only iterate query terms (small)
            dot = 0.0
            for term, q_score in query_vector.items():
                postings = self.index.get(term)
                if postings is None:
                    continue
                freq = postings.get(doc_id, 0)
                if freq == 0:
                    continue
                dl = self.doc_lengths.get(doc_id, 0)
                if dl == 0:
                    continue
                tf = freq / dl
                idf = compute_idf(term, self.index, self.total_docs)
                dot += q_score * (tf * idf)
            if dot > 0:
                scores[doc_id] = dot / (query_norm * doc_norm)

        # 4. Sort and get top results (still using internal indices)
        internal_results = sort_results(scores, limit=top_k)

        # 5. Map internal indices back to original document IDs
        # (skip tombstoned entries if present).
        mapped: List[Tuple[DocId, float]] = []
        for doc_id, score in internal_results:
            ext_id = self.id_map.get(doc_id)
            if ext_id is None:
                continue
            mapped.append((ext_id, score))
        return mapped

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

        When the storage backend is :class:`MetadataStorage`, only
        lightweight metadata (total_docs, id_type, engine_name) is
        written — heavy index data is skipped because it lives in
        ``.yny`` files.

        Otherwise, compact structures are *thawed* back to regular dicts for
        serialization.  The in-memory engine keeps the compact
        versions — only the serialization copy is inflated.
        """
        if not self.storage:
            raise ValueError("No storage adapter configured in the engine.")

        from ..storage.metadata_storage import MetadataStorage
        if isinstance(self.storage, MetadataStorage):
            state = {
                "total_docs": self.total_docs,
                "id_type": self.id_type,
                "engine_name": self.name,
            }
            self.storage.save(state, name)
            return

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
            "doc_norms": self.doc_norms,
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
        raw_id_map = state.get("id_map", {i: i for i in range(self.total_docs)})
        self.id_type = state.get("id_type", "none")

        # Normalize keys to int (JSON deserializes dict keys as str)
        self.id_map = {int(k): v for k, v in raw_id_map.items()}

        # Freeze to compact structures
        self.index = freeze_index(raw_index)
        self.doc_lengths = freeze_doc_lengths(raw_doc_lengths, self.total_docs)
        del raw_index, raw_doc_lengths

        # Load norms (new format) or recompute from old doc_vectors
        raw_norms = state.get("doc_norms")
        if raw_norms:
            self.doc_norms = {int(k): float(v) for k, v in raw_norms.items()}
        else:
            raw_vecs = state.get("doc_vectors", {})
            if raw_vecs:
                self.doc_norms = {
                    int(k): sqrt(sum(s * s for s in v.values()))
                    for k, v in raw_vecs.items()
                }
            else:
                self._precompute_norms()

    # Mmap-backed structures promotion

    def _ensure_mutable(self) -> None:
        """Promote mmap-backed read-only structures to mutable containers.

        After ``load_mmap()`` the engine's ``id_map``, ``doc_lengths``
        and ``index`` are backed by read-only memoryviews.  This method
        materialises them into regular Python dicts so that
        ``add_documents()`` / ``remove_documents()`` can mutate safely.
        """
        if isinstance(self.id_map, MmapIdMap):
            self.id_map = self.id_map.to_dict()
        if isinstance(self.doc_lengths, (MmapDocLengths, CompactDocLengths)):
            self.doc_lengths = (
                self.doc_lengths.to_dict()
                if hasattr(self.doc_lengths, 'to_dict')
                else dict(self.doc_lengths.items())
            )
        if isinstance(self.index, LazyIndex):
            # Materialise AND convert MmapPostings → CompactPostings
            # so the mmap file can be fully released (critical on Windows).
            from ..utils.mmap_storage import MmapPostings
            raw = dict(self.index.items())
            self.index = {
                token: (CompactPostings.from_dict(dict(p.items()))
                        if isinstance(p, MmapPostings) else p)
                for token, p in raw.items()
            }
        if self._yny_handle is not None:
            self._yny_handle.close()
            self._yny_handle = None

    # Incremental indexing

    def add_documents(self, new_docs: Union[List[str], Dict[Any, str]]) -> None:
        """Incrementally add new documents to the existing index.

        Builds a delta, merges it into the compact index, and
        recomputes TF-IDF vectors **only** for the new documents.
        Existing vectors are kept as-is — their IDF component becomes
        slightly stale but remains a good approximation until the next
        full rebuild.

        Args:
            new_docs: New documents to add (same formats as
                ``build_index``).
        """
        self._ensure_mutable()

        start_id = self.total_docs

        # Normalize
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

        tokenized_new = parallel_preprocess(
            new_texts, self.preprocessor, SimpleTokenizer(),
        )

        # Build delta index
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
                self.index[token] = CompactPostings.from_dict(new_postings)
            else:
                merged = existing.to_dict() if isinstance(existing, CompactPostings) else dict(existing)
                merged.update(new_postings)
                self.index[token] = CompactPostings.from_dict(merged)

        # Extend doc_lengths
        for doc_id, length in new_doc_lengths.items():
            self.doc_lengths[doc_id] = length

        self.total_docs += len(new_texts)

        # Compute L2 norms ONLY for new documents
        self._precompute_norms(start_id=start_id)

    def remove_documents(self, doc_ids: List[Any]) -> int:
        """Remove documents by original IDs (tombstone + postings purge).

        Purges postings, deletes TF-IDF vectors, and tombstones
        id_map entries.

        Args:
            doc_ids: Original document IDs to remove.

        Returns:
            Number of documents removed.
        """
        if not doc_ids or not self.index:
            return 0

        self._ensure_mutable()

        target = {str(v) for v in doc_ids}
        remove_internal = {
            int(i)
            for i, ext in self.id_map.items()
            if ext is not None and str(ext) in target
        }
        if not remove_internal:
            return 0

        # Purge from postings
        for token in list(self.index.keys()):
            postings = self.index[token]
            if isinstance(postings, CompactPostings):
                p_dict = postings.to_dict()
            else:
                p_dict = dict(postings)

            for rid in remove_internal:
                p_dict.pop(rid, None)

            if p_dict:
                self.index[token] = CompactPostings.from_dict(p_dict)
            else:
                del self.index[token]

        # Tombstone metadata + remove norms
        for rid in remove_internal:
            self.doc_lengths[rid] = 0
            self.id_map[rid] = None
            self.doc_norms.pop(rid, None)

        return len(remove_internal)

    # Binary persistence (.yny) 

    def save_binary(self, path: str) -> None:
        """Serialise this engine to a ``.yny`` file (including doc_norms)."""
        save_yny(path, self)

    def load_mmap(self, path: str) -> None:
        """Load engine state from a ``.yny`` file using memory-mapped I/O.

        The inverted index, doc_lengths, and id_map are backed by
        zero-copy mmap views.  ``doc_norms`` are loaded from the
        .yny header or recomputed from the index.
        """
        self.close_mmap()
        handle = open_yny(path)
        self._yny_handle = handle
        self.index = handle.index
        self.doc_lengths = handle.doc_lengths
        self.total_docs = handle.total_docs
        self.id_map = handle.id_map
        self.id_type = handle.id_type

        # Load doc_norms from .yny if stored, otherwise recompute
        stored_norms = getattr(handle, "doc_norms", None)
        if stored_norms:
            self.doc_norms = stored_norms
        else:
            self._ensure_mutable()
            self._precompute_norms()

    def close_mmap(self) -> None:
        """Release the mmap handle and OS file descriptor."""
        if self._yny_handle is not None:
            self._yny_handle.close()
            self._yny_handle = None
            self.index = {}
            self.doc_lengths = None
            self.id_map = {}
            self.doc_norms = {}