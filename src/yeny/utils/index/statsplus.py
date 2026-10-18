"""
Statistical functions for inverted index analysis - NumPy accelerated.

Same interface as stats.py but optimized for batch operations on large corpora.
Use stats.py for small corpora or when NumPy is not available.
"""
import numpy as np
from numpy.typing import NDArray

# BATCH FREQUENCY FUNCTIONS

def compute_doc_len_plus(index: dict, total_docs: int) -> NDArray[np.int64]:
    """
    Computes document lengths as NumPy array.
    
    Returns array where lengths[doc_id] = total terms in document.
    NumPy array enables vectorized TF calculations.
    """
    lengths = np.zeros(total_docs, dtype=np.int64)
    
    for word_docs in index.values():
        for doc_id, count in word_docs.items():
            lengths[doc_id] += count
    
    return lengths


def compute_idf_plus(index: dict, total_docs: int, smooth: bool = True) -> dict[str, float]:
    """
    Pre-computes IDF for all terms in vocabulary.
    
    Returns {word: idf_score} - compute once, reuse for all TF-IDF calculations.
    This avoids redundant log computations when processing multiple documents.
    """
    idf_dict: dict[str, float] = {}
    
    for word, docs in index.items():
        df = len(docs)
        if smooth:
            idf_dict[word] = np.log((total_docs + 1) / (df + 1)) + 1
        else:
            idf_dict[word] = np.log(total_docs / df) if df > 0 else 0.0
    
    return idf_dict

# TF-IDF MATRIX FUNCTIONS

def compute_tfidf_plus(
    index: dict,
    total_docs: int,
    doc_lengths: NDArray[np.int64] | None = None,
    smooth_idf: bool = True
) -> tuple[NDArray[np.float64], list[str]]:
    """
    Builds dense TF-IDF matrix for entire corpus.
    
    Returns:
        matrix: Shape (total_docs, vocab_size) where matrix[doc_id, term_idx] = tf-idf score
        vocabulary: List of terms where vocabulary[term_idx] = word
    
    Memory: O(N * V) - use only when you need the full matrix (e.g., sklearn compatibility)
    For sparse operations, use compute_document_vector from stats.py
    """
    vocabulary = list(index.keys())
    vocab_size = len(vocabulary)
    word_to_idx = {word: idx for idx, word in enumerate(vocabulary)}
    
    # Pre-compute doc lengths if not provided
    if doc_lengths is None:
        doc_lengths = compute_doc_len_plus(index, total_docs)
    
    # Pre-compute IDF for all terms - avoids redundant log() calls
    idf_vector = np.zeros(vocab_size, dtype=np.float64)
    for idx, word in enumerate(vocabulary):
        df = len(index[word])
        if smooth_idf:
            idf_vector[idx] = np.log((total_docs + 1) / (df + 1)) + 1
        else:
            idf_vector[idx] = np.log(total_docs / df) if df > 0 else 0.0
    
    # Build TF matrix then multiply by IDF
    tf_matrix = np.zeros((total_docs, vocab_size), dtype=np.float64)
    
    for word, docs in index.items():
        term_idx = word_to_idx[word]
        for doc_id, count in docs.items():
            if doc_lengths[doc_id] > 0:
                tf_matrix[doc_id, term_idx] = count / doc_lengths[doc_id]
    
    # Element-wise multiplication: each row (doc) * idf_vector
    tfidf_matrix = tf_matrix * idf_vector
    
    return tfidf_matrix, vocabulary


def compute_sparse_tfidf_matrix(
    index: dict,
    total_docs: int,
    doc_lengths: NDArray[np.int64] | None = None,
    smooth_idf: bool = True
):
    """
    Builds scipy sparse TF-IDF matrix - memory efficient for large vocabularies.
    
    Returns:
        matrix: scipy.sparse.csr_matrix of shape (total_docs, vocab_size)
        vocabulary: List of terms
    
    Requires scipy. Falls back to dense matrix if scipy not available.
    """
    try:
        from scipy.sparse import csr_matrix, lil_matrix
    except ImportError:
        # Fallback to dense if scipy not installed
        return compute_tfidf_plus(index, total_docs, doc_lengths, smooth_idf)
    
    vocabulary = list(index.keys())
    vocab_size = len(vocabulary)
    word_to_idx = {word: idx for idx, word in enumerate(vocabulary)}
    
    if doc_lengths is None:
        doc_lengths = compute_doc_len_plus(index, total_docs)
    
    # lil_matrix is efficient for incremental construction
    tf_matrix = lil_matrix((total_docs, vocab_size), dtype=np.float64)
    
    # Pre-compute IDF
    idf_vector = np.zeros(vocab_size, dtype=np.float64)
    for idx, word in enumerate(vocabulary):
        df = len(index[word])
        if smooth_idf:
            idf_vector[idx] = np.log((total_docs + 1) / (df + 1)) + 1
        else:
            idf_vector[idx] = np.log(total_docs / df) if df > 0 else 0.0
    
    # Fill TF values - only non-zero entries
    for word, docs in index.items():
        term_idx = word_to_idx[word]
        for doc_id, count in docs.items():
            if doc_lengths[doc_id] > 0:
                tf_matrix[doc_id, term_idx] = count / doc_lengths[doc_id]
    
    # Convert to CSR for efficient arithmetic, then multiply by IDF
    tf_csr = tf_matrix.tocsr()
    # Multiply each column by its IDF value
    tfidf_matrix = tf_csr.multiply(idf_vector)
    
    return tfidf_matrix.tocsr(), vocabulary


# BATCH SIMILARITY FUNCTIONS

def batch_document_similarity(
    tfidf_matrix: NDArray[np.float64],
    doc_id: int
) -> NDArray[np.float64]:
    """
    Computes cosine similarity between one document and all others.
    
    Returns array where result[i] = similarity(doc_id, i).
    Uses NumPy broadcasting for vectorized computation.
    """
    # Get query vector
    query = tfidf_matrix[doc_id]
    query_norm = np.linalg.norm(query)
    
    if query_norm == 0:
        return np.zeros(tfidf_matrix.shape[0])
    
    # Compute all dot products at once
    dots = tfidf_matrix @ query
    
    # Compute all norms at once
    norms = np.linalg.norm(tfidf_matrix, axis=1)
    
    # Avoid division by zero
    with np.errstate(divide='ignore', invalid='ignore'):
        similarities = dots / (norms * query_norm)
        similarities = np.nan_to_num(similarities, 0.0)
    
    return similarities


def find_similar_documents(
    tfidf_matrix: NDArray[np.float64],
    doc_id: int,
    top_k: int = 10
) -> list[tuple[int, float]]:
    """
    Finds most similar documents to a given document.
    
    Returns [(doc_id, score), ...] sorted by similarity descending.
    Excludes the query document itself.
    """
    similarities = batch_document_similarity(tfidf_matrix, doc_id)
    
    # Set self-similarity to -1 to exclude from results
    similarities[doc_id] = -1.0
    
    # Get top-k indices using argpartition (faster than full sort for large arrays)
    if top_k < len(similarities):
        top_indices = np.argpartition(similarities, -top_k)[-top_k:]
        top_indices = top_indices[np.argsort(similarities[top_indices])[::-1]]
    else:
        top_indices = np.argsort(similarities)[::-1]
    
    return [(int(idx), float(similarities[idx])) for idx in top_indices[:top_k]]
