"""Timing and statistical helpers for Lucis benchmarks.

The module keeps raw nanosecond samples and derives a small robust summary.
No performance threshold is encoded here; callers decide how to interpret
measurements.
"""

from __future__ import annotations

import math
import statistics
import time
from typing import Any, Callable, Dict, List, Sequence, Tuple, TypeVar


T = TypeVar("T")


def summarize_samples(samples: Sequence[int]) -> Dict[str, float]:
    """Summarize a non-empty sequence of nanosecond measurements.

    Args:
        samples: Positive or zero integer duration samples in nanoseconds.

    Returns:
        Dictionary containing count, minimum, median, p95, and maximum.

    Raises:
        ValueError: If ``samples`` is empty.
    """
    if not samples:
        raise ValueError("samples cannot be empty")

    ordered = sorted(samples)
    p95_index = max(0, math.ceil(len(ordered) * 0.95) - 1)
    return {
        "count": len(ordered),
        "min": float(ordered[0]),
        "median": float(statistics.median(ordered)),
        "p95": float(ordered[p95_index]),
        "max": float(ordered[-1]),
    }


def measure_operation(
    operation: Callable[[], Any],
    repetitions: int = 1,
) -> List[int]:
    """Measure repeated calls using ``time.perf_counter_ns``.

    Args:
        operation: Zero-argument callable to execute.
        repetitions: Number of measured calls.

    Returns:
        Raw elapsed times in nanoseconds, one entry per call.

    Raises:
        ValueError: If ``repetitions`` is not greater than zero.
    """
    if repetitions <= 0:
        raise ValueError("repetitions must be greater than zero")

    samples: List[int] = []
    for _ in range(repetitions):
        started = time.perf_counter_ns()
        operation()
        samples.append(time.perf_counter_ns() - started)
    return samples


def measure_once(operation: Callable[[], T]) -> Tuple[T, int]:
    """Measure one operation while preserving its return value.

    Args:
        operation: Zero-argument callable to execute once.

    Returns:
        Tuple containing the operation result and elapsed nanoseconds.
    """
    started = time.perf_counter_ns()
    value = operation()
    return value, time.perf_counter_ns() - started


def make_measurement(
    name: str,
    samples: Sequence[int],
    *,
    unit: str = "ns",
    **context: Any,
) -> Dict[str, Any]:
    """Create a JSON-ready measurement record.

    Args:
        name: Stable metric name.
        samples: Raw duration or size samples.
        unit: Measurement unit such as ``ns``, ``bytes``, or ``count``.
        **context: Additional fields such as engine or query category.

    Returns:
        Measurement dictionary containing raw samples and summary statistics.
    """
    return {
        "name": name,
        "unit": unit,
        "samples": list(samples),
        "summary": summarize_samples(samples),
        **context,
    }
