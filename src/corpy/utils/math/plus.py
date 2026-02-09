"""
Math utilities for vector operations - NumPy accelerated.

Same interface as core.py but optimized for large-scale operations.
Use core.py for small vectors or when NumPy is not available.
"""
import numpy as np
from numpy.typing import NDArray

# DENSE VECTOR FUNCTIONS (NumPy accelerated)

def dot_product_plus(vec_a: NDArray, vec_b: NDArray) -> float:
    """Dot product using NumPy - SIMD optimized, handles large vectors efficiently."""
    return float(np.dot(vec_a, vec_b))


def vector_norm_plus(vec: NDArray) -> float:
    """L2 norm using NumPy's optimized BLAS routines."""
    return float(np.linalg.norm(vec))


def cosine_similarity_plus(vec_a: NDArray, vec_b: NDArray) -> float:
    """Cosine similarity - fully vectorized, no Python loops."""
    norm_a = np.linalg.norm(vec_a)
    norm_b = np.linalg.norm(vec_b)
    
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    
    return float(np.dot(vec_a, vec_b) / (norm_a * norm_b))


def argsort_descending_plus(values: NDArray) -> NDArray[np.intp]:
    """Returns indices sorted by descending value - NumPy's optimized quicksort."""
    return np.argsort(values)[::-1]


def batch_cosine_similarity_plus(
    query_vec: NDArray, 
    doc_matrix: NDArray
) -> NDArray[np.float64]:
    """
    Cosine similarity between query and all docs in matrix.
    
    Uses matrix multiplication for O(1) Python overhead regardless of corpus size.
    doc_matrix shape: (n_docs, n_features)
    """
    query_norm = np.linalg.norm(query_vec)
    
    if query_norm == 0.0:
        return np.zeros(doc_matrix.shape[0])
    
    # All dot products in one matrix-vector multiplication
    dots = doc_matrix @ query_vec
    
    # All norms at once
    norms = np.linalg.norm(doc_matrix, axis=1)
    
    # Safe division
    with np.errstate(divide='ignore', invalid='ignore'):
        similarities = dots / (norms * query_norm)
        similarities = np.nan_to_num(similarities, 0.0)
    
    return similarities


# PAIRWISE SIMILARITY FUNCTIONS

def pairwise_cosine_similarity_plus(matrix: NDArray) -> NDArray[np.float64]:
    """
    Computes cosine similarity between all pairs of vectors.
    
    Returns (n_docs, n_docs) similarity matrix.
    Much faster than nested loops: O(n²) but with NumPy BLAS.
    """
    # Normalize each row to unit length
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    
    # Avoid division by zero
    norms = np.where(norms == 0, 1, norms)
    normalized = matrix / norms
    
    # Similarity matrix is just dot product of normalized vectors
    return normalized @ normalized.T


def top_k_similar_plus(
    similarity_matrix: NDArray,
    doc_id: int,
    top_k: int = 10
) -> list[tuple[int, float]]:
    """
    Gets top_k most similar documents from pre-computed similarity matrix.
    
    Uses argpartition for O(n) instead of O(n log n) full sort.
    """
    similarities = similarity_matrix[doc_id].copy()
    similarities[doc_id] = -1.0  # Exclude self
    
    if top_k < len(similarities):
        # argpartition is O(n) vs argsort O(n log n)
        top_indices = np.argpartition(similarities, -top_k)[-top_k:]
        top_indices = top_indices[np.argsort(similarities[top_indices])[::-1]]
    else:
        top_indices = np.argsort(similarities)[::-1]
    
    return [(int(idx), float(similarities[idx])) for idx in top_indices[:top_k]]


# SPARSE VECTOR FUNCTIONS (scipy accelerated)
# Only import scipy when needed - it's a heavy dependency

def sparse_cosine_similarity_plus(
    sparse_a: dict[any, float], 
    sparse_b: dict[any, float],
    vocabulary: list | None = None
) -> float:
    """
    Cosine similarity for sparse vectors using NumPy.
    
    If vocabulary is provided, converts to dense arrays for SIMD speedup.
    For very sparse vectors (< 100 non-zero), core.py may be faster due to conversion overhead.
    """
    if vocabulary is None:
        # Build vocabulary from both vectors
        vocabulary = list(set(sparse_a.keys()) | set(sparse_b.keys()))
    
    # Convert to dense arrays
    vec_a = np.array([sparse_a.get(word, 0.0) for word in vocabulary])
    vec_b = np.array([sparse_b.get(word, 0.0) for word in vocabulary])
    
    return cosine_similarity_plus(vec_a, vec_b)


def sparse_to_dense_matrix_plus(
    sparse_vectors: list[dict[any, float]],
    vocabulary: list | None = None
) -> tuple[NDArray[np.float64], list]:
    """
    Converts list of sparse vectors to dense NumPy matrix.
    
    Returns: (matrix, vocabulary) where matrix[i, j] = sparse_vectors[i][vocabulary[j]]
    Use this once, then use dense operations for bulk computations.
    """
    if vocabulary is None:
        vocab_set: set = set()
        for vec in sparse_vectors:
            vocab_set.update(vec.keys())
        vocabulary = list(vocab_set)
    
    word_to_idx = {word: idx for idx, word in enumerate(vocabulary)}
    
    matrix = np.zeros((len(sparse_vectors), len(vocabulary)), dtype=np.float64)
    
    for doc_id, vec in enumerate(sparse_vectors):
        for word, score in vec.items():
            if word in word_to_idx:
                matrix[doc_id, word_to_idx[word]] = score
    
    return matrix, vocabulary


# UTILITY FUNCTIONS

def sort_results_plus(scores: NDArray, limit: int = 10) -> list[tuple[int, float]]:
    """Sorts array of scores descending. Returns [(idx, score), ...]"""
    if limit < len(scores):
        top_indices = np.argpartition(scores, -limit)[-limit:]
        top_indices = top_indices[np.argsort(scores[top_indices])[::-1]]
    else:
        top_indices = np.argsort(scores)[::-1]
    
    return [(int(idx), float(scores[idx])) for idx in top_indices[:limit]]
