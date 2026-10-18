"""
SearchMixin — Search orchestration and shard preloading.

Provides the ``search()`` method that wraps raw engine results into
structured ``SearchResponse`` objects, and the ``preload_shards()``
helper for warming lazy-loaded shards before a query.
"""
import time
from typing import List, Optional, Union

from ..models.search import SearchResult, SearchResponse
from ..utils.nlp import SimpleTokenizer
from ..core.shard import normalize_to_shard_key, shard_key_in_range
from ..exceptions import YenyEngineError


class SearchMixin:
    """Mixin that provides search orchestration and shard preloading."""

    def search(
        self,
        query: Union[str, List[str]],
        top_k: int = 10,
        since: Optional[str] = None,
        until: Optional[str] = None,
    ) -> SearchResponse:
        """
        Searches the indexed corpus for documents matching the query.

        The engine returns raw tuples; Yeny wraps them in a SearchResponse
        with full context: query, tokens, timing, and structured results.

        When the index is sharded (temporal partitioning), ``since`` and
        ``until`` restrict the search to shards within the specified range.
        Without these parameters, **all** shards are searched.

        Args:
            query: A search string ("love python") or pre-tokenized list (["love", "python"]).
            top_k: Maximum number of results to return.
            since: Start of the temporal range (inclusive).  Accepts:
                - Shard keys: ``"2026_01"``
                - ISO dates: ``"2026-01-15"``
                - Year-month: ``"2026-01"``
                Ignored for non-sharded indices.
            until: End of the temporal range (inclusive).  Same formats.

        Returns:
            SearchResponse with ranked results and search metadata.

        Example:
            response = yn.search("programación python", top_k=5)
            print(response.total_results)        # 5
            print(response.results[0].doc_id)     # "doc_001"
            print(response.results[0].score)      # 0.3903
            print(response.search_time_ms)        # 2.31
            print(response.to_dict())             # JSON-ready dict

        Example — time-scoped::

            response = yn.search("invoice", since="2026-01", until="2026-02")
        """
        if not self._is_indexed:
            raise YenyEngineError(
                engine_name=self.engine.name,
                detail="No index built yet. Use .index(data), .from_dict(), or .from_list() first."
            )

        # Preserve the original query before tokenization
        original_query = query

        # Preprocess + tokenize to capture the tokens for the response
        if isinstance(query, str):
            processed = self.preprocessor(query)
            # Fallback: if preprocessor returned str instead of list[str], apply SimpleTokenizer
            tokens = SimpleTokenizer()(processed) if isinstance(processed, str) else processed
        else:
            tokens = list(query)

        # Time the search (the core computation)
        start = time.perf_counter()

        if self._shard_manager:
            # ── Sharded search: query relevant shards and merge ──
            raw_results = self._shard_manager.search(
                tokens, top_k=top_k, since=since, until=until,
            )
            elapsed_ms = (time.perf_counter() - start) * 1000

            # raw_results: [(doc_id, score, shard_key), ...]
            results = [
                SearchResult(
                    doc_id=doc_id, score=round(score, 6),
                    rank=rank, shard_key=shard_key,
                )
                for rank, (doc_id, score, shard_key) in enumerate(raw_results, start=1)
            ]

            # Count shards actually queried
            since_key = normalize_to_shard_key(since)
            until_key = normalize_to_shard_key(until)
            shards_searched = sum(
                1 for k in self._shard_manager.shards
                if shard_key_in_range(k, since_key, until_key)
            )

            return SearchResponse(
                query=original_query,
                tokens=tokens,
                engine=self.engine.name,
                total_results=len(results),
                search_time_ms=round(elapsed_ms, 2),
                results=results,
                shards_searched=shards_searched,
                total_shards=len(self._shard_manager.shards),
            )
        else:
            # Single-engine search (non-sharded)
            raw_results = self.engine.search(tokens, top_k=top_k)
            elapsed_ms = (time.perf_counter() - start) * 1000

            results = [
                SearchResult(doc_id=doc_id, score=round(score, 6), rank=rank)
                for rank, (doc_id, score) in enumerate(raw_results, start=1)
            ]

            return SearchResponse(
                query=original_query,
                tokens=tokens,
                engine=self.engine.name,
                total_results=len(results),
                search_time_ms=round(elapsed_ms, 2),
                results=results,
            )

    def preload_shards(
        self,
        since: Optional[str] = None,
        until: Optional[str] = None,
        n_recent: Optional[int] = None,
    ) -> List[str]:
        """Explicitly warm shards into memory without blocking searches.

        Only useful when ``max_loaded_shards > 0`` was passed to the
        constructor (lazy mode).  Call this before running a query against
        historical data so the shards are ready in RAM.

        Args:
            since: Load shards at or after this key / ISO date (e.g. ``"2025_01"``).
            until: Load shards at or before this key / ISO date.
            n_recent: Load only the *n_recent* most recent qualifying shards.
                If ``None``, loads all matching shards (subject to the
                LRU eviction limit).

        Returns:
            List of shard keys that were newly loaded into memory.

        Example::

            yn = Yeny(name="email_idx", ...,
                        options=YenyOptions(max_loaded_shards=6))
            # After load(), only 6 most recent shards are in RAM.
            # To also query 2024 data:
            yn.preload_shards(since="2024_01", until="2024_12")
        """
        if self._shard_manager is None:
            return []
        return self._shard_manager.preload_shards(since=since, until=until, n_recent=n_recent)
