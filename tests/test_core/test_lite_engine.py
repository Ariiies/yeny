
import pytest

from yeny.engines.lite import LiteEngine

@pytest.mark.unit
class TestLiteEngine:

    def test_build_index_uses_default_char_ngrams(self):
        engine = LiteEngine()

        engine.build_index([
            "Python for testing",
            "JavaScript for frontend",
        ])

        assert engine.total_docs == 2
        assert "pyt" in engine.index
        assert engine.index["pyt"].get(0) > 0

    def test_search_returns_relevant_results(self):
        engine = LiteEngine()
        engine.build_index([
            "Python for testing",
            "JavaScript for frontend",
        ])

        results = engine.search("python", top_k=5)

        assert len(results) == 1
        assert results[0][0] == 0
        assert results[0][1] > 0

    def test_add_documents_extends_index(self):
        engine = LiteEngine()
        engine.build_index(["Python for testing"])

        engine.add_documents(["Python and pytest"])

        assert engine.total_docs == 2
        assert engine.doc_lengths.get(1) > 0
        assert engine.search("pytest", top_k=5)[0][0] == 1