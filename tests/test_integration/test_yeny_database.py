"""Integration coverage for Yeny' database facade workflows.

The source database is always a temporary SQLite file.  This exercises the
real :class:`DatabaseReader` and persistence paths without requiring a network
service.  SQLite's schema model is intentionally limited; ``schema=None`` is
covered as the portable/default schema case, while named PostgreSQL/MySQL
schemas remain a dialect-specific concern.
"""

from __future__ import annotations

from pathlib import Path

import pytest

sqlalchemy = pytest.importorskip("sqlalchemy")
from sqlalchemy import create_engine, text

from yeny import Yeny, MetadataStorage
from yeny.config import YenyOptions, TableConfig, TableSource


@pytest.fixture
def alchemy_source(tmp_path: Path) -> tuple[str, Path]:
    """Create a deterministic source table spanning multiple month shards."""
    db_path = tmp_path / "source.db"
    url = f"sqlite:///{db_path}"
    engine = create_engine(url)
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                CREATE TABLE articles (
                    id INTEGER PRIMARY KEY,
                    title TEXT NOT NULL,
                    body TEXT NOT NULL,
                    tags TEXT,
                    active INTEGER NOT NULL,
                    created_at TEXT,
                    published_at TEXT
                )
                """
            )
        )
        connection.execute(
            text(
                """
                INSERT INTO articles
                    (id, title, body, tags, active, created_at, published_at)
                VALUES
                    (1, 'Python basics', 'friendly language tutorial',
                     'programming beginner', 1, '2026-01-03', '2025-11-10'),
                    (2, 'Database guide', 'sqlite persistence patterns',
                     'storage sql', 1, '2026-02-07', '2025-12-12'),
                    (3, 'Python search', 'cross field indexing',
                     'yeny advanced', 1, '2026-03-09', '2026-01-14'),
                    (4, 'Hidden draft', 'unpublished secret material',
                     'draft', 0, NULL, NULL)
                """
            )
        )
    engine.dispose()
    return url, db_path


def _result_ids(instance: Yeny, query: str, **kwargs) -> list[str]:
    return [str(item.doc_id) for item in instance.search(query, **kwargs).results]


def _close_instance(instance: Yeny) -> None:
    instance.close()
    close_storage = getattr(instance.storage, "close", None)
    if close_storage is not None:
        close_storage()


@pytest.mark.integration
def test_table_non_sharded_cross_field_where_and_default_schema(
    alchemy_source: tuple[str, Path], tmp_path: Path
) -> None:
    """Cover E, H, I, J and K with SQLite's portable ``schema=None``."""
    url, _ = alchemy_source
    instance = Yeny.from_table(
        TableSource(
            table="articles",
            connection_url=url,
            text_columns=["title", "body", "tags"],
            id_column="id",
            date_column=None,
        ),
        name="plain_articles",
        engine="core",
        config=TableConfig(
            where_clause="active = 1",
            schema=None,
            stream_ordered=False,
        ),
        options=YenyOptions(storage_dir=str(tmp_path / "plain-index")),
    )

    try:
        assert instance.is_indexed is True
        assert instance.is_sharded is False
        assert instance.total_docs == 3
        assert _result_ids(instance, "advanced") == ["3"]
        assert _result_ids(instance, "secret") == []
        assert instance._source_info is not None
        assert instance._source_info.schema is None
    finally:
        _close_instance(instance)


@pytest.mark.integration
def test_table_auto_detects_date_column_and_builds_shards(
    alchemy_source: tuple[str, Path], tmp_path: Path
) -> None:
    """Cover F and post-index searchability with automatic date detection."""
    url, _ = alchemy_source
    instance = Yeny.from_table(
        TableSource("articles", url, "body", id_column="id"),
        name="auto_dates",
        engine="lite",
        options=YenyOptions(storage_dir=str(tmp_path / "auto-index")),
    )

    try:
        assert instance._source_info is not None
        assert instance._source_info.date_column == "created_at"
        assert instance.is_sharded is True
        assert instance.total_docs == 4
        assert instance._shard_manager is not None
        assert instance._shard_manager.shard_keys == [
            "2026_01",
            "2026_02",
            "2026_03",
            "9999_99",
        ]
        assert _result_ids(instance, "friendly") == ["1"]
    finally:
        _close_instance(instance)


@pytest.mark.integration
def test_table_custom_date_column(
    alchemy_source: tuple[str, Path], tmp_path: Path
) -> None:
    """Cover G by routing with an explicitly selected date column."""
    url, _ = alchemy_source
    instance = Yeny.from_table(
        TableSource(
            "articles",
            url,
            "body",
            id_column="id",
            date_column="published_at",
        ),
        name="published_dates",
        config=TableConfig(where_clause="active = 1"),
        options=YenyOptions(storage_dir=str(tmp_path / "published-index")),
    )

    try:
        assert instance._source_info is not None
        assert instance._source_info.date_column == "published_at"
        assert instance._shard_manager is not None
        assert instance._shard_manager.shard_keys == [
            "2025_11",
            "2025_12",
            "2026_01",
        ]
    finally:
        _close_instance(instance)


@pytest.mark.integration
@pytest.mark.parametrize(
    ("limit_argument", "limit_value"),
    [("max_loaded_shards", 1), ("memory_limit_mb", 1)],
)
def test_table_memory_management_and_streaming(
    alchemy_source: tuple[str, Path],
    tmp_path: Path,
    limit_argument: str,
    limit_value: int,
) -> None:
    """Cover L, M and N for both supported memory-management controls."""
    url, _ = alchemy_source
    option_values = {
        limit_argument: limit_value,
        "storage_dir": str(tmp_path / f"managed-{limit_argument}"),
    }
    instance = Yeny.from_table(
        TableSource(
            "articles",
            url,
            "body",
            id_column="id",
            date_column="created_at",
        ),
        name=f"managed_{limit_argument}",
        engine="lite",
        config=TableConfig(
            where_clause="active = 1",
            shard_batch_size=1,
            stream_ordered=True,
        ),
        options=YenyOptions(**option_values),
    )

    try:
        assert instance._shard_manager is not None
        assert instance._shard_manager._is_managed is True
        assert instance.total_docs == 3
        assert _result_ids(
            instance,
            "friendly",
            since="2026-01",
            until="2026-01",
        ) == ["1"]
    finally:
        _close_instance(instance)


@pytest.mark.integration
def test_database_binary_directory_auto_and_metadata_storage(
    alchemy_source: tuple[str, Path], tmp_path: Path
) -> None:
    """Cover O and the MetadataStorage creation half of Q."""
    url, _ = alchemy_source
    storage_dir = tmp_path / "auto-binary"
    instance = Yeny.from_table(
        TableSource(
            "articles", url, "body", id_column="id", date_column=None
        ),
        name="auto_binary",
        engine="lite",
        options=YenyOptions(storage_dir=str(storage_dir)),
    )

    try:
        expected_binary_dir = storage_dir / "yny"
        assert instance._binary_dir == str(expected_binary_dir)
        assert isinstance(instance.storage, MetadataStorage)
        assert Path(instance.storage.db_path) == expected_binary_dir / "yeny_meta.db"
        assert list(expected_binary_dir.glob("auto_binary__v*.yny"))
    finally:
        _close_instance(instance)


@pytest.mark.integration
def test_database_custom_binary_directory(
    alchemy_source: tuple[str, Path], tmp_path: Path
) -> None:
    """Cover P with a binary directory independent of ``storage_dir``."""
    url, _ = alchemy_source
    binary_dir = tmp_path / "custom-yny"
    instance = Yeny.from_table(
        TableSource(
            "articles", url, "body", id_column="id", date_column=None
        ),
        name="custom_binary",
        engine="lite",
        options=YenyOptions(
            storage_dir=str(tmp_path / "unused-storage"),
            binary_dir=str(binary_dir),
        ),
    )

    try:
        assert instance._binary_dir == str(binary_dir)
        assert Path(instance.storage.db_path) == binary_dir / "yeny_meta.db"
        assert list(binary_dir.glob("custom_binary__v*.yny"))
    finally:
        _close_instance(instance)


@pytest.mark.integration
def test_database_roundtrip_auto_discovers_metadata_and_preserves_results(
    alchemy_source: tuple[str, Path], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Cover Q, R and S, including ranked IDs, scores and source metadata."""
    url, _ = alchemy_source
    monkeypatch.chdir(tmp_path)
    built = Yeny.from_table(
        TableSource(
            "articles",
            url,
            ["title", "body"],
            id_column="id",
            date_column="created_at",
        ),
        name="roundtrip_articles",
        engine="lite",
    )
    queries = ["python", "persistence", "indexing"]
    expected = {
        query: [(str(item.doc_id), item.score) for item in built.search(query).results]
        for query in queries
    }
    expected_source = built._source_info
    expected_keys = built._shard_manager.shard_keys

    _close_instance(built)
    reloaded = Yeny(name="roundtrip_articles", engine="lite")
    try:
        actual = {
            query: [(str(item.doc_id), item.score) for item in reloaded.search(query).results]
            for query in queries
        }
        assert actual == expected
        assert reloaded.is_indexed is True
        assert reloaded._source_info == expected_source
        assert reloaded._shard_manager is not None
        assert reloaded._shard_manager.shard_keys == expected_keys
        assert reloaded.total_docs == 4
        assert isinstance(reloaded.storage, MetadataStorage)
    finally:
        _close_instance(reloaded)


@pytest.mark.integration
def test_database_query_builds_and_reloads(
    alchemy_source: tuple[str, Path], tmp_path: Path
) -> None:
    """Complete the SQLAlchemy factory coverage with the arbitrary-query path."""
    url, _ = alchemy_source
    storage_dir = tmp_path / "query-index"
    built = Yeny.from_query(
        "SELECT id, title FROM articles WHERE active = 1 ORDER BY id",
        url,
        name="active_query",
        engine="core",
        options=YenyOptions(storage_dir=str(storage_dir)),
    )
    try:
        assert built.is_indexed is True
        assert built._source_info is not None
        assert built._source_info.type == "query"
        assert _result_ids(built, "Python") == ["1", "3"]
    finally:
        _close_instance(built)

    reloaded = Yeny(
        name="active_query",
        engine="core",
        options=YenyOptions(storage_dir=str(storage_dir)),
    )
    try:
        assert reloaded._source_info is not None
        assert reloaded._source_info.query.startswith("SELECT id, title")
        assert _result_ids(reloaded, "Database") == ["2"]
    finally:
        _close_instance(reloaded)
