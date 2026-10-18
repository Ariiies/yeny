"""
Plus Engines - Implementaciones optimizadas con NumPy y Polars.

Estas implementaciones son OPCIONALES y solo se cargan si las
dependencias están instaladas. Ofrecen mejor rendimiento para:
- Corpus grandes (> 100k documentos)
- Operaciones vectorizadas masivas
- Entornos con buena disponibilidad de memoria
"""
from typing import Iterator
import importlib.util


# ═══════════════════════════════════════════════════════════════════
# Detección de dependencias disponibles
# ═══════════════════════════════════════════════════════════════════

def _is_available(module_name: str) -> bool:
    """Verifica si un módulo está instalado sin importarlo."""
    return importlib.util.find_spec(module_name) is not None


HAS_NUMPY = _is_available("numpy")
HAS_POLARS = _is_available("polars")


# ═══════════════════════════════════════════════════════════════════
# NumPy Engine
# ═══════════════════════════════════════════════════════════════════

class NumpyEngine:
    """
    Engine optimizado con NumPy para operaciones vectorizadas.
    
    Ventajas sobre VanillaEngine:
    - Operaciones SIMD en CPU (hasta 10x más rápido en vectores grandes)
    - Mejor uso de caché de CPU
    - Operaciones matriciales nativas
    
    Requisitos:
    - numpy instalado: pip install yeny[plus]
    """
    
    __slots__ = ('np',)
    
    def __init__(self):
        if not HAS_NUMPY:
            raise ImportError(
                "NumPy no está instalado. Instálalo con:\n"
                "  pip install numpy\n"
                "  o: pip install yeny[plus]"
            )
        import numpy as np
        self.np = np
    
    @property
    def name(self) -> str:
        return "numpy"
    
    def build_inverted_index(self, tokenized_corpus: list[list[str]]) -> dict[str, dict[int, int]]:
        """
        Construye índice invertido.
        
        Nota: Esta operación es inherentemente secuencial por la naturaleza
        de los diccionarios, así que no hay ventaja significativa con NumPy.
        Usamos la misma lógica que VanillaEngine.
        """
        index: dict[str, dict[int, int]] = {}
        
        for doc_id, tokens in enumerate(tokenized_corpus):
            for token in tokens:
                if token not in index:
                    index[token] = {}
                if doc_id not in index[token]:
                    index[token][doc_id] = 0
                index[token][doc_id] += 1
        
        return index
    
    def term_frequency(self, word: str, doc_id: int, inverted_index: dict) -> int:
        return inverted_index.get(word, {}).get(doc_id, 0)
    
    def document_frequency(self, word: str, inverted_index: dict) -> int:
        return len(inverted_index.get(word, {}))
    
    def dot_product(self, vec_a: list[float], vec_b: list[float]) -> float:
        """Producto punto vectorizado con NumPy."""
        return float(self.np.dot(vec_a, vec_b))
    
    def vector_norm(self, vec: list[float]) -> float:
        """Norma L2 con NumPy (usa BLAS internamente)."""
        return float(self.np.linalg.norm(vec))
    
    def cosine_similarity(self, vec_a: list[float], vec_b: list[float]) -> float:
        """
        Similitud del coseno optimizada.
        
        NumPy maneja vectores de cualquier tamaño eficientemente.
        """
        if not vec_a or not vec_b:
            return 0.0
        
        a = self.np.asarray(vec_a)
        b = self.np.asarray(vec_b)
        
        norm_a = self.np.linalg.norm(a)
        norm_b = self.np.linalg.norm(b)
        
        if norm_a == 0.0 or norm_b == 0.0:
            return 0.0
        
        return float(self.np.dot(a, b) / (norm_a * norm_b))
    
    def argsort_descending(self, values: list[float]) -> list[int]:
        """
        Ordenamiento con NumPy (quicksort/mergesort optimizado).
        
        np.argsort es significativamente más rápido para arrays grandes.
        """
        arr = self.np.asarray(values)
        # argsort ordena ascendente, [::-1] lo invierte
        return self.np.argsort(arr)[::-1].tolist()
    
    def batch_cosine_similarity(
        self, 
        query_vec: list[float], 
        doc_vectors: list[list[float]]
    ) -> list[float]:
        """
        Similitud del coseno para múltiples documentos a la vez.
        
        Esta es donde NumPy BRILLA - operaciones matriciales vectorizadas.
        """
        if not doc_vectors:
            return []
        
        query = self.np.asarray(query_vec)
        docs = self.np.asarray(doc_vectors)
        
        query_norm = self.np.linalg.norm(query)
        if query_norm == 0.0:
            return [0.0] * len(doc_vectors)
        
        # Normas de todos los documentos a la vez
        doc_norms = self.np.linalg.norm(docs, axis=1)
        
        # Producto punto de query con todos los docs
        dots = docs @ query  # Multiplicación matricial
        
        # Evitar división por cero
        with self.np.errstate(divide='ignore', invalid='ignore'):
            similarities = dots / (doc_norms * query_norm)
            similarities = self.np.nan_to_num(similarities, nan=0.0)
        
        return similarities.tolist()
    
    def build_tfidf_matrix(
        self, 
        tokenized_corpus: list[list[str]], 
        vocabulary: list[str],
        inverted_index: dict
    ):
        """
        Construye matriz TF-IDF completa (docs × vocab).
        
        Retorna un numpy array para operaciones matriciales eficientes.
        """
        from math import log
        
        n_docs = len(tokenized_corpus)
        n_vocab = len(vocabulary)
        
        # Matriz de ceros
        matrix = self.np.zeros((n_docs, n_vocab), dtype=self.np.float32)
        
        # Mapeo palabra -> índice para acceso O(1)
        word_to_idx = {word: idx for idx, word in enumerate(vocabulary)}
        
        for word, doc_counts in inverted_index.items():
            if word not in word_to_idx:
                continue
            
            word_idx = word_to_idx[word]
            df = len(doc_counts)
            idf = log(n_docs / df) if df > 0 else 0.0
            
            for doc_id, tf in doc_counts.items():
                matrix[doc_id, word_idx] = tf * idf
        
        return matrix


