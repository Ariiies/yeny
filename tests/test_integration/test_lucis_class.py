
import pytest

from lucis import Lucis, SearchResponse
from lucis.engines.core import CoreEngine
from lucis.engines.lite import LiteEngine
from lucis.utils.nlp import WordTokenizer

@pytest.fixture
def sample_corpus():
    return {
        "doc1": "Python is a versatile language",
        "doc2": "JavaScript dominates the frontend",
        "doc3": "Python and JavaScript are popular",
    }

@pytest.mark.integration
class TestLucisPublicApi:

    def test_from_dict_builds_searchable_index(self, sample_corpus, tmp_path):
        lucis = Lucis.from_dict(
            sample_corpus,
            name="integration_core",
            engine="core",
            storage_dir=str(tmp_path),
            preprocessor=WordTokenizer(),
        )

        response = lucis.search("versatile", top_k=3)

        assert isinstance(response, SearchResponse)
        assert response.query == "versatile"
        assert response.tokens == ["versatile"]
        assert response.total_results >= 1
        assert response.results[0].doc_id == "doc1"
        assert response.results[0].rank == 1

    def test_from_list_assigns_sequential_ids(self, tmp_path):
        lucis = Lucis.from_list(
            ["Machine learning with Python", "Web development with JavaScript"],
            name="integration_list",
            engine="core",
            storage_dir=str(tmp_path),
            preprocessor=WordTokenizer(),
        )

        response = lucis.search("Python", top_k=3)

        assert isinstance(response, SearchResponse)
        assert response.results[0].doc_id == 0

    def test_engine_selection(self, sample_corpus, tmp_path):
        lucis_core = Lucis.from_dict(
            sample_corpus,
            name="engine_core",
            engine="core",
            storage_dir=str(tmp_path / "core"),
            preprocessor=WordTokenizer(),
        )
        lucis_lite = Lucis.from_dict(
            sample_corpus,
            name="engine_lite",
            engine="lite",
            storage_dir=str(tmp_path / "lite"),
        )

        assert isinstance(lucis_core.engine, CoreEngine)
        assert isinstance(lucis_lite.engine, LiteEngine)

    def test_save_and_reload_roundtrip(self, sample_corpus, tmp_path):
        lucis = Lucis.from_dict(
            sample_corpus,
            name="persistent_index",
            engine="core",
            storage_dir=str(tmp_path),
            preprocessor=WordTokenizer(),
        )

        lucis.save()

        reloaded = Lucis(
            name="persistent_index",
            engine="core",
            storage_dir=str(tmp_path),
            preprocessor=WordTokenizer(),
        )

        response = reloaded.search("frontend", top_k=3)

        assert isinstance(response, SearchResponse)
        assert response.results
        assert response.results[0].doc_id == "doc2"

    def test_custom_preprocessor_applies_to_index_and_search(self, tmp_path):
        def custom_preprocessor(text: str):
            return text.lower().strip()

        lucis = Lucis.from_dict(
            {"doc1": "  PYTHON TESTING  "},
            name="custom_preprocessor",
            engine="core",
            storage_dir=str(tmp_path),
            preprocessor=custom_preprocessor,
        )

        response = lucis.search("PYTHON", top_k=1)

        assert response.tokens == ["python"]
        assert response.results[0].doc_id == "doc1"