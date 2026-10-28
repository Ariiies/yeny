
from dataclasses import FrozenInstanceError

import pytest
import yeny

from yeny import Yeny, SearchResponse, MetadataStorage
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
        assert defaults.storage_type == "metadata"
        assert defaults.db_path is None
        assert defaults.connection_url is None
        assert defaults.max_loaded_shards == 0
        assert defaults.memory_limit_mb is None
        assert defaults.binary_dir == "auto"
        assert instance._binary_dir == "yeny_data/yny"
        assert isinstance(instance.storage, MetadataStorage)
        assert instance.storage.db_path == "yeny_data/yny/yeny_meta.db"
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

    def test_default_persistence_generates_yny_and_metadata_storage(self, sample_corpus, tmp_path):
        options = YenyOptions(storage_dir=str(tmp_path), binary_dir="auto")
        searcher = Yeny(name="mi_indice", engine="core", options=options)
        searcher.index(sample_corpus)

        try:
            assert isinstance(searcher.storage, MetadataStorage)
            yny_dir = tmp_path / "yny"
            assert (yny_dir / "yeny_meta.db").exists()
            yny_files = list(yny_dir.glob("mi_indice__v*.yny"))
            assert len(yny_files) >= 1
            # Confirm no .json files were generated
            assert list(tmp_path.glob("*.json")) == []
            assert list(yny_dir.glob("*.json")) == []
        finally:
            searcher.close()

        # Test reload (autoload)
        loaded = Yeny(name="mi_indice", engine="core", options=options)
        try:
            assert loaded.is_indexed is True
            assert isinstance(loaded.storage, MetadataStorage)
            res = loaded.search("versatile", top_k=3)
            assert res.results
            assert res.results[0].doc_id == "doc1"
        finally:
            loaded.close()

    def test_binary_dir_boolean_normalization(self, tmp_path):
        opt_true = YenyOptions(storage_dir=str(tmp_path), binary_dir=True)
        assert opt_true.binary_dir == "auto"
        inst_true = Yeny(name="bool_true", autoload=False, options=opt_true)
        try:
            assert inst_true._binary_dir == str(tmp_path / "yny")
            assert isinstance(inst_true.storage, MetadataStorage)
        finally:
            inst_true.close()

        opt_false = YenyOptions(storage_dir=str(tmp_path), binary_dir=False)
        assert opt_false.binary_dir is None
        inst_false = Yeny(name="bool_false", autoload=False, options=opt_false)
        try:
            assert inst_false._binary_dir is None
            assert isinstance(inst_false.storage, JSONStorage)
        finally:
            inst_false.close()

    def test_explicit_json_storage_creates_json_file(self, sample_corpus, tmp_path):
        options = YenyOptions(storage_dir=str(tmp_path), storage_type="json")
        searcher = Yeny(name="json_idx", options=options, autoload=False)
        try:
            assert isinstance(searcher.storage, JSONStorage)
            searcher.index(sample_corpus)
            assert (tmp_path / "json_idx.json").exists()
            assert not (tmp_path / "yny").exists()
        finally:
            searcher.close()

    def test_from_list_and_from_dict_default_to_metadata_storage(self, tmp_path):
        list_dir = tmp_path / "list_data"
        yn_list = Yeny.from_list(
            ["hello world", "python search"],
            name="from_list_idx",
            options=YenyOptions(storage_dir=str(list_dir)),
        )
        try:
            assert isinstance(yn_list.storage, MetadataStorage)
            assert (list_dir / "yny" / "yeny_meta.db").exists()
            assert list((list_dir / "yny").glob("from_list_idx__v*.yny"))
            assert list(list_dir.glob("*.json")) == []
        finally:
            yn_list.close()

        dict_dir = tmp_path / "dict_data"
        yn_dict = Yeny.from_dict(
            {"d1": "hello world", "d2": "python search"},
            name="from_dict_idx",
            options=YenyOptions(storage_dir=str(dict_dir)),
        )
        try:
            assert isinstance(yn_dict.storage, MetadataStorage)
            assert (dict_dir / "yny" / "yeny_meta.db").exists()
            assert list((dict_dir / "yny").glob("from_dict_idx__v*.yny"))
            assert list(dict_dir.glob("*.json")) == []
        finally:
            yn_dict.close()

    def test_in_memory_mode_leaves_zero_disk_trace(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        docs = ["Python is fast and versatile", "Machine learning search engine"]

        # 1. from_list with persist=False
        searcher_persist_false = Yeny.from_list(docs, persist=False)
        try:
            assert searcher_persist_false.is_in_memory is True
            res1 = searcher_persist_false.search("python")
            assert len(res1.results) == 1
            assert res1.results[0].doc_id == 0
        finally:
            searcher_persist_false.close()

        # Temporary working directory must be completely empty
        assert list(tmp_path.iterdir()) == []

        # 2. from_list with storage_type=None and binary_dir=None
        options_none = YenyOptions(storage_type=None, binary_dir=None, storage_dir=str(tmp_path))
        searcher_none_opts = Yeny.from_list(docs, options=options_none)
        try:
            assert searcher_none_opts.is_in_memory is True
            res2 = searcher_none_opts.search("versatile")
            assert len(res2.results) == 1
            assert res2.results[0].doc_id == 0
        finally:
            searcher_none_opts.close()

        # Still completely empty
        assert list(tmp_path.iterdir()) == []

        # 3. Yeny constructor with storage_type="memory" and index()
        options_mem = YenyOptions(storage_type="memory", storage_dir=str(tmp_path))
        searcher_mem = Yeny(name="in_memory_idx", options=options_mem)
        try:
            assert searcher_mem.is_in_memory is True
            searcher_mem.index(docs)
            res3 = searcher_mem.search("engine")
            assert len(res3.results) == 1
            # save() and load() must be safe no-ops
            searcher_mem.save()
            searcher_mem.load()
        finally:
            searcher_mem.close()

        assert list(tmp_path.iterdir()) == []

        # 4. from_dict with persist=False
        searcher_dict_mem = Yeny.from_dict({"k1": "Python in memory"}, persist=False)
        try:
            assert searcher_dict_mem.is_in_memory is True
            res4 = searcher_dict_mem.search("memory")
            assert len(res4.results) == 1
            assert res4.results[0].doc_id == "k1"
        finally:
            searcher_dict_mem.close()

        assert list(tmp_path.iterdir()) == []

    def test_shared_memory_storage_autoload(self, tmp_path):
        from yeny.storage.memory_storage import MemoryStorage
        docs = ["Fast ephemeral search", "Zero disk persistence with shared RAM"]
        mem = MemoryStorage()

        # Build index in shared in-memory storage
        s1 = Yeny(name="shared_idx", storage=mem)
        assert s1.is_in_memory is True
        s1.index(docs)
        assert s1.is_indexed is True
        s1.close()  # Must not wipe shared memory storage

        # Reload automatically from shared in-memory storage via autoload=True (default)
        s2 = Yeny(name="shared_idx", storage=mem)
        try:
            assert s2.is_in_memory is True
            assert s2.is_indexed is True
            res = s2.search("ephemeral")
            assert len(res.results) == 1
            assert res.results[0].doc_id == 0
        finally:
            s2.close()

        # Explicit clear clears the store
        mem.clear()
        assert mem.exists("shared_idx") is False
        assert list(tmp_path.iterdir()) == []
