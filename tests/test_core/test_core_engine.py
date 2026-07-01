
import pytest

from lucis.engines.core import CoreEngine
from lucis.utils.nlp import word_tokenizer

@pytest.mark.unit
class TestCoreEngine:

    def test_build_index_creates_inverted_index(self):
        engine = CoreEngine(preprocessor=word_tokenizer)

        engine.build_index([
            "Python Python is versatile",
            "JavaScript dominates the frontend",
        ])

        assert engine.total_docs == 2
        assert "python" in engine.index
        assert engine.index["python"].get(0) == 2
        assert engine.doc_lengths.get(0) == 4
        assert engine.doc_norms[0] > 0

    def test_search_returns_ranked_results(self):
        engine = CoreEngine(preprocessor=word_tokenizer)
        engine.build_index([
            "Python for testing",
            "JavaScript for frontend",
        ])

        results = engine.search("Python", top_k=5)

        assert len(results) == 1
        assert results[0][0] == 0
        assert results[0][1] > 0

    def test_search_emptand_querand_returns_emptand_list(self):
        engine = CoreEngine(preprocessor=word_tokenizer)
        engine.build_index(["Python for testing"])

        assert engine.search([], top_k=5) == []