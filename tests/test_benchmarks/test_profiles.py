"""Tests for benchmark profile loading and validation."""

import json
from pathlib import Path

import pytest

from benchmarks import queries as queries_module
from benchmarks.config import (
    EXPECTED_QUERY_SET_VERSION,
    BenchmarkProfile,
    BenchmarkRunConfig,
    load_profiles,
    load_reference_hashes,
)


def _valid_values():
    return {
        "documents": 10,
        "vocabulary_size": 32,
        "min_document_tokens": 4,
        "mode_document_tokens": 8,
        "max_document_tokens": 12,
        "zipf_exponent": 1.07,
        "duplicate_rate": 0.1,
        "seed": 42,
    }


@pytest.mark.unit
def test_default_profiles_are_small_and_ordered():
    profiles = load_profiles()

    assert list(profiles) == ["tiny", "small", "medium", "large"]
    assert [profile.documents for profile in profiles.values()] == [
        100,
        1000,
        10000,
        100000,
    ]
    assert all(profile.generator_version == "lexical_zipf_v1"
               for profile in profiles.values())


@pytest.mark.unit
def test_profiles_share_every_parameter_except_document_count():
    profiles = list(load_profiles().values())
    shared = {
        (
            profile.vocabulary_size,
            profile.min_document_tokens,
            profile.mode_document_tokens,
            profile.max_document_tokens,
            profile.zipf_exponent,
            profile.duplicate_rate,
            profile.seed,
        )
        for profile in profiles
    }

    assert len(shared) == 1


@pytest.mark.unit
def test_run_config_keeps_tiny_as_default_profile():
    assert BenchmarkRunConfig().profile == "tiny"


@pytest.mark.unit
def test_reference_hashes_cover_every_profile():
    reference = load_reference_hashes()

    assert list(reference) == ["tiny", "small", "medium", "large"]
    for entry in reference.values():
        assert len(entry["dataset_sha256"]) == 64
        assert len(entry["queries_sha256"]) == 64


@pytest.mark.unit
def test_reference_query_version_matches_query_module():
    assert EXPECTED_QUERY_SET_VERSION == queries_module.QUERY_SET_VERSION


def _write_reference(tmp_path, **overrides):
    payload = {
        "schema_version": 1,
        "generator_version": "lexical_zipf_v1",
        "query_set_version": "queries_v1",
        "profiles": {
            name: {
                "dataset_sha256": "a" * 64,
                "queries_sha256": "b" * 64,
            }
            for name in load_profiles()
        },
    }
    payload.update(overrides)
    path = tmp_path / "reference_hashes.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


@pytest.mark.unit
@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"schema_version": 2}, "schema_version"),
        ({"generator_version": "other"}, "generator_version"),
        ({"query_set_version": "other"}, "query_set_version"),
    ],
)
def test_reference_hashes_reject_unknown_versions(
    tmp_path,
    overrides,
    message,
):
    path = _write_reference(tmp_path, **overrides)

    with pytest.raises(ValueError, match=message):
        load_reference_hashes(path)


@pytest.mark.unit
def test_reference_hashes_reject_incomplete_profiles(tmp_path):
    payload = {
        "schema_version": 1,
        "generator_version": "lexical_zipf_v1",
        "query_set_version": "queries_v1",
        "profiles": {
            "tiny": {
                "dataset_sha256": "a" * 64,
                "queries_sha256": "b" * 64,
            }
        },
    }
    path = tmp_path / "reference_hashes.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValueError, match="missing"):
        load_reference_hashes(path)


@pytest.mark.unit
def test_reference_hashes_reject_unknown_profiles(tmp_path):
    payload = {
        "schema_version": 1,
        "generator_version": "lexical_zipf_v1",
        "query_set_version": "queries_v1",
        "profiles": {
            **{
                name: {
                    "dataset_sha256": "a" * 64,
                    "queries_sha256": "b" * 64,
                }
                for name in load_profiles()
            },
            "huge": {
                "dataset_sha256": "a" * 64,
                "queries_sha256": "b" * 64,
            },
        },
    }
    path = tmp_path / "reference_hashes.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValueError, match="unknown"):
        load_reference_hashes(path)


@pytest.mark.unit
def test_reference_hashes_reject_malformed_digest(tmp_path):
    payload = {
        "schema_version": 1,
        "generator_version": "lexical_zipf_v1",
        "query_set_version": "queries_v1",
        "profiles": {
            name: {
                "dataset_sha256": "not-a-hash",
                "queries_sha256": "b" * 64,
            }
            for name in load_profiles()
        },
    }
    path = tmp_path / "reference_hashes.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValueError, match="hex hash"):
        load_reference_hashes(path)


@pytest.mark.unit
@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("documents", 0, "documents"),
        ("vocabulary_size", 7, "vocabulary_size"),
        ("min_document_tokens", 0, "document token bounds"),
        ("mode_document_tokens", 13, "document token bounds"),
        ("max_document_tokens", 3, "document token bounds"),
        ("zipf_exponent", 0, "zipf_exponent"),
        ("duplicate_rate", -0.1, "duplicate_rate"),
        ("duplicate_rate", 1.0, "duplicate_rate"),
        ("seed", True, "seed"),
    ],
)
def test_profile_validation_rejects_invalid_values(field, value, message):
    values = _valid_values()
    values[field] = value

    with pytest.raises(ValueError, match=message):
        BenchmarkProfile.from_mapping("invalid", values)


@pytest.mark.unit
def test_profile_validation_reports_missing_fields():
    with pytest.raises(ValueError, match="seed"):
        BenchmarkProfile.from_mapping(
            "missing",
            {
                key: value
                for key, value in _valid_values().items()
                if key != "seed"
            },
        )


@pytest.mark.unit
def test_load_profiles_rejects_unknown_schema(tmp_path):
    path = tmp_path / "profiles.json"
    path.write_text(
        json.dumps({"schema_version": 99, "profiles": {}}),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="schema_version"):
        load_profiles(path)


@pytest.mark.unit
def test_run_config_resolves_default_output():
    config = BenchmarkRunConfig()

    config.validate()

    assert config.resolved_output_dir().name == "results"
    assert config.to_dict()["engines"] == ["core", "lite"]


@pytest.mark.unit
@pytest.mark.parametrize(
    "config",
    [
        BenchmarkRunConfig(profile="unknown"),
        BenchmarkRunConfig(engines=()),
        BenchmarkRunConfig(engines=("core", "core")),
        BenchmarkRunConfig(engines=("other",)),
        BenchmarkRunConfig(warmups=-1),
        BenchmarkRunConfig(repetitions=0),
    ],
)
def test_run_config_rejects_invalid_options(config):
    with pytest.raises(ValueError):
        config.validate()


@pytest.mark.unit
def test_run_config_rejects_output_inside_src():
    source_dir = (
        Path(__file__).parents[2]
        / "src"
        / "benchmark-output"
    )
    config = BenchmarkRunConfig(output_dir=source_dir)

    with pytest.raises(ValueError, match="inside src"):
        config.validate()
