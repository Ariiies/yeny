"""
SQLiteLoadersMixin — Factory methods for SQLite data sources.

Contains the ``from_sqlite_table`` and ``from_sqlite_query`` class
methods that create a ready-to-search Lucis instance by reading rows
directly from a SQLite database via the standard-library ``sqlite3``
module.
"""
from typing import TYPE_CHECKING, Dict, List, Optional, Union

from ...sync.source_spec import SourceSpec
from ..._internals import _build_sql_text_expr

if TYPE_CHECKING:
    from ...main import Lucis


class SQLiteLoadersMixin:
    """Mixin that provides the ``from_sqlite_table`` and ``from_sqlite_query``
    factory methods."""

    @classmethod
    def from_sqlite_table(
        cls,
        table_name: str,
        db_path: str,
        text_column: Union[str, List[str]],
        id_column: Optional[str] = None,
        where_clause: Optional[str] = None,
        name: str = "default",
        **kwargs,
    ) -> "Lucis":
        """
        Create a Lucis instance by reading rows from an existing SQLite table.

        The index is automatically persisted back to the **same** database
        (``storage_type`` defaults to ``"sqlite"``).

        Args:
            table_name: Name of the source table.
            db_path: Path to the SQLite database file.
            text_column: Column name (or list of column names) containing
                the document text.  When a list is given (cross-field
                search), the columns are concatenated with spaces at the
                SQL level.
            id_column: Column to use as document ID (optional).
            where_clause: Optional SQL ``WHERE`` filter (without the ``WHERE`` keyword).
            name: Identifier for the persisted index.
            **kwargs: Extra arguments forwarded to ``Lucis.__init__``.

        Returns:
            A ready-to-search Lucis instance.

        Example::

            luc = Lucis.from_sqlite_table(
                table_name="articles",
                db_path="blog.db",
                text_column="content",
                id_column="article_id",
            )
            results = luc.search("python tutorial")
        """
        import sqlite3 as _sqlite3

        text_expr = _build_sql_text_expr(text_column)
        cols = f"{id_column}, {text_expr}" if id_column else text_expr
        query = f"SELECT {cols} FROM {table_name}"
        if where_clause:
            query += f" WHERE {where_clause}"

        conn = _sqlite3.connect(db_path)
        cursor = conn.execute(query)

        if id_column:
            data: Union[Dict[str, str], List[str]] = {
                str(row[0]): row[1] for row in cursor
            }
        else:
            data = [row[0] for row in cursor]

        conn.close()

        # Default to sqlite storage backed by the same db
        kwargs.setdefault("storage_type", "sqlite")
        kwargs.setdefault("db_path", db_path)
        instance = cls(name=name, autoload=False, **kwargs)
        instance._source_info = SourceSpec(
            type="table",
            table_name=table_name,
            text_column=text_column,
            id_column=id_column,
            date_column=None,
            where_clause=where_clause,
        )
        instance.index(data)
        return instance

    @classmethod
    def from_sqlite_query(
        cls,
        query: str,
        db_path: str,
        name: str = "default",
        **kwargs,
    ) -> "Lucis":
        """
        Create a Lucis instance from an arbitrary SQL ``SELECT`` query.

        * If the query returns **one** column → treated as a list of texts.
        * If it returns **two or more** columns → first column is the ID,
          second column is the text.

        Args:
            query: A ``SELECT`` statement to execute.
            db_path: Path to the SQLite database file.
            name: Identifier for the persisted index.
            **kwargs: Extra arguments forwarded to ``Lucis.__init__``.

        Returns:
            A ready-to-search Lucis instance.

        Example::

            luc = Lucis.from_sqlite_query(
                query=(
                    "SELECT p.id, p.title || ' ' || p.body "
                    "FROM posts p "
                    "WHERE p.published = 1"
                ),
                db_path="forum.db",
                name="published_posts",
            )
        """
        import sqlite3 as _sqlite3

        conn = _sqlite3.connect(db_path)
        cursor = conn.execute(query)

        first_row = cursor.fetchone()
        if first_row is None:
            conn.close()
            raise ValueError("The query returned no results.")

        # Re-execute to include the first row (simplest portable approach)
        cursor = conn.execute(query)

        if len(first_row) == 1:
            data: Union[Dict[str, str], List[str]] = [row[0] for row in cursor]
        else:
            data = {str(row[0]): row[1] for row in cursor}

        conn.close()

        kwargs.setdefault("storage_type", "sqlite")
        kwargs.setdefault("db_path", db_path)
        instance = cls(name=name, autoload=False, **kwargs)
        instance._source_info = SourceSpec(
            type="query",
            query=query,
        )
        instance.index(data)
        return instance
