
import pytest
from lucis import Lucis
from lucis.utils.nlp import word_tokenizer

@pytest.fixture
def sample_corpus():
    return {
        "doc1": "Python is a versatile language",
        "doc2": "JavaScript dominates the frontend",
        "doc3": "Python and JavaScript are popular"
    }

@pytest.fixture
def sample_list_corpus():
    return [
        "Machine learning with Python",
        "Web development with JavaScript",
        "Deep neural networks"
    ]

@pytest.fixture
def buscador_core(sample_corpus):
    return Lucis.from_dict(sample_corpus, name="test_core", engine="core")

@pytest.fixture
def buscador_lite(sample_corpus):
    return Lucis.from_dict(sample_corpus, name="test_lite", engine="lite")

@pytest.fixture
def temp_dir(tmp_path):
    return tmp_path / "lucis_data"