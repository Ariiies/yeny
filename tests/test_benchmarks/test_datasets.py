"""Tests for deterministic synthetic dataset generation."""

import random
from dataclasses import replace
from collections import Counter

import pytest

from benchmarks.config import load_profiles, load_reference_hashes
from benchmarks.datasets import build_vocabulary, generate_dataset
from benchmarks.queries import build_queries


@pytest.mark.unit
def test_vocabulary_is_stable_unique_and_alphabetic():
    vocabulary = build_vocabulary(100)

    assert vocabulary[:3] == ["tokena", "tokenb", "tokenc"]
    assert len(set(vocabulary)) == 100
    assert all(token.isalpha() and token.islower() for token in vocabulary)


@pytest.mark.unit
def test_dataset_generation_is_deterministic():
    profile = load_profiles()["tiny"]

    first = generate_dataset(profile)
    second = generate_dataset(profile)

    assert first.documents == second.documents
    assert first.manifest == second.manifest
    assert len(first.manifest.sha256) == 64


@pytest.mark.unit
def test_tiny_dataset_hash_is_frozen():
    dataset = generate_dataset(load_profiles()["tiny"])

    assert dataset.manifest.sha256 == (
        "60735906d9feebb636cd173b04d80497"
        "eda774956df222dbd4de291e9d135be0"
    )


@pytest.mark.unit
def test_tiny_hashes_match_frozen_reference():
    reference = load_reference_hashes()["tiny"]
    dataset = generate_dataset(load_profiles()["tiny"])
    queries = build_queries(dataset)

    assert dataset.manifest.sha256 == reference["dataset_sha256"]
    assert queries.manifest.sha256 == reference["queries_sha256"]


@pytest.mark.slow
@pytest.mark.parametrize("profile_name", ["small", "medium", "large"])
def test_profile_hashes_match_frozen_reference(profile_name):
    reference = load_reference_hashes()[profile_name]
    dataset = generate_dataset(load_profiles()[profile_name])
    queries = build_queries(dataset)

    assert dataset.manifest.sha256 == reference["dataset_sha256"]
    assert queries.manifest.sha256 == reference["queries_sha256"]


@pytest.mark.unit
def test_different_seed_changes_dataset_hash():
    profile = load_profiles()["tiny"]

    first = generate_dataset(profile)
    second = generate_dataset(replace(profile, seed=profile.seed + 1))

    assert first.manifest.sha256 != second.manifest.sha256


@pytest.mark.unit
def test_manifest_matches_generated_dataset():
    profile = load_profiles()["tiny"]
    dataset = generate_dataset(profile)
    counts = Counter(dataset.documents.values())
    repeated_documents = sum(count - 1 for count in counts.values())

    assert dataset.manifest.documents == profile.documents
    assert dataset.manifest.vocabulary_nominal == profile.vocabulary_size
    assert dataset.manifest.intentional_duplicates == 2
    assert repeated_documents >= dataset.manifest.intentional_duplicates
    assert dataset.manifest.total_tokens == sum(
        len(text.split()) for text in dataset.documents.values()
    )
    assert dataset.manifest.vocabulary_observed == len(
        {
            token
            for text in dataset.documents.values()
            for token in text.split()
        }
    )


@pytest.mark.unit
def test_generation_does_not_modify_global_random_state():
    profile = load_profiles()["tiny"]
    random.seed(12345)
    state = random.getstate()

    generate_dataset(profile)

    assert random.getstate() == state


@pytest.mark.unit
def test_document_ids_are_stable_and_ordered():
    dataset = generate_dataset(load_profiles()["tiny"])

    assert list(dataset.documents)[:2] == ["doc_000000", "doc_000001"]
    assert list(dataset.documents)[-1] == "doc_000099"
