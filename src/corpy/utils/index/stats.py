"""
Statistical functions for inverted index analysis.

All functions expect an index with structure: {word: {doc_id: count, ...}, ...}
This is the format returned by both build_index and build_index_plus.
"""
from math import log

# RAW FREQUENCY FUNCTIONS

# function to get term frequency
def get_tf_count(word: str, doc_id: int, index: dict) -> int:
    """Raw count of word in document. Use compute_tf for normalized version."""
    # Chained .get() is O(1) and avoids KeyError
    return index.get(word, {}).get(doc_id, 0)

# function to get document frequency
def get_df_count(word: str, index: dict) -> int:
    """Counts documents containing the word - this is the 'df' in IDF."""
    return len(index.get(word, {}))

# function to get collection frequency
def get_cf_count(word: str, index: dict) -> int:
    """Total word occurrences across entire corpus."""
    return sum(index.get(word, {}).values())


# HELPER FUNCTIONS

# function to get document lengths
def get_doc_len(index: dict, total_docs: int) -> dict[int, int]:
    """
    Reconstructs document lengths from inverted index.
    
    Pre-compute once, reuse for all TF calculations.
    reminder: This is O(V*avg_df) - call once and cache the result
    """
    # Initialize all docs with 0 - handles empty documents
    lengths: dict[int, int] = {i: 0 for i in range(total_docs)}
    
    # Each word contributes its count to each document it appears in
    for word_docs in index.values():
        for doc_id, count in word_docs.items():
            lengths[doc_id] += count
    
    return lengths

# TF-IDF FUNCTIONS

def compute_tf(word: str, doc_id: int, index: dict, doc_lengths: dict[int, int]) -> float:
    """
    Normalized Term Frequency: tf(t,d) = count(t,d) / |d|
    
    Prevents bias towards longer documents.
    """
    raw_tf = get_tf_count(word, doc_id, index)
    
    if raw_tf == 0:
        return 0.0
    
    doc_length = doc_lengths.get(doc_id, 0)
    
    # Guard against empty documents (defensive programming)
    if doc_length == 0:
        return 0.0
    
    return raw_tf / doc_length


def compute_idf(word: str, index: dict, total_docs: int, smooth: bool = True) -> float:
    """
    Inverse Document Frequency - measures word rarity.
    
    Smoothed: idf(t) = log((N + 1) / (df(t) + 1)) + 1 (recommended)
    Standard: idf(t) = log(N / df(t))
    """
    df = get_df_count(word, index)
    
    if smooth:
        # sklearn's default - numerically stable, always positive
        return log((total_docs + 1) / (df + 1)) + 1
    
    # Standard IDF - can be problematic with edge cases
    if df == 0:
        return 0.0
    
    return log(total_docs / df)


def compute_tfidf(
    word: str, 
    doc_id: int, 
    index: dict, 
    doc_lengths: dict[int, int], 
    total_docs: int,
    smooth_idf: bool = True
) -> float:
    """
    TF-IDF score: tf_idf(t,d) = tf(t,d) * idf(t)
    
    High score = frequent in doc AND rare across corpus.
    """
    tf = compute_tf(word, doc_id, index, doc_lengths)
    
    # Early return - if word not in doc, no need to compute IDF
    if tf == 0.0:
        return 0.0
    
    idf = compute_idf(word, index, total_docs, smooth=smooth_idf)
    
    return tf * idf

"""
this function creates a sparse TF-IDF vector for a given document
Note: this function is potentially weighty in computation if vocabulary is large
    but is memory efficient since it only stores non-zero entries.
    in some test cases this function can be heavy in computation
"""
def compute_document_vector(
    doc_id: int, 
    index: dict, 
    doc_lengths: dict[int, int], 
    total_docs: int,
    smooth_idf: bool = True
) -> dict[str, float]:
    """
    Creates sparse TF-IDF vector for document similarity/search operations.
    
    Returns {word: tf_idf_score} - only non-zero entries for memory efficiency.
    Use with sparse_cosine_similarity from math.py for document comparison.
    """
    vector: dict[str, float] = {}
    
    # Iterate vocabulary - check `doc_id in docs` is O(1) with dict hashing
    for word, docs in index.items():
        if doc_id in docs:
            score = compute_tfidf(word, doc_id, index, doc_lengths, total_docs, smooth_idf)
            vector[word] = score
    
    return vector