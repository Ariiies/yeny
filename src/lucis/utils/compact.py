"""
Compact data structures for memory-efficient indexing.

Replaces Python ``dict`` posting lists and doc-length maps with
``array.array``-backed structures.  On a 2M-document index this
reduces RAM from ~3.5 GB to ~300–400 MB (≈ 90 % saving) because
Python dicts carry ~100 bytes overhead **per entry** whereas
``array.array`` stores values in a contiguous C buffer at 4 bytes each.

Both classes duck-type as read-only dicts so existing code that
calls ``.get()``, ``.keys()``, ``.items()`` keeps working.

Internals
---------
* **CompactPostings**: sorted parallel arrays (doc_ids + freqs).
  Lookup is O(log n) via ``bisect`` instead of O(1) dict, but the
  constant factor is far smaller due to cache-friendly memory layout.

* **CompactDocLengths**: a flat ``array.array('I')`` indexed directly
  by doc_id (0 … N-1).  Lookup is O(1).
"""
from __future__ import annotations

import array
from bisect import bisect_left
from typing import Any, Dict, Iterator, Tuple


# Compact Posting List 

class CompactPostings:
    """Memory-efficient posting list using sorted parallel arrays.

    Replaces ``Dict[int, int]`` — same read interface, ~12× less RAM.

    Internal layout::

        _doc_ids:  [3, 17, 42, 999, ...]   ← sorted
        _freqs:    [2,  1,  5,   3, ...]   ← parallel
    """

    __slots__ = ("_doc_ids", "_freqs", "_len")

    def __init__(
        self,
        doc_ids: "array.array[int]",
        freqs: "array.array[int]",
    ) -> None:
        self._doc_ids = doc_ids
        self._freqs = freqs
        self._len = len(doc_ids)

    # ── Constructors ──

    @classmethod
    def from_dict(cls, d: Dict[int, int]) -> "CompactPostings":
        """Freeze a ``{doc_id: freq}`` dict into compact form.

        Handles string keys transparently (common after JSON
        deserialization).
        """
        if not d:
            return cls(array.array("i"), array.array("I"))
        items = sorted((int(k), int(v)) for k, v in d.items())
        return cls(
            array.array("i", (k for k, _ in items)),
            array.array("I", (v for _, v in items)),
        )

    # Dict-compatible read interface

    def get(self, doc_id: int, default: int = 0) -> int:
        """O(log n) lookup via binary search."""
        idx = bisect_left(self._doc_ids, doc_id)
        if idx < self._len and self._doc_ids[idx] == doc_id:
            return self._freqs[idx]
        return default

    def keys(self) -> "array.array[int]":
        return self._doc_ids

    def values(self) -> "array.array[int]":
        return self._freqs

    def items(self) -> Iterator[Tuple[int, int]]:
        return zip(self._doc_ids, self._freqs)

    def __contains__(self, doc_id: int) -> bool:
        idx = bisect_left(self._doc_ids, doc_id)
        return idx < self._len and self._doc_ids[idx] == doc_id

    def __getitem__(self, doc_id: int) -> int:
        idx = bisect_left(self._doc_ids, doc_id)
        if idx < self._len and self._doc_ids[idx] == doc_id:
            return self._freqs[idx]
        raise KeyError(doc_id)

    def __len__(self) -> int:
        return self._len

    def __bool__(self) -> bool:
        return self._len > 0

    # Serialization

    def to_dict(self) -> Dict[int, int]:
        """Thaw back to a regular dict (for storage serialization)."""
        return {int(k): int(v) for k, v in zip(self._doc_ids, self._freqs)}

    def __repr__(self) -> str:
        return f"CompactPostings(entries={self._len})"


# Compact Document Lengths

class CompactDocLengths:
    """Flat array of document lengths, indexed by doc_id.

    Replaces ``Dict[int, int]`` — same read interface, ~25× less RAM.

    Works because internal doc_ids are always 0 … N-1, so direct
    array indexing replaces dict hashing.
    """

    __slots__ = ("_data",)

    def __init__(self, data: "array.array[int]") -> None:
        self._data = data

    # Constructor

    @classmethod
    def from_dict(cls, d: Dict[int, int], total_docs: int) -> "CompactDocLengths":
        """Convert a ``{doc_id: length}`` dict to compact form.

        Handles string keys transparently (common after JSON
        deserialization).
        """
        arr = array.array("I", bytes(4 * total_docs))  # zero-initialized
        for doc_id, length in d.items():
            arr[int(doc_id)] = int(length)
        return cls(arr)

    # Dict-compatible read interface

    def get(self, doc_id: int, default: int = 0) -> int:
        if 0 <= doc_id < len(self._data):
            return self._data[doc_id]
        return default

    def __getitem__(self, doc_id: int) -> int:
        return self._data[doc_id]

    def __setitem__(self, doc_id: int, value: int) -> None:
        # Support incremental add_documents — extend if needed
        if doc_id >= len(self._data):
            extend_size = doc_id - len(self._data) + 1
            self._data.extend(array.array("I", bytes(4 * extend_size)))
        self._data[doc_id] = value

    def __len__(self) -> int:
        return len(self._data)

    def __bool__(self) -> bool:
        return len(self._data) > 0

    def keys(self) -> range:
        return range(len(self._data))

    def values(self) -> "array.array[int]":
        return self._data

    def items(self) -> Iterator[Tuple[int, int]]:
        return enumerate(self._data)

    # Serialization

    def to_dict(self) -> Dict[int, int]:
        """Thaw back to a regular dict (for storage serialization)."""
        return {i: int(v) for i, v in enumerate(self._data)}

    def __repr__(self) -> str:
        return f"CompactDocLengths(size={len(self._data)})"


# Helpers

def freeze_index(
    index: Dict[str, Dict[int, int]],
) -> Dict[str, CompactPostings]:
    """Convert an entire inverted index from dicts to compact postings."""
    return {
        word: CompactPostings.from_dict(postings)
        for word, postings in index.items()
    }


def thaw_index(
    index: Dict[str, CompactPostings],
) -> Dict[str, Dict[int, int]]:
    """Convert an entire compact index back to regular dicts."""
    return {
        word: postings.to_dict() if isinstance(postings, CompactPostings) else dict(postings)
        for word, postings in index.items()
    }


def freeze_doc_lengths(
    doc_lengths: Dict[int, int],
    total_docs: int,
) -> CompactDocLengths:
    """Convert doc_lengths dict to compact array."""
    return CompactDocLengths.from_dict(doc_lengths, total_docs)
