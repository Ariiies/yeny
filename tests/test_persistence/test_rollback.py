
import pytest

from lucis import Lucis
from lucis.config import LucisOptions
from lucis.exceptions import LucisEngineError
from lucis.utils.nlp import word_tokenizer

def _set_version_name(storage, version_name):
	storage._generate_versioned_name = lambda base_name: version_name

@pytest.mark.integration
def test_rollback_restores_previous_version(sample_corpus, tmp_path):
	db_path = tmp_path / "lucis.db"

	lucis = Lucis(
		name="articles",
		engine="core",
		options=LucisOptions(storage_type="sqlite", db_path=str(db_path)),
		preprocessor=word_tokenizer,
		autoload=False,
	)
	lucis.index(sample_corpus, persist=False)
	_set_version_name(lucis.storage, "articles__v1")
	lucis.save()

	first_version = lucis.storage.get_alias("articles")

	updated_corpus = dict(sample_corpus)
	updated_corpus["doc4"] = "Modern frontend with React"
	_set_version_name(lucis.storage, "articles__v2")
	lucis.reindex(updated_corpus)
	second_version = lucis.storage.get_alias("articles")

	assert first_version == "articles__v1"
	assert second_version == "articles__v2"
	assert lucis.search("react", top_k=1).results[0].doc_id == "doc4"

	lucis.rollback()

	assert lucis.storage.get_alias("articles") == first_version
	versions = lucis.list_versions()
	assert first_version in versions
	assert second_version in versions
	assert versions.index(first_version) < versions.index(second_version)
	assert lucis.search("react", top_k=1).results == []
	assert lucis.search("frontend", top_k=1).results[0].doc_id == "doc2"

@pytest.mark.integration
def test_rollback_without_previous_version_raises(tmp_path):
	db_path = tmp_path / "lucis.db"

	lucis = Lucis(
		name="articles",
		engine="core",
		options=LucisOptions(storage_type="sqlite", db_path=str(db_path)),
		preprocessor=word_tokenizer,
		autoload=False,
	)
	lucis.index({"doc1": "Python is a language"}, persist=False)
	_set_version_name(lucis.storage, "articles__v1")
	lucis.save()

	with pytest.raises(LucisEngineError):
		lucis.rollback()
