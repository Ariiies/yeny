"""
Parallel preprocessing utilities for Lucis.

Provides CPU-aware parallel document preprocessing using the best
available concurrency model for the current platform:

* **Linux / fork-based** — ``ProcessPoolExecutor``.  Fork is near-free,
  worker memory is shared copy-on-write, and pure-Python CPU work truly
  runs in parallel (multiple interpreters, no GIL).
* **Windows / macOS (spawn-based)** — ``ThreadPoolExecutor``.  Spawning
  new Python processes has very high overhead (~500 ms per pool creation),
  making it *slower* than sequential for repeated small batches.  Threads
  share the same process so there is zero spawn cost.  Crucially,
  crypto preprocessors (Fernet decrypt, HMAC) are **C extensions that
  release the GIL**, so threads give real parallelism for the dominant
  workload in Lucis.

Falls back transparently to sequential processing when workers = 1 or
the corpus is too small to benefit.

Example::

    from lucis.utils.parallel import parallel_preprocess, get_optimal_workers

    workers = get_optimal_workers("performance")
    tokenized = parallel_preprocess(texts, my_preprocessor, workers=workers)
"""
from __future__ import annotations

import logging
import multiprocessing
import os
import pickle
import sys
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from typing import Any, Callable, List, Optional, Union

logger = logging.getLogger("lucis.parallel")


# ---------------------------------------------------------------------------
# CPU topology helpers
# ---------------------------------------------------------------------------

def get_cpu_count() -> int:
    """Return the number of logical CPUs available.

    Uses ``os.cpu_count()`` with a safe fallback of 2 when the value
    cannot be determined (e.g. containerised environments that mask
    ``/proc/cpuinfo``).

    Returns:
        Number of logical CPU cores (threads).
    """
    return os.cpu_count() or 2


