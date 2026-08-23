"""Tests for persistence and mmap benchmark scenarios."""

import pytest

from lucis import Lucis
from lucis.utils.nlp import WordTokenizer

from benchmarks.config import load_profiles
from benchmarks.datasets import generate_dataset
from benchmarks.queries import build_queries
from benchmarks.scenarios.mmap_load import (
    measure_lcs_write,
    measure_mmap_load,
)
from benchmarks.scenarios.persistence import (
    measure_json_save,
    measure_sqlite_save,
    measure_standard_load,
)
from benchmarks.scenarios.roundtrip import (
    SCORE_ABS_TOLERANCE,
    collect_result_sequence,
    verify_roundtrip,
)


@pytest.fixture()
def tiny_dataset():
    profiles = load_profiles()
    return generate_dataset(profiles["tiny"])


@pytest.fixture()
def tiny_queries(tiny_dataset):
    return build_queries(tiny_dataset)


def _indexed(tmp_path, dataset, name="scenario", **overrides):
    options = {
        "name": name,
        "engine": "core",
        "storage_dir": str(tmp_path / name),
        "preprocessor": WordTokenizer(),
        "autoload": False,
        "binary_dir": None,
    }
    options.update(overrides)
    lucis = Lucis(**options)
    lucis.index(dataset.documents, persist=False)
    return lucis


def _entry(doc_id, score):
    return {"doc_id": doc_id, "score": score}


@pytest.mark.unit
def test_verify_roundtrip_accepts_identical_results():
    expected = {
        "q1": [_entry("doc_a", 0.5), _entry("doc_b", 0.25)],
        "q2": [],
    }

    verified = verify_roundtrip(
        expected,
        {"q1": [_entry("doc_a", 0.5), _entry("doc_b", 0.25)], "q2": []},
        backend="json",
    )

    assert verified == 2


@pytest.mark.unit
def test_verify_roundtrip_rejects_query_set_mismatch():
    with pytest.raises(ValueError, match="query sets"):
        verify_roundtrip({"q1": []}, {"q2": []}, backend="json")


@pytest.mark.unit
def test_verify_roundtrip_rejects_result_count_change():
    with pytest.raises(RuntimeError, match="result count"):
        verify_roundtrip(
            {"q1": [_entry("doc_a", 0.5)]},
            {"q1": [_entry("doc_a", 0.5), _entry("doc_b", 0.1)]},
            backend="json",
        )


@pytest.mark.unit
def test_verify_roundtrip_rejects_changed_doc_id():
    with pytest.raises(RuntimeError, match="ranking.*position 0"):
        verify_roundtrip(
            {"q1": [_entry("doc_a", 0.5)]},
            {"q1": [_entry("doc_b", 0.5)]},
            backend="sqlite",
        )


@pytest.mark.unit
def test_verify_roundtrip_rejects_reordered_ids():
    with pytest.raises(RuntimeError, match="ranking.*position 0"):
        verify_roundtrip(
            {"q1": [_entry("doc_a", 0.9), _entry("doc_b", 0.8)]},
            {"q1": [_entry("doc_b", 0.8), _entry("doc_a", 0.9)]},
            backend="mmap",
        )


@pytest.mark.unit
def test_verify_roundtrip_rejects_score_beyond_tolerance():
    with pytest.raises(RuntimeError, match="score"):
        verify_roundtrip(
            {"q1": [_entry("doc_a", 0.5)]},
            {"q1": [_entry("doc_a", 0.500001)]},
            backend="json",
        )


@pytest.mark.unit
def test_verify_roundtrip_accepts_score_within_tolerance():
    expected = {"q1": [_entry("doc_a", 0.5)]}
    tolerated = 0.5 + SCORE_ABS_TOLERANCE / 2

    verified = verify_roundtrip(
        expected,
        {"q1": [_entry("doc_a", tolerated)]},
        backend="json",
    )

    assert verified == 1


@pytest.mark.integration
def test_collect_result_sequence_preserves_ranking_and_scores(
    tmp_path,
    tiny_dataset,
    tiny_queries,
):
    lucis = _indexed(tmp_path, tiny_dataset)
    try:
        collected = collect_result_sequence(lucis, tiny_queries)
    finally:
        lucis.close()

    assert set(collected) == {
        query.query_id for query in tiny_queries.items
    }
    assert collected["no_result_00"] == []
    for entries in collected.values():
        scores = [entry["score"] for entry in entries]
        assert scores == sorted(scores, reverse=True)
        assert all(isinstance(entry["score"], float) for entry in entries)
        assert all(entry["doc_id"].startswith("doc_") for entry in entries)
    rare_entries = collected["rare_00"]
    assert rare_entries
    assert len({entry["doc_id"] for entry in rare_entries}) == len(
        rare_entries
    )


@pytest.mark.integration
def test_json_save_reports_real_artifact_size(tmp_path, tiny_dataset):
    lucis = _indexed(tmp_path, tiny_dataset)
    try:
        measurements = measure_json_save(lucis, engine="core")
    finally:
        lucis.close()

    by_name = {item["name"]: item for item in measurements}
    assert by_name["json_save"]["unit"] == "ns"
    artifact = tmp_path / "scenario" / "scenario.json"
    assert artifact.exists()
    size = by_name["json_artifact_size"]
    assert size["unit"] == "bytes"
    assert size["samples"] == [artifact.stat().st_size]


