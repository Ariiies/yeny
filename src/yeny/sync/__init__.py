"""
yeny.sync — Data synchronization layer.

This package provides the building blocks for automatic index
synchronization with external data sources:

- ``SourceSpec``: structured description of a data source.
- ``data_providers``: full-corpus fetch factories.
- ``delta_providers``: incremental delta factories.
- ``change_detectors``: count-based change detection factories.

These components are consumed by ``AutomationMixin.create_worker()``
to auto-generate the callables that power ``IndexWorker``.
"""
from .source_spec import SourceSpec
from .data_providers import build_data_fn, build_streaming_fn
from .delta_providers import build_delta_fn
from .change_detectors import build_change_detector

__all__ = [
    "SourceSpec",
    "build_data_fn",
    "build_streaming_fn",
    "build_delta_fn",
    "build_change_detector",
]
