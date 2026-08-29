
from dataclasses import FrozenInstanceError

import pytest
import lucis

from lucis import Lucis, SearchResponse
from lucis.config import LucisOptions, TableConfig, TableSource
from lucis.engines.core import CoreEngine
from lucis.engines.lite import LiteEngine
from lucis.storage.json_storage import JSONStorage
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
            options=LucisOptions(storage_dir=str(tmp_path)),
            preprocessor=WordTokenizer,
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
            options=LucisOptions(storage_dir=str(tmp_path)),
            preprocessor=WordTokenizer,
        )

        response = lucis.search("Python", top_k=3)

        assert isinstance(response, SearchResponse)
        assert response.results[0].doc_id == 0

    def test_engine_selection(self, sample_corpus, tmp_path):
        lucis_core = Lucis.from_dict(
            sample_corpus,
            name="engine_core",
            engine="core",
            options=LucisOptions(storage_dir=str(tmp_path / "core")),
            preprocessor=WordTokenizer,
        )
        lucis_lite = Lucis.from_dict(
            sample_corpus,
            name="engine_lite",
            engine="lite",
            options=LucisOptions(storage_dir=str(tmp_path / "lite")),
        )

        assert isinstance(lucis_core.engine, CoreEngine)
        assert isinstance(lucis_lite.engine, LiteEngine)

    def test_save_and_reload_roundtrip(self, sample_corpus, tmp_path):
        lucis = Lucis.from_dict(
            sample_corpus,
            name="persistent_index",
            engine="core",
            options=LucisOptions(storage_dir=str(tmp_path)),
            preprocessor=WordTokenizer,
        )

        lucis.save()

        reloaded = Lucis(
            name="persistent_index",
            engine="core",
            options=LucisOptions(storage_dir=str(tmp_path)),
            preprocessor=WordTokenizer,
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
            options=LucisOptions(storage_dir=str(tmp_path)),
            preprocessor=custom_preprocessor,
        )

        response = lucis.search("PYTHON", top_k=1)

        assert response.tokens == ["python"]
        assert response.results[0].doc_id == "doc1"

    def test_is_indexed_is_public_and_read_only(self, tmp_path):
        empty = Lucis(
            name="empty",
            autoload=False,
            options=LucisOptions(storage_dir=str(tmp_path / "empty")),
        )
        built = Lucis.from_dict(
            {"doc": "searchable"},
            name="built",
            options=LucisOptions(storage_dir=str(tmp_path / "built")),
        )

        assert empty.is_indexed is False
        assert built.is_indexed is True
        with pytest.raises(AttributeError):
            built.is_indexed = False

    def test_factory_rejects_misspelled_option_immediately(self):
        with pytest.raises(TypeError, match="storage_dri"):
            Lucis.from_dict({"doc": "text"}, storage_dri="typo")

    def test_lucis_options_defaults_and_immutability(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        defaults = LucisOptions()
        instance = Lucis(name="defaults", autoload=False)

        assert defaults.storage_dir == "lucis_data"
        assert defaults.storage_type == "json"
        assert defaults.db_path is None
        assert defaults.connection_url is None
        assert defaults.max_loaded_shards == 0
        assert defaults.memory_limit_mb is None
        assert defaults.binary_dir == "auto"
        assert instance._binary_dir == "lucis_data/lcs"
        assert instance._max_loaded_shards == 0
        assert instance._memory_limit_mb is None
        with pytest.raises(FrozenInstanceError):
            defaults.storage_dir = "changed"

    def test_configuration_objects_live_only_in_config_module(self):
        assert LucisOptions is not None
        assert TableConfig is not None
        assert TableSource is not None
        assert not hasattr(lucis, "LucisOptions")
        assert not hasattr(lucis, "TableConfig")
        assert not hasattr(lucis, "TableSource")
        assert not hasattr(lucis, "AlchemyTableConfig")

    def test_explicit_storage_takes_precedence_over_options(self, tmp_path):
        custom_storage = JSONStorage(directory=str(tmp_path / "custom"))
        instance = Lucis(
            name="custom_storage",
            storage=custom_storage,
            autoload=False,
            options=LucisOptions(
                storage_type="sqlite",
                db_path=None,
                storage_dir=str(tmp_path / "declarative"),
            ),
        )

        assert instance.storage is custom_storage

    @pytest.mark.parametrize(
        ("options", "message"),
        [
            (LucisOptions(storage_type="sqlite"), "db_path is required"),
            (
                LucisOptions(storage_type="alchemy"),
                "connection_url is required",
            ),
        ],
    )
    def test_declarative_storage_preserves_required_field_errors(
        self, options, message
    ):
        with pytest.raises(ValueError, match=message):
            Lucis(name="invalid_storage", autoload=False, options=options)
