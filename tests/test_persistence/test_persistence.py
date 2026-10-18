
import pytest

from yeny import Yeny
from yeny.config import YenyOptions
from yeny.utils.nlp import WordTokenizer

def _set_version_name(storage, version_name):
	storage._generate_versioned_name = lambda base_name: version_name

@pytest.mark.integration
def test_save_and_reload_with_sqlite(sample_corpus, tmp_path):
	db_path = tmp_path / "yeny.db"

	yeny = Yeny(
		name="articles",
		engine="core",
		options=YenyOptions(storage_type="sqlite", db_path=str(db_path)),
		preprocessor=WordTokenizer(),
		autoload=False,
	)
	yeny.index(sample_corpus, persist=False)
	_set_version_name(yeny.storage, "articles__v1")
	yeny.save()

	current_alias = yeny.storage.get_alias("articles")
	assert current_alias == "articles__v1"
	assert current_alias in yeny.list_versions()
	assert yeny.search("frontend", top_k=1).results[0].doc_id == "doc2"

	reloaded = Yeny(
		name="articles",
		engine="core",
		options=YenyOptions(storage_type="sqlite", db_path=str(db_path)),
		preprocessor=WordTokenizer(),
	)

	reloaded_response = reloaded.search("frontend", top_k=1)

	assert reloaded_response.results[0].doc_id == "doc2"
	assert reloaded.storage.get_alias("articles") == "articles__v1"

@pytest.mark.integration
def test_reindex_creates_new_version_and_updates_alias(sample_corpus, tmp_path):
	db_path = tmp_path / "yeny.db"

	yeny = Yeny(
		name="articles",
		engine="core",
		options=YenyOptions(storage_type="sqlite", db_path=str(db_path)),
		preprocessor=WordTokenizer(),
		autoload=False,
	)
	yeny.index(sample_corpus, persist=False)
	_set_version_name(yeny.storage, "articles__v1")
	yeny.save()

	updated_corpus = dict(sample_corpus)
	updated_corpus["doc4"] = "Modern frontend with React"
	_set_version_name(yeny.storage, "articles__v2")
	yeny.reindex(updated_corpus)

	assert yeny.storage.get_alias("articles") == "articles__v2"
	versions = yeny.list_versions()
	assert "articles__v1" in versions
	assert "articles__v2" in versions
	assert versions.index("articles__v1") < versions.index("articles__v2")
	assert yeny.search("react", top_k=1).results[0].doc_id == "doc4"
