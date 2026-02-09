"""
Math utilities for vector operations.

Optimized pure Python implementations for:
- Dense vector operations (lists)
- Sparse vector operations (dicts)
- Similarity calculations
"""
from math import sqrt
from typing import Iterator, Any

# DENSE VECTOR FUNCTIONS
# For vectors represented as list[float] where all dimensions are explicit
# Best for small vocabularies or when most values are non-zero

def dot_product(vec_a: list[float], vec_b: list[float]) -> float:
    """Dot product using zip generator - avoids intermediate list allocation."""
    return sum(a * b for a, b in zip(vec_a, vec_b))


def vector_norm(vec: list[float]) -> float:
    """L2 norm (Euclidean): ||v|| = sqrt(sum(v_i²))"""
    return sqrt(sum(x * x for x in vec))


def cosine_similarity(vec_a: list[float], vec_b: list[float]) -> float:
    """
    Cosine similarity between two dense vectors.
    
    Returns 0.0 for empty or zero vectors (safe division).
    """
    if not vec_a or not vec_b:
        return 0.0
    
    dot = dot_product(vec_a, vec_b)
    norm_a = vector_norm(vec_a)
    norm_b = vector_norm(vec_b)
    
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    
    return dot / (norm_a * norm_b)


def argsort_descending(values: list[float]) -> list[int]:
    """Returns indices sorted by descending value - useful for ranking."""
    indexed = list(enumerate(values))
    indexed.sort(key=lambda x: x[1], reverse=True)
    return [idx for idx, _ in indexed]


def batch_cosine_similarity(
    query_vec: list[float], 
    doc_vectors: list[list[float]]
) -> Iterator[float]:
    """
    Yields cosine similarities for multiple documents.
    
    Caches query_norm to avoid redundant computation.
    """
    query_norm = vector_norm(query_vec)
    
    if query_norm == 0.0:
        for _ in doc_vectors:
            yield 0.0
        return
    
    for doc_vec in doc_vectors:
        doc_norm = vector_norm(doc_vec)
        if doc_norm == 0.0:
            yield 0.0
        else:
            dot = dot_product(query_vec, doc_vec)
            yield dot / (query_norm * doc_norm)


# SPARSE VECTOR FUNCTIONS
# For vectors represented as dict[key, float] where only non-zero values are stored
# Best for TF-IDF vectors where vocabulary is large but docs contain few unique terms

def sparse_dot_product(sparse_a: dict[Any, float], sparse_b: dict[Any, float]) -> float:
    """
    Dot product for sparse vectors - only iterates non-zero elements.
    
    Iterates over smaller dict for efficiency: O(min(|a|, |b|))
    """
    if len(sparse_a) > len(sparse_b):
        sparse_a, sparse_b = sparse_b, sparse_a
    
    return sum(
        val * sparse_b.get(idx, 0.0)
        for idx, val in sparse_a.items()
    )


def sparse_vector_norm(sparse_vec: dict[Any, float]) -> float:
    """L2 norm for sparse vectors: ||v|| = sqrt(sum(v_i²)) over non-zero elements."""
    if not sparse_vec:
        return 0.0
    return sqrt(sum(val * val for val in sparse_vec.values()))


def sparse_cosine_similarity(sparse_a: dict[Any, float], sparse_b: dict[Any, float]) -> float:
    """
    Cosine similarity between two sparse vectors.
    
    This is the main function for comparing TF-IDF document vectors.
    """
    dot = sparse_dot_product(sparse_a, sparse_b)
    if dot == 0.0:
        return 0.0
    
    norm_a = sparse_vector_norm(sparse_a)
    norm_b = sparse_vector_norm(sparse_b)
    
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    
    return dot / (norm_a * norm_b)

# Helper function to sort search results
def sort_results(scores: dict[int, float], limit: int = 10) -> list[tuple[int, float]]:
    """Sorts search results by score descending. Returns [(doc_id, score), ...]"""
    return sorted(scores.items(), key=lambda x: x[1], reverse=True)[:limit]