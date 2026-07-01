
import pytest

from lucis import Lucis
from lucis.utils.nlp import word_tokenizer

def _set_version_name(storage, version_name):
	storage._generate_versioned_name = lambda base_name: version_name

@pytest.mark.integration
def test_save_and_reload_with_sqlite(sample_corpus, tmp_path):
	db_path = tmp_path / "lucis.db"

	lucis = Lucis(
		name="articles",
		engine="core",
		storage_type="sqlite",
		db_path=str(db_path),
		preprocessor=word_tokenizer,
		autoload=False,
	)
	lucis.index(sample_corpus, persist=False)
	_set_version_name(lucis.storage, "articles__v1")
	lucis.save()

	current_alias = lucis.storage.get_alias("articles")
	assert current_alias == "articles__v1"
	assert current_alias in lucis.list_versions()
	assert lucis.search("frontend", top_k=1).results[0].doc_id == "doc2"

	reloaded = Lucis(
		name="articles",
		engine="core",
		storage_type="sqlite",
		db_path=str(db_path),
		preprocessor=word_tokenizer,
	)

	reloaded_response = reloaded.search("frontend", top_k=1)

	assert reloaded_response.results[0].doc_id == "doc2"
	assert reloaded.storage.get_alias("articles") == "articles__v1"

@pytest.mark.integration
def test_reindex_creates_new_version_and_updates_alias(sample_corpus, tmp_path):
	db_path = tmp_path / "lucis.db"

	lucis = Lucis(
		name="articles",
		engine="core",
		storage_type="sqlite",
		db_path=str(db_path),
		preprocessor=word_tokenizer,
		autoload=False,
	)
	lucis.index(sample_corpus, persist=False)
	_set_version_name(lucis.storage, "articles__v1")
	lucis.save()

	updated_corpus = dict(sample_corpus)
	updated_corpus["doc4"] = "Modern frontend with React"
	_set_version_name(lucis.storage, "articles__v2")
	lucis.reindex(updated_corpus)

	assert lucis.storage.get_alias("articles") == "articles__v2"
	versions = lucis.list_versions()
	assert "articles__v1" in versions
	assert "articles__v2" in versions
	assert versions.index("articles__v1") < versions.index("articles__v2")
	assert lucis.search("react", top_k=1).results[0].doc_id == "doc4"