@pytest.mark.integration
def test_sqlite_save_reports_real_artifact_size(tmp_path, tiny_dataset):
    db_dir = tmp_path / "sqlite"
    db_dir.mkdir()
    lucis = _indexed(
        tmp_path,
        tiny_dataset,
        name="sqlite_case",
        storage_type="sqlite",
        db_path=str(db_dir / "benchmark.db"),
    )
    try:
        measurements = measure_sqlite_save(lucis, engine="core")
    finally:
        lucis.storage.close()

    by_name = {item["name"]: item for item in measurements}
    assert by_name["sqlite_save"]["unit"] == "ns"
    size = by_name["sqlite_artifact_size"]
    assert size["unit"] == "bytes"
    assert size["samples"][0] >= (db_dir / "benchmark.db").stat().st_size


@pytest.mark.integration
def test_lcs_write_reports_real_artifact_size(tmp_path, tiny_dataset):
    lucis = _indexed(tmp_path, tiny_dataset)
    lcs_path = tmp_path / "lcs" / "scenario.lcs"
    try:
        measurements = measure_lcs_write(lucis, lcs_path, engine="core")
    finally:
        lucis.close()

    by_name = {item["name"]: item for item in measurements}
    assert by_name["lcs_write"]["unit"] == "ns"
    assert lcs_path.exists()
    size = by_name["lcs_artifact_size"]
    assert size["unit"] == "bytes"
    assert size["samples"] == [lcs_path.stat().st_size]


@pytest.mark.integration
def test_standard_load_roundtrip_preserves_ids(
    tmp_path,
    tiny_dataset,
    tiny_queries,
):
    built = _indexed(tmp_path, tiny_dataset, name="loadable")
    built.save()
    expected = collect_result_sequence(built, tiny_queries)
    built.close()

    measurements = measure_standard_load(
        "json",
        lambda: Lucis(
            name="loadable",
            engine="core",
            storage_dir=str(tmp_path / "loadable"),
            preprocessor=WordTokenizer(),
            autoload=True,
            binary_dir=None,
        ),
        engine="core",
        queries=tiny_queries,
        expected_results=expected,
        warmups=1,
        repetitions=2,
    )

    names = [item["name"] for item in measurements]
    assert "load_standard" in names
    assert "search_first_after_load" in names
    assert "search_warm_after_load" in names
    roundtrip = next(
        item for item in measurements if item["name"] == "roundtrip_verified"
    )
    assert roundtrip["unit"] == "count"
    assert roundtrip["samples"] == [len(tiny_queries.items)]
    assert all(item.get("backend") == "json" for item in measurements)


@pytest.mark.integration
def test_standard_load_detects_changed_results(
    tmp_path,
    tiny_dataset,
    tiny_queries,
):
    built = _indexed(tmp_path, tiny_dataset, name="tampered")
    built.save()
    expected = collect_result_sequence(built, tiny_queries)
    built.close()
    expected["rare_00"] = [{"doc_id": "doc_999999", "score": 1.0}]

    with pytest.raises(RuntimeError, match="json round-trip"):
        measure_standard_load(
            "json",
            lambda: Lucis(
                name="tampered",
                engine="core",
                storage_dir=str(tmp_path / "tampered"),
                preprocessor=WordTokenizer(),
                autoload=True,
                binary_dir=None,
            ),
            engine="core",
            queries=tiny_queries,
            expected_results=expected,
            warmups=0,
            repetitions=1,
        )


@pytest.mark.integration
def test_mmap_load_roundtrip_preserves_ids_and_closes_handle(
    tmp_path,
    tiny_dataset,
    tiny_queries,
):
    built = _indexed(tmp_path, tiny_dataset, name="mmap_case")
    lcs_path = tmp_path / "lcs" / "case.lcs"
    built.engine.save_binary(str(lcs_path))
    expected = collect_result_sequence(built, tiny_queries)
    built.close()

    holder = []

    def constructor():
        instance = Lucis(
            name="mmap_fresh",
            engine="core",
            storage_dir=str(tmp_path / "fresh"),
            preprocessor=WordTokenizer(),
            autoload=False,
            binary_dir=None,
        )
        holder.append(instance)
        return instance

    measurements = measure_mmap_load(
        constructor,
        lcs_path,
        engine="core",
        queries=tiny_queries,
        expected_results=expected,
        warmups=1,
        repetitions=2,
    )

    names = [item["name"] for item in measurements]
    assert "mmap_load" in names
    assert "search_first_mmap" in names
    assert "search_warm_mmap" in names
    roundtrip = next(
        item for item in measurements if item["name"] == "roundtrip_verified"
    )
    assert roundtrip["backend"] == "mmap"
    assert roundtrip["samples"] == [len(tiny_queries.items)]
    assert holder[0].engine._lcs_handle is None

    lcs_path.unlink()
    assert not lcs_path.exists()
