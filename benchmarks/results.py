"""Validation and persistence for Lucis benchmark results.

Results are stored as readable JSON and never silently overwrite an earlier
run. Writes use a temporary file followed by ``os.replace`` so readers do not
observe partially-written documents.
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any, Mapping, Sequence


REQUIRED_RESULT_FIELDS = {
    "schema_version",
    "run_id",
    "started_at_utc",
    "environment",
    "configuration",
    "datasets",
    "measurements",
}


def validate_result(result: Mapping[str, Any]) -> None:
    """Validate the structural result contract without extra dependencies.

    Args:
        result: Result object to validate.

    Raises:
        ValueError: If a required field has an invalid type or value.
    """
    if not isinstance(result, Mapping):
        raise ValueError("result must be an object")

    missing = sorted(REQUIRED_RESULT_FIELDS.difference(result))
    if missing:
        raise ValueError(
            f"result is missing fields: {', '.join(missing)}"
        )
    if result["schema_version"] != "1.0":
        raise ValueError("Unsupported result schema_version")
    for field in ("run_id", "started_at_utc"):
        if not isinstance(result[field], str) or not result[field]:
            raise ValueError(f"{field} must be a non-empty string")
    for field in ("environment", "configuration"):
        if not isinstance(result[field], Mapping):
            raise ValueError(f"{field} must be an object")
    for field in ("datasets", "measurements"):
        value = result[field]
        if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
            raise ValueError(f"{field} must be an array")


def _write_atomically(target: Path, text: str) -> None:
    """Write text through a temporary sibling plus ``os.replace``."""
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{target.stem}-",
        suffix=".tmp",
        dir=str(target.parent),
        text=True,
    )
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            stream.write(text)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary_path, target)
    except Exception:
        try:
            temporary_path.unlink()
        except FileNotFoundError:
            pass
        raise


def write_report(markdown: str, result_path: Path) -> Path:
    """Atomically write a Markdown report next to its JSON result.

    Args:
        markdown: Rendered Markdown report text.
        result_path: Path of the JSON result the report belongs to.

    Returns:
        Absolute path of the created ``.md`` file.

    Raises:
        ValueError: If the report file already exists.
        OSError: If the file cannot be written.
    """
    target = result_path.with_suffix(".md")
    if target.exists():
        raise ValueError(f"Report already exists: {target}")
    _write_atomically(target, markdown)
    return target.resolve()


def write_result(
    result: Mapping[str, Any],
    output_dir: Path,
) -> Path:
    """Atomically write one benchmark result as JSON.

    Args:
        result: Validated benchmark result.
        output_dir: Destination directory.

    Returns:
        Absolute path to the created JSON file.

    Raises:
        ValueError: If the result is invalid or the destination already
            exists.
        OSError: If the directory or file cannot be created.
    """
    validate_result(result)
    output_dir.mkdir(parents=True, exist_ok=True)
    target = output_dir / f"lucis-benchmark-{result['run_id']}.json"
    if target.exists():
        raise ValueError(f"Result already exists: {target}")

    descriptor, temporary_name = tempfile.mkstemp(
        prefix=".lucis-benchmark-",
        suffix=".tmp",
        dir=str(output_dir),
        text=True,
    )
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            json.dump(result, stream, indent=2, ensure_ascii=False)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary_path, target)
    except Exception:
        try:
            temporary_path.unlink()
        except FileNotFoundError:
            pass
        raise
    return target.resolve()
