import polars as pl
from ..decorators import corpus_input
from ..nlp import WordTokenizer

# Build index functions, optimized with Polars for large corpora

@corpus_input(WordTokenizer())
def build_index_plus(tokenized_corpus: list[list[str]], as_pure_dict: bool = False) -> dict[str, dict[int, int]]:
        """
        Builds index (inverted ways) using Polars for parallel processing.
        
        Optimized for massive corpora where Python's GIL becomes a bottleneck.
        Polars processes in parallel chunks using all CPU cores.
        
        Example:
            corpus = [["hello", "world", "hello"], ["python", "world"]]
            result = {
                "hello": {0: 2},      # "hello" appears 2 times in doc 0
                "world": {0: 1, 1: 1}, # "world" appears 1 time in doc 0 and 1
                "python": {1: 1}      # "python" appears 1 time in doc 1
            }
        
        Note: For small corpora (< 100k docs), build_index is faster due to Polars overhead.
        """
        # Early return for empty corpus - avoid unnecessary DataFrame creation
        if not tokenized_corpus:
            return {}
        
        # Building separate lists is faster than list of dicts (avoids dict allocation overhead per row)
        # Using list comprehension with enumerate is O(n) where n = total tokens across all docs
        doc_ids: list[int] = []
        tokens: list[str] = []
        
        for doc_id, doc_tokens in enumerate(tokenized_corpus):
            for token in doc_tokens:
                doc_ids.append(doc_id)
                tokens.append(token)
        
        # Early return if corpus has no tokens (all empty documents)
        if not tokens:
            return {}
        
        # Create DataFrame from columnar data - Polars native format, zero-copy when possible
        # This is significantly faster than row-wise construction with list of dicts
        df = pl.DataFrame({
            "doc_id": doc_ids,
            "token": tokens
        })
        
        # Lazy evaluation + group_by is where Polars shines:
        # - Lazy mode enables query optimization (predicate pushdown, projection pruning)
        # - group_by uses parallel hashing across all CPU cores
        # - len() is optimized to avoid materializing intermediate results
        counts = (
            df.lazy()
            .group_by(["token", "doc_id"])
            .agg(pl.len().alias("count"))
            .collect()
        )
        
        # Convert to nested dict structure using Polars native methods
        # partition_by splits DataFrame by token - returns list of DataFrames, one per unique token
        # This is faster than iter_rows() which has Python overhead per row
        index: dict[str, dict[int, int]] = {}
        
        for token_df in counts.partition_by("token", maintain_order=False, include_key=True):
            # First row contains the token (all rows in this partition share it)
            token = token_df["token"][0]
            # to_dict returns {col_name: list_of_values} - we zip doc_ids with counts
            data = token_df.select(["doc_id", "count"]).to_dict(as_series=False)
            index[token] = dict(zip(data["doc_id"], data["count"]))
        
        # reminder: unlike build_index, this returns a normal dict (not defaultdict)
        # accessing with .get(word, {}) still works correctly for missing keys
        return index