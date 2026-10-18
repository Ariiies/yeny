
from dataclasses import FrozenInstanceError

import pytest
import yeny

from yeny import Yeny, SearchResponse
from yeny.config import YenyOptions, TableConfig, TableSource
from yeny.engines.core import CoreEngine
from yeny.engines.lite import LiteEngine
from yeny.storage.json_storage import JSONStorage
from yeny.utils.nlp import WordTokenizer

@pytest.fixture
def sample_corpus():
    return {
        "doc1": "Python is a versatile language",
        "doc2": "JavaScript dominates the frontend",
        "doc3": "Python and JavaScript are popular",
    }

@pytest.mark.integration
class TestYenyPublicApi:

    def test_from_dict_builds_searchable_index(self, sample_corpus, tmp_path):
        yeny = Yeny.from_dict(
            sample_corpus,
            name="integration_core",
            engine="core",
            options=YenyOptions(storage_dir=str(tmp_path)),
            preprocessor=WordTokenizer(),
        )

        response = yeny.search("versatile", top_k=3)

        assert isinstance(response, SearchResponse)
        assert response.query == "versatile"
        assert response.tokens == ["versatile"]
        assert response.total_results >= 1
        assert response.results[0].doc_id == "doc1"
        assert response.results[0].rank == 1

    def test_from_list_assigns_sequential_ids(self, tmp_path):
        yeny = Yeny.from_list(
            ["Machine learning with Python", "Web development with JavaScript"],
            name="integration_list",
            engine="core",
            options=YenyOptions(storage_dir=str(tmp_path)),
            preprocessor=WordTokenizer(),
        )

        response = yeny.search("Python", top_k=3)

        assert isinstance(response, SearchResponse)
        assert response.results[0].doc_id == 0

    def test_engine_selection(self, sample_corpus, tmp_path):
        yeny_core = Yeny.from_dict(
            sample_corpus,
            name="engine_core",
            engine="core",
            options=YenyOptions(storage_dir=str(tmp_path / "core")),
            preprocessor=WordTokenizer(),
        )
        yeny_lite = Yeny.from_dict(
            sample_corpus,
            name="engine_lite",
            engine="lite",
            options=YenyOptions(storage_dir=str(tmp_path / "lite")),
        )

        assert isinstance(yeny_core.engine, CoreEngine)
        assert isinstance(yeny_lite.engine, LiteEngine)

    def test_save_and_reload_roundtrip(self, sample_corpus, tmp_path):
        yeny = Yeny.from_dict(
            sample_corpus,
            name="persistent_index",
            engine="core",
            options=YenyOptions(storage_dir=str(tmp_path)),
            preprocessor=WordTokenizer(),
        )

        yeny.save()

        reloaded = Yeny(
            name="persistent_index",
            engine="core",
            options=YenyOptions(storage_dir=str(tmp_path)),
            preprocessor=WordTokenizer(),
        )

        response = reloaded.search("frontend", top_k=3)

        assert isinstance(response, SearchResponse)
        assert response.results
        assert response.results[0].doc_id == "doc2"

    def test_custom_preprocessor_applies_to_index_and_search(self, tmp_path):
        def custom_preprocessor(text: str):
            return text.lower().strip()

        yeny = Yeny.from_dict(
            {"doc1": "  PYTHON TESTING  "},
            name="custom_preprocessor",
            engine="core",
            options=YenyOptions(storage_dir=str(tmp_path)),
            preprocessor=custom_preprocessor,
        )

        response = yeny.search("PYTHON", top_k=1)

        assert response.tokens == ["python"]
        assert response.results[0].doc_id == "doc1"

    def test_is_indexed_is_public_and_read_only(self, tmp_path):
        empty = Yeny(
            name="empty",
            autoload=False,
            options=YenyOptions(storage_dir=str(tmp_path / "empty")),
        )
        built = Yeny.from_dict(
            {"doc": "searchable"},
            name="built",
            options=YenyOptions(storage_dir=str(tmp_path / "built")),
        )

        assert empty.is_indexed is False
        assert built.is_indexed is True
        with pytest.raises(AttributeError):
            built.is_indexed = False

    def test_factory_rejects_misspelled_option_immediately(self):
        with pytest.raises(TypeError, match="storage_dri"):
            Yeny.from_dict({"doc": "text"}, storage_dri="typo")

    def test_yeny_options_defaults_and_immutability(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        defaults = YenyOptions()
        instance = Yeny(name="defaults", autoload=False)

        assert defaults.storage_dir == "yeny_data"
        assert defaults.storage_type == "json"
        assert defaults.db_path is None
        assert defaults.connection_url is None
        assert defaults.max_loaded_shards == 0
        assert defaults.memory_limit_mb is None
        assert defaults.binary_dir == "auto"
        assert instance._binary_dir == "yeny_data/yny"
        assert instance._max_loaded_shards == 0
        assert instance._memory_limit_mb is None
        with pytest.raises(FrozenInstanceError):
            defaults.storage_dir = "changed"

    def test_configuration_objects_live_only_in_config_module(self):
        assert YenyOptions is not None
        assert TableConfig is not None
        assert TableSource is not None
        assert not hasattr(yeny, "YenyOptions")
        assert not hasattr(yeny, "TableConfig")
        assert not hasattr(yeny, "TableSource")
        assert not hasattr(yeny, "AlchemyTableConfig")

    def test_explicit_storage_takes_precedence_over_options(self, tmp_path):
        custom_storage = JSONStorage(directory=str(tmp_path / "custom"))
        instance = Yeny(
            name="custom_storage",
            storage=custom_storage,
            autoload=False,
            options=YenyOptions(
                storage_type="sqlite",
                db_path=None,
                storage_dir=str(tmp_path / "declarative"),
            ),
        )

        assert instance.storage is custom_storage

    @pytest.mark.parametrize(
        ("options", "message"),
        [
            (YenyOptions(storage_type="sqlite"), "db_path is required"),
            (
                YenyOptions(storage_type="alchemy"),
                "connection_url is required",
            ),
        ],
    )
    def test_declarative_storage_preserves_required_field_errors(
        self, options, message
    ):
        with pytest.raises(ValueError, match=message):
            Yeny(name="invalid_storage", autoload=False, options=options)
