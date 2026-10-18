"""
LoaderMixin — Factory methods for creating Yeny instances from data sources.

Thin facade that composes the specialized per-source-type loader
mixins into the single ``LoaderMixin`` consumed by ``Yeny``. Each
concrete ``from_*`` factory method lives in its own module so that a
bug or a new source type stays isolated to a single file:

- ``BasicLoadersMixin`` (``loaders_basic.py``): ``from_dict``, ``from_list``.
- ``SQLiteLoadersMixin`` (``loaders_sqlite.py``): ``from_sqlite_table``,
  ``from_sqlite_query``.
- ``DatabaseLoadersMixin`` (``loaders_db.py``): ``from_table``, ``from_query``.
"""
from .loaders_basic import BasicLoadersMixin
from .loaders_sqlite import SQLiteLoadersMixin
from .loaders_db import DatabaseLoadersMixin


class LoaderMixin(BasicLoadersMixin, SQLiteLoadersMixin, DatabaseLoadersMixin):
    """Mixin that provides ``from_*`` factory class methods.

    These methods create a new ``Yeny`` instance, ingest data from
    the specified source, persist the index, and return it ready to
    search.

    All methods are ``@classmethod`` — they receive ``cls`` (which is
    ``Yeny`` at runtime due to MRO) and delegate to ``index()``,
    ``save()``, and internal helpers defined on the full class.

    Public intent (source, name, engine, and preprocessor) stays explicit;
    advanced infrastructure is carried by ``YenyOptions`` and database table
    tuning by ``TableConfig``.  The factories deliberately avoid
    catch-all ``**kwargs`` so misspelled options fail immediately.

    This class itself only composes the three source-specific mixins
    above; it does not define any behavior of its own.
    """