def get_optimal_workers(mode: str = "efficiency") -> int:
    """Choose worker count based on *mode* and available cores.

    Two modes are provided:

    * **efficiency** (default) — ``cores // 2``.  Leaves headroom for
      the OS and other processes.  Best for background indexing while
      the application continues to serve requests.
    * **performance** — ``cores - 1``.  Uses nearly all available CPU
      power.  Best for one-off bulk indexing where latency matters
      and the machine is otherwise idle.

    The result is always ≥ 1.

    Args:
        mode: ``"efficiency"`` or ``"performance"``.

    Returns:
        Recommended number of worker threads/processes.
    """
    cores = get_cpu_count()
    if mode == "performance":
        return max(1, cores - 1)
    # "efficiency" — half the cores
    return max(1, cores // 2)


# ---------------------------------------------------------------------------
# Thresholds
# ---------------------------------------------------------------------------

#: Minimum documents to justify thread-pool overhead (very low — threads
#: are cheap to create and share process memory).
MIN_THREAD_DOCS: int = 200

#: Minimum documents to justify process-pool overhead (process spawn is
#: expensive; only worth it for large batches on Linux/fork).
MIN_PROCESS_DOCS: int = 500


# ---------------------------------------------------------------------------
# Module-level worker helpers (needed by ProcessPoolExecutor — must be
# picklable, i.e. defined at module scope, not as closures).
# ---------------------------------------------------------------------------

_worker_preprocessor: Optional[Callable] = None
_worker_tokenizer: Optional[Callable] = None


def _init_worker(preprocessor_fn: Callable, tokenizer_fn: Callable) -> None:
    """Pool initializer: stash the preprocessor in each worker process."""
    global _worker_preprocessor, _worker_tokenizer
    _worker_preprocessor = preprocessor_fn
    _worker_tokenizer = tokenizer_fn


def _preprocess_doc(doc: str) -> List[str]:
    """Process a single document inside a worker process (ProcessPool)."""
    result = _worker_preprocessor(doc)  # type: ignore[misc]
    if isinstance(result, str):
        return _worker_tokenizer(result)  # type: ignore[misc]
    return result


def _is_picklable(obj: Any) -> bool:
    """Return ``True`` if *obj* can be pickled (required for IPC)."""
    try:
        pickle.dumps(obj, protocol=pickle.HIGHEST_PROTOCOL)
        return True
    except (pickle.PicklingError, TypeError, AttributeError):
        return False


def _get_spawn_method() -> str:
    """Return the effective multiprocessing start method."""
    try:
        return multiprocessing.get_start_method()
    except RuntimeError:
        return "spawn" if os.name == "nt" else "fork"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def parallel_preprocess(
    texts: List[str],
    preprocessor: Callable[[str], Union[str, List[str]]],
    tokenizer: Callable[[str], List[str]],
    *,
    workers: Optional[int] = None,
    mode: str = "efficiency",
    min_docs: int = MIN_THREAD_DOCS,
) -> List[List[str]]:
    """Preprocess *texts* in parallel using the best available executor.

    **Strategy selection** (automatic, no configuration needed):

    * *Fork platforms* (Linux): ``ProcessPoolExecutor`` bypasses the GIL
      entirely.  Used when corpus ≥ ``min_docs`` and preprocessor is
      picklable.
    * *Spawn platforms* (Windows/macOS): ``ThreadPoolExecutor`` with zero
      spawn overhead.  Effective for **crypto-heavy** preprocessors
      (Fernet, HMAC) because their C extensions release the GIL, giving
      true thread-level parallelism.
    * *Fallback*: sequential single-threaded loop.

    Args:
        texts: Raw document strings to preprocess.
        preprocessor: Text preprocessor ``(str) → str | list[str]``.
        tokenizer: Fallback tokenizer applied when *preprocessor* returns
            a ``str`` instead of a ``list[str]``.
        workers: Explicit worker count.  ``None`` uses
            :func:`get_optimal_workers` with the given *mode*.
        mode: ``"efficiency"`` or ``"performance"`` (used when *workers*
            is ``None``).
        min_docs: Minimum corpus size to activate a worker pool.

    Returns:
        List of token lists, one per input document, same order as *texts*.
    """
    n = len(texts)

    if workers is None:
        workers = get_optimal_workers(mode)

    # Always sequential for tiny batches or single-worker config.
    if n < min_docs or workers <= 1:
        return _sequential_preprocess(texts, preprocessor, tokenizer)

    spawn_method = _get_spawn_method()

    # ------------------------------------------------------------------
    # Fork path (Linux): ProcessPoolExecutor — true CPU parallelism.
    # ------------------------------------------------------------------
    if spawn_method == "fork" and multiprocessing.parent_process() is None:
        if not _is_picklable(preprocessor) or not _is_picklable(tokenizer):
            return _sequential_preprocess(texts, preprocessor, tokenizer)

        if n < MIN_PROCESS_DOCS:
            return _sequential_preprocess(texts, preprocessor, tokenizer)

        chunksize = max(64, n // (workers * 4))
        logger.info(
            "ProcessPool preprocessing: %d docs × %d workers (chunksize=%d)",
            n, workers, chunksize,
        )
        try:
            with ProcessPoolExecutor(
                max_workers=workers,
                initializer=_init_worker,
                initargs=(preprocessor, tokenizer),
            ) as pool:
                return list(pool.map(_preprocess_doc, texts, chunksize=chunksize))
        except Exception as exc:
            logger.warning("ProcessPool failed (%s) — falling back.", exc)
            return _sequential_preprocess(texts, preprocessor, tokenizer)

    # ------------------------------------------------------------------
    # Spawn path (Windows/macOS): sequential with LRU-cached preprocessor.
    #
    # Rationale: ThreadPoolExecutor adds scheduling/GIL overhead that
    # dominates for moderate batch sizes (5 K – 20 K docs).  The dominant
    # CPU cost (HMAC per n-gram) is already eliminated by the lru_cache on
    # encrypt_token, so sequential is the fastest choice on spawn platforms.
    # ------------------------------------------------------------------
    return _sequential_preprocess(texts, preprocessor, tokenizer)


def _sequential_preprocess(
    texts: List[str],
    preprocessor: Callable,
    tokenizer: Callable,
) -> List[List[str]]:
    """Sequential preprocessing — single-threaded fallback."""
    tokenized: List[List[str]] = []
    for doc in texts:
        result = preprocessor(doc)
        tokenized.append(tokenizer(result) if isinstance(result, str) else result)
    return tokenized
