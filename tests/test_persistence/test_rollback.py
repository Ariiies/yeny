
import pytest

from yeny import Yeny
from yeny.config import YenyOptions
from yeny.exceptions import YenyEngineError
from yeny.utils.nlp import WordTokenizer

def _set_version_name(storage, version_name):
	storage._generate_versioned_name = lambda base_name: version_name

@pytest.mark.integration
def test_rollback_restores_previous_version(sample_corpus, tmp_path):
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

	first_version = yeny.storage.get_alias("articles")

	updated_corpus = dict(sample_corpus)
	updated_corpus["doc4"] = "Modern frontend with React"
	_set_version_name(yeny.storage, "articles__v2")
	yeny.reindex(updated_corpus)
	second_version = yeny.storage.get_alias("articles")

	assert first_version == "articles__v1"
	assert second_version == "articles__v2"
	assert yeny.search("react", top_k=1).results[0].doc_id == "doc4"

	yeny.rollback()

	assert yeny.storage.get_alias("articles") == first_version
	versions = yeny.list_versions()
	assert first_version in versions
	assert second_version in versions
	assert versions.index(first_version) < versions.index(second_version)
	assert yeny.search("react", top_k=1).results == []
	assert yeny.search("frontend", top_k=1).results[0].doc_id == "doc2"

@pytest.mark.integration
def test_rollback_without_previous_version_raises(tmp_path):
	db_path = tmp_path / "yeny.db"

	yeny = Yeny(
		name="articles",
		engine="core",
		options=YenyOptions(storage_type="sqlite", db_path=str(db_path)),
		preprocessor=WordTokenizer(),
		autoload=False,
	)
	yeny.index({"doc1": "Python is a language"}, persist=False)
	_set_version_name(yeny.storage, "articles__v1")
	yeny.save()

	with pytest.raises(YenyEngineError):
		yeny.rollback()
