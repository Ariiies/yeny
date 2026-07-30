"""Tests for deterministic benchmark query generation."""

from collections import Counter

import pytest

from benchmarks.config import load_profiles
from benchmarks.datasets import generate_dataset
from benchmarks.queries import build_queries


@pytest.fixture(scope="module")
def tiny_dataset():
    return generate_dataset(load_profiles()["tiny"])


@pytest.mark.unit
def test_query_generation_is_deterministic(tiny_dataset):
    first = build_queries(tiny_dataset)
    second = build_queries(tiny_dataset)

    assert first == second
    assert first.manifest.dataset_sha256 == tiny_dataset.manifest.sha256
    assert len(first.manifest.sha256) == 64


@pytest.mark.unit
def test_tiny_query_set_hash_is_frozen(tiny_dataset):
    queries = build_queries(tiny_dataset)

    assert queries.manifest.sha256 == (
        "78de5bc2f7e91be29ae348183ed12e3c"
        "386d477c5a354af377465acaf995a4f4"
    )


@pytest.mark.unit
def test_query_set_has_all_required_categories(tiny_dataset):
    queries = build_queries(tiny_dataset, per_category=4)
    category_counts = Counter(item.category for item in queries.items)

    assert category_counts == {
        "common": 4,
        "rare": 4,
        "multi": 4,
        "no_result": 4,
        "repeated": 1,
    }
    assert queries.manifest.queries == 17


@pytest.mark.unit
def test_no_result_queries_are_absent_from_corpus(tiny_dataset):
    corpus_tokens = {
        token
        for text in tiny_dataset.documents.values()
        for token in text.split()
    }
    queries = build_queries(tiny_dataset)

    absent = [
        item
        for item in queries.items
        if item.category == "no_result"
    ]
    assert absent
    assert all(not set(item.tokens).intersection(corpus_tokens)
               for item in absent)
    assert all(item.expected_documents == () for item in absent)


@pytest.mark.unit
def test_present_queries_reference_documents_containing_a_token(tiny_dataset):
    queries = build_queries(tiny_dataset)

    for item in queries.items:
        if item.category == "no_result":
            continue
        assert item.expected_documents
        for doc_id in item.expected_documents:
            document_tokens = set(tiny_dataset.documents[doc_id].split())
            assert document_tokens.intersection(item.tokens)


@pytest.mark.unit
def test_repeated_query_declares_repetition_count(tiny_dataset):
    queries = build_queries(tiny_dataset)
    repeated = [
        item for item in queries.items if item.category == "repeated"
    ]

    assert len(repeated) == 1
    assert repeated[0].repetitions == 100


@pytest.mark.unit
def test_query_generation_rejects_invalid_count(tiny_dataset):
    with pytest.raises(ValueError, match="per_category"):
        build_queries(tiny_dataset, per_category=0)