# ═══════════════════════════════════════════════════════════════════
# Polars Engine
# ═══════════════════════════════════════════════════════════════════

class PolarsEngine:
    """
    Engine para datasets masivos usando Polars.
    
    Ventajas:
    - Procesamiento lazy (solo computa lo necesario)
    - Paralelización automática en múltiples cores
    - Excelente para corpus > 1M documentos
    - Bajo consumo de memoria con streaming
    
    Requisitos:
    - polars instalado: pip install yeny[plus]
    """
    
    __slots__ = ('pl',)
    
    def __init__(self):
        if not HAS_POLARS:
            raise ImportError(
                "Polars no está instalado. Instálalo con:\n"
                "  pip install polars\n"
                "  o: pip install yeny[plus]"
            )
        import polars as pl
        self.pl = pl
    
    @property
    def name(self) -> str:
        return "polars"
    
    def build_inverted_index(self, tokenized_corpus: list[list[str]]) -> dict[str, dict[int, int]]:
        """
        Construye índice invertido usando Polars.
        
        Para corpus muy grandes, Polars puede ser más eficiente
        al procesar en chunks paralelos.
        """
        # Expandir corpus a formato tabular
        rows = []
        for doc_id, tokens in enumerate(tokenized_corpus):
            for token in tokens:
                rows.append({"doc_id": doc_id, "token": token})
        
        if not rows:
            return {}
        
        # Crear DataFrame y agrupar
        df = self.pl.DataFrame(rows)
        
        # Contar ocurrencias por (token, doc_id)
        counts = (
            df.lazy()
            .group_by(["token", "doc_id"])
            .agg(self.pl.len().alias("count"))
            .collect()
        )
        
        # Convertir a diccionario
        index: dict[str, dict[int, int]] = {}
        for row in counts.iter_rows(named=True):
            token = row["token"]
            doc_id = row["doc_id"]
            count = row["count"]
            
            if token not in index:
                index[token] = {}
            index[token][doc_id] = count
        
        return index
    
    def term_frequency(self, word: str, doc_id: int, inverted_index: dict) -> int:
        return inverted_index.get(word, {}).get(doc_id, 0)
    
    def document_frequency(self, word: str, inverted_index: dict) -> int:
        return len(inverted_index.get(word, {}))
    
    def dot_product(self, vec_a: list[float], vec_b: list[float]) -> float:
        """Producto punto con Polars Series."""
        series_a = self.pl.Series(vec_a)
        series_b = self.pl.Series(vec_b)
        return (series_a * series_b).sum()
    
    def vector_norm(self, vec: list[float]) -> float:
        """Norma L2 con Polars."""
        series = self.pl.Series(vec)
        return (series * series).sum() ** 0.5
    
    def cosine_similarity(self, vec_a: list[float], vec_b: list[float]) -> float:
        if not vec_a or not vec_b:
            return 0.0
        
        a = self.pl.Series(vec_a)
        b = self.pl.Series(vec_b)
        
        dot = (a * b).sum()
        norm_a = (a * a).sum() ** 0.5
        norm_b = (b * b).sum() ** 0.5
        
        if norm_a == 0.0 or norm_b == 0.0:
            return 0.0
        
        return dot / (norm_a * norm_b)
    
    def argsort_descending(self, values: list[float]) -> list[int]:
        """Ordenamiento con Polars."""
        df = self.pl.DataFrame({
            "idx": range(len(values)),
            "val": values
        })
        
        sorted_df = df.sort("val", descending=True)
        return sorted_df["idx"].to_list()
    
    def batch_cosine_similarity(
        self, 
        query_vec: list[float], 
        doc_vectors: list[list[float]]
    ) -> list[float]:
        """
        Similitud batch con Polars DataFrame.
        
        Polars optimiza operaciones columnar automáticamente.
        """
        if not doc_vectors:
            return []
        
        n_dims = len(query_vec)
        
        # Crear DataFrame con docs como filas
        data = {f"d{i}": [dv[i] for dv in doc_vectors] for i in range(n_dims)}
        df = self.pl.DataFrame(data)
        
        query = self.pl.Series(query_vec)
        query_norm = (query * query).sum() ** 0.5
        
        if query_norm == 0.0:
            return [0.0] * len(doc_vectors)
        
        # Calcular dot products y norms
        results = []
        for row in df.iter_rows():
            doc = self.pl.Series(row)
            doc_norm = (doc * doc).sum() ** 0.5
            if doc_norm == 0.0:
                results.append(0.0)
            else:
                dot = (query * doc).sum()
                results.append(dot / (query_norm * doc_norm))
        
        return results


# ═══════════════════════════════════════════════════════════════════
# Factory para seleccionar engine automáticamente
# ═══════════════════════════════════════════════════════════════════

def get_engine(preference: str = "auto"):
    """
    Factory para obtener el engine óptimo.
    
    Args:
        preference: 
            - "auto": Selecciona el mejor disponible (numpy > polars > vanilla)
            - "vanilla": Fuerza Python puro
            - "numpy": Fuerza NumPy (error si no instalado)
            - "polars": Fuerza Polars (error si no instalado)
    
    Returns:
        Instancia del engine seleccionado
    """
    from .core import CoreEngine
    
    if preference == "vanilla":
        return CoreEngine()
    
    if preference == "numpy":
        return NumpyEngine()
    
    if preference == "polars":
        return PolarsEngine()
    
    if preference == "auto":
        # Prioridad: numpy > vanilla (polars es mejor para casos específicos)
        if HAS_NUMPY:
            return NumpyEngine()
        return CoreEngine()
    
    raise ValueError(f"Engine desconocido: {preference}. Usa: auto, vanilla, numpy, polars")
