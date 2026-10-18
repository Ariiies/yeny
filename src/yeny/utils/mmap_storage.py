"""
Memory-mapped binary storage for LiteEngine shards (.yny format).

This module provides the binary serialisation layer that writes
``CompactPostings`` and ``CompactDocLengths`` arrays directly to disk in
a contiguous, mmap-friendly layout.  On read, the file is memory-mapped
and the numeric data is accessed through zero-copy ``memoryview`` objects,
so the OS page-cache replaces Python heap as the "container" for the
index.

File layout (.yny — Yeny Compact Shard)::

    ┌──────────────────────────────────────────────┐
    │ MAGIC          4 bytes: b"YNY\\x01"          │
    │ HEADER_LEN     4 bytes: uint32 LE            │
    │ HEADER         variable: JSON (utf-8)        │
    │ [zero-padding to 4 096-byte alignment]       │
    ├──────────────────────────────────────────────┤
    │ PAYLOAD (raw binary)                         │
    │   doc_lengths   total_docs × 4 bytes (I)     │
    │   postings…     per-token:                   │
    │     doc_ids     n × 4 bytes (i, signed)      │
    │     freqs       n × 4 bytes (I, unsigned)    │
    └──────────────────────────────────────────────┘

The header is a JSON object that records offsets into the payload so that
each posting list and the doc-length array can be located by simple byte
arithmetic inside a ``memoryview``.

Only standard-library modules are used (``mmap``, ``array``, ``struct``,
``json``).  No third-party dependency is required.

Typical usage (ShardManager integration)::

    # Write after persist:
    save_yny(path, engine)

    # Read (zero-copy):
    handle = open_yny(path)      # YnyHandle context-manager
    engine = handle.to_engine()  # LiteEngine with MmapPostings
    ...
    handle.close()               # release mmap + file handle
"""
from __future__ import annotations

import array
import json
import logging
import mmap
import os
import struct
from bisect import bisect_left
from typing import Any, Dict, Iterator, Optional, Tuple

from .compact import CompactPostings, CompactDocLengths

log = logging.getLogger("yeny.mmap_storage")

#VConstants 

MAGIC = b"YNY\x01"
_ALIGN = 4096  # payload alignment (OS page size)
_UINT32 = struct.Struct("<I")


#  Zero-copy mmap-backed data structures


class MmapPostings:
    """Posting list backed by a read-only ``memoryview`` into an mmap.

    Duck-types as :class:`CompactPostings` — existing engine code that
    calls ``.get()``, ``.keys()``, ``__contains__`` etc. works with no
    changes.  The actual bytes live in the OS page-cache, not on the
    Python heap.

    Warning:
        Instances are only valid while the parent :class:`YnyHandle` is
        open.  Accessing data after ``handle.close()`` causes a
        ``ValueError``.
    """

    __slots__ = ("_ids_view", "_frq_view", "_len")

    def __init__(
        self,
        ids_view: memoryview,
        frq_view: memoryview,
    ) -> None:
        self._ids_view = ids_view
        self._frq_view = frq_view
        self._len = len(ids_view)

    # Dict-compatible read interface

    def get(self, doc_id: int, default: int = 0) -> int:
        """O(log n) lookup via binary search on the memoryview."""
        idx = bisect_left(self._ids_view, doc_id)
        if idx < self._len and self._ids_view[idx] == doc_id:
            return self._frq_view[idx]
        return default

    def keys(self) -> memoryview:
        return self._ids_view

    def values(self) -> memoryview:
        return self._frq_view

    def items(self) -> Iterator[Tuple[int, int]]:
        return zip(self._ids_view, self._frq_view)

    def __contains__(self, doc_id: int) -> bool:
        idx = bisect_left(self._ids_view, doc_id)
        return idx < self._len and self._ids_view[idx] == doc_id

    def __getitem__(self, doc_id: int) -> int:
        idx = bisect_left(self._ids_view, doc_id)
        if idx < self._len and self._ids_view[idx] == doc_id:
            return self._frq_view[idx]
        raise KeyError(doc_id)

    def __len__(self) -> int:
        return self._len

    def __bool__(self) -> bool:
        return self._len > 0

    def to_dict(self) -> Dict[int, int]:
        """Materialise to a regular dict (needed by ``persist()``)."""
        return {int(k): int(v) for k, v in zip(self._ids_view, self._frq_view)}

    def __repr__(self) -> str:
        return f"MmapPostings(entries={self._len})"


class MmapDocLengths:
    """Doc-length array backed by a read-only ``memoryview`` into an mmap.

    Duck-types as :class:`CompactDocLengths`.
    """

    __slots__ = ("_view",)

    def __init__(self, view: memoryview) -> None:
        self._view = view

    # Dict-compatible read interface 

    def get(self, doc_id: int, default: int = 0) -> int:
        if 0 <= doc_id < len(self._view):
            return self._view[doc_id]
        return default

    def __getitem__(self, doc_id: int) -> int:
        return self._view[doc_id]

    def __setitem__(self, doc_id: int, value: int) -> None:
        raise TypeError("MmapDocLengths is read-only (backed by mmap)")

    def __len__(self) -> int:
        return len(self._view)

    def __bool__(self) -> bool:
        return len(self._view) > 0

    def keys(self) -> range:
        return range(len(self._view))

    def values(self) -> memoryview:
        return self._view

    def items(self) -> Iterator[Tuple[int, int]]:
        return enumerate(self._view)

    def to_dict(self) -> Dict[int, int]:
        """Materialise to a regular dict (needed by ``persist()``)."""
        return {i: int(v) for i, v in enumerate(self._view)}

    def __repr__(self) -> str:
        return f"MmapDocLengths(size={len(self._view)})"


class LazyIndex:
    """Dict-like container that creates :class:`MmapPostings` on demand.

    Instead of pre-allocating ``MmapPostings`` objects (and 2 memoryview
    sub-slices each) for *every* token in the vocabulary, this class
    stores only the compact metadata arrays.  A ``MmapPostings`` is
    materialised only when the token is actually accessed — and it is
    **not cached**, so the objects can be GC'd immediately after use.

    Memory savings are dramatic: for 75 shards × 15 K tokens × 2
    memoryviews × 184 bytes ≈ 414 MB of ``memoryview`` object shells
    are completely eliminated.

    The caller (``LiteEngine.search``) should pre-fetch postings for the
    query tokens into a local dict to avoid re-creating them in the
    inner scoring loop.

    Duck-types as ``Dict[str, MmapPostings]`` — all existing engine code
    that uses ``engine.index`` works unchanged.
    """

    __slots__ = ("_token_idx", "_ids_off", "_ids_n", "_payload", "_n_tokens")

    def __init__(
        self,
        tokens: list,
        ids_off: "array.array",
        ids_n: "array.array",
        payload: memoryview,
    ) -> None:
        self._token_idx: Dict[str, int] = {t: i for i, t in enumerate(tokens)}
        self._ids_off = ids_off    # array('I') – byte offset of doc_ids
        self._ids_n = ids_n        # array('I') – count of entries
        self._payload = payload    # shared payload memoryview
        self._n_tokens = len(tokens)

    # private helper

    def _make(self, idx: int) -> MmapPostings:
        """Create a fresh ``MmapPostings`` for vocab index *idx*."""
        off = self._ids_off[idx]
        n = self._ids_n[idx]
        ids_view = self._payload[off: off + n * 4].cast("i")
        frq_view = self._payload[off + n * 4: off + n * 8].cast("i")
        return MmapPostings(ids_view, frq_view)

    # dict interface

    def __getitem__(self, token: str) -> MmapPostings:
        return self._make(self._token_idx[token])

    def __contains__(self, token: str) -> bool:
        return token in self._token_idx

    def get(self, token: str, default: Any = None) -> Any:
        idx = self._token_idx.get(token)
        if idx is not None:
            return self._make(idx)
        return default

    def keys(self) -> Any:
        return self._token_idx.keys()

    def values(self) -> Iterator[MmapPostings]:
        for i in range(self._n_tokens):
            yield self._make(i)

    def items(self) -> Iterator[Tuple[str, MmapPostings]]:
        for token, idx in self._token_idx.items():
            yield token, self._make(idx)

    def __len__(self) -> int:
        return self._n_tokens

    def __bool__(self) -> bool:
        return self._n_tokens > 0

    def clear(self) -> None:
        """Release internal references (used by ``YnyHandle.close()``)."""
        self._token_idx.clear()
        self._payload = None

    def __repr__(self) -> str:
        return f"LazyIndex(tokens={self._n_tokens})"


class MmapIdMap:
    """Id-map backed by a read-only ``memoryview`` into an mmap.

    For ``id_type="str"`` the payload contains:
    - An offset table: ``(total_docs + 1) × uint32`` — byte offsets
      into the string-data region.
    - String data: concatenated UTF-8 encoded original IDs.

    Access is O(1): ``id_map[doc_id]`` → decodes only the requested
    string from the mmap.  No Python ``dict`` or ``str`` objects are
    kept in the heap until actually requested.

    For ``id_type="int"`` the payload is a flat ``int64`` array — O(1),
    no decoding needed.

    Duck-types as a dict where ``engine.id_map`` is expected.
    """

    __slots__ = ("_offsets_view", "_strings_view", "_int_view", "_len", "_id_type")

    def __init__(
        self,
        id_type: str,
        size: int,
        offsets_view: Optional[memoryview] = None,
        strings_view: Optional[memoryview] = None,
        int_view: Optional[memoryview] = None,
    ) -> None:
        self._id_type = id_type
        self._len = size
        self._offsets_view = offsets_view   # cast('I') → uint32
        self._strings_view = strings_view   # raw bytes
        self._int_view = int_view           # cast('q') → int64

    def __getitem__(self, doc_id: int) -> Any:
        if self._id_type == "int":
            return int(self._int_view[doc_id])
        # str type: offset table → string bytes
        start = self._offsets_view[doc_id]
        end = self._offsets_view[doc_id + 1]
        return bytes(self._strings_view[start:end]).decode("utf-8")

    def get(self, doc_id: int, default: Any = None) -> Any:
        if 0 <= doc_id < self._len:
            return self[doc_id]
        return default

    def __contains__(self, doc_id: int) -> bool:
        return 0 <= doc_id < self._len

    def __len__(self) -> int:
        return self._len

    def __bool__(self) -> bool:
        return self._len > 0

    def keys(self) -> range:
        return range(self._len)

    def values(self) -> Iterator:
        for i in range(self._len):
            yield self[i]

    def items(self) -> Iterator[Tuple[int, Any]]:
        for i in range(self._len):
            yield i, self[i]

    def update(self, other: Any) -> None:
        raise TypeError("MmapIdMap is read-only (backed by mmap)")

    def to_dict(self) -> Dict[int, Any]:
        """Materialise to a regular dict (needed by ``persist()``)."""
        return {i: self[i] for i in range(self._len)}

    def __repr__(self) -> str:
        return f"MmapIdMap(size={self._len}, id_type='{self._id_type}')"

#  YNY file handle (context-manager for mmap lifecycle)

class YnyHandle:
    """Context-manager that owns the mmap and file descriptor.

    While open, the ``.index``, ``.doc_lengths``, ``.id_map``,
    ``.total_docs``, and ``.id_type`` attributes expose the engine
    state using zero-copy mmap views.  Call ``.close()`` (or exit the
    ``with`` block) to release OS resources.
    """

    def __init__(self, path: str) -> None:
        self.path = path
        self._file = None
        self._mm = None
        self._payload_view: Optional[memoryview] = None
        # Engine state (populated by _parse)
        self.total_docs: int = 0
        self.id_type: str = "none"
        self.id_map: Dict[int, Any] = {}
        self.index: Dict[str, MmapPostings] = {}
        self.doc_lengths: Optional[MmapDocLengths] = None
        self.doc_norms: Optional[Dict[int, float]] = None
        self._open()

    # Lifecycle management

    def _open(self) -> None:
        self._file = open(self.path, "rb")
        # Validate magic
        magic = self._file.read(4)
        if magic != MAGIC:
            self._file.close()
            raise ValueError(
                f"Not a valid .yny file (bad magic): {self.path}"
            )
        # Read header length
        header_len = _UINT32.unpack(self._file.read(4))[0]
        header_bytes = self._file.read(header_len)
        header = json.loads(header_bytes.decode("utf-8"))

        # Memory-map the entire file (read-only)
        self._mm = mmap.mmap(
            self._file.fileno(), 0, access=mmap.ACCESS_READ,
        )
        payload_offset = header["payload_offset"]
        self._payload_view = memoryview(self._mm)[payload_offset:]

        # Deserialise metadata (kept in Python heap — small)
        self.total_docs = header["total_docs"]
        self.id_type = header.get("id_type", "none")

        # id_map: zero-copy if binary format (v2+), dict fallback (v1)
        version = header.get("version", 1)
        idmap_bin = header.get("id_map_bin")

        if idmap_bin and idmap_bin.get("type") == "str":
            # String id_map: offset table + packed strings → MmapIdMap
            im_off = idmap_bin["offset"]
            n_docs = idmap_bin["count"]
            off_bytes = idmap_bin["offsets_bytes"]
            str_bytes = idmap_bin["strings_bytes"]
            offsets_view = self._payload_view[im_off: im_off + off_bytes].cast("I")
            str_start = im_off + off_bytes
            strings_view = self._payload_view[str_start: str_start + str_bytes]
            self.id_map = MmapIdMap(
                id_type="str", size=n_docs,
                offsets_view=offsets_view, strings_view=strings_view,
            )
        elif idmap_bin and idmap_bin.get("type") == "int":
            # Integer id_map: flat int64 array → MmapIdMap
            im_off = idmap_bin["offset"]
            n_docs = idmap_bin["count"]
            int_bytes = idmap_bin["int_bytes"]
            int_view = self._payload_view[im_off: im_off + int_bytes].cast("q")
            self.id_map = MmapIdMap(
                id_type="int", size=n_docs, int_view=int_view,
            )
        elif idmap_bin and idmap_bin.get("type") == "none":
            self.id_map = {}
        else:
            # v1 fallback: id_map was in JSON header
            raw_id_map = header.get("id_map", {})
            self.id_map = {int(k): v for k, v in raw_id_map.items()}

        #  doc_lengths: zero-copy view 
        dl = header["doc_lengths"]
        dl_start = dl["offset"]
        dl_bytes = dl["count"] * 4
        self.doc_lengths = MmapDocLengths(
            self._payload_view[dl_start: dl_start + dl_bytes].cast("I")
        )

        #  inverted index: LazyIndex (zero per-token heap cost) 
        vocab_meta = header["vocab"]
        tokens = sorted(vocab_meta.keys())
        ids_off_arr = array.array("I", (vocab_meta[t]["ids_off"] for t in tokens))
        ids_n_arr = array.array("I", (vocab_meta[t]["ids_n"] for t in tokens))
        self.index = LazyIndex(tokens, ids_off_arr, ids_n_arr, self._payload_view)

        # doc_norms (v3+): compact float64 array or legacy doc_vectors 
        norms_header = header.get("doc_norms")
        if norms_header:
            # New format: flat float64 array
            n_off = norms_header["offset"]
            n_count = norms_header["count"]
            n_bytes = n_count * 8
            if n_off + n_bytes <= len(self._payload_view):
                norms_view = self._payload_view[n_off: n_off + n_bytes].cast("d")
                self.doc_norms = {
                    i: float(v) for i, v in enumerate(norms_view) if v > 0
                }
            else:
                log.warning(
                    "doc_norms section out of bounds in %s — will be recomputed.",
                    self.path,
                )
                self.doc_norms = None
        else:
            # Backward compat: old v3 with doc_vectors JSON blob
            dv_header = header.get("doc_vectors")
            if dv_header:
                dv_off = dv_header["offset"]
                dv_len = dv_header["length"]
                if dv_len > 0 and dv_off + dv_len <= len(self._payload_view):
                    try:
                        dv_bytes = bytes(self._payload_view[dv_off: dv_off + dv_len])
                        raw = json.loads(dv_bytes.decode("utf-8"))
                        from math import sqrt as _sqrt
                        self.doc_norms = {
                            int(k): _sqrt(sum(s * s for s in v.values()))
                            for k, v in raw.items()
                        }
                    except (json.JSONDecodeError, UnicodeDecodeError):
                        log.warning(
                            "Corrupt doc_vectors in %s — norms will be recomputed.",
                            self.path,
                        )
                        self.doc_norms = None
                else:
                    log.warning(
                        "doc_vectors section out of bounds in %s — norms will be recomputed.",
                        self.path,
                    )
                    self.doc_norms = None

    def close(self) -> None:
        """Release mmap and file handle.

        All ``MmapPostings`` and ``MmapDocLengths`` views are
        invalidated first so that no memoryview keeps the mmap alive.
        Safe to call multiple times.
        """
        # Release inverted index
        if isinstance(self.index, LazyIndex):
            self.index.clear()
        else:
            for postings in self.index.values():
                if hasattr(postings, "_ids_view") and postings._ids_view is not None:
                    postings._ids_view.release()
                    postings._ids_view = None
                if hasattr(postings, "_frq_view") and postings._frq_view is not None:
                    postings._frq_view.release()
                    postings._frq_view = None
            self.index.clear()
        self.index = {}
        # Release doc_lengths memoryview
        if self.doc_lengths is not None:
            view = getattr(self.doc_lengths, "_view", None)
            if view is not None:
                view.release()
                self.doc_lengths._view = None
            self.doc_lengths = None
        # Release id_map memoryviews (MmapIdMap)
        if isinstance(self.id_map, MmapIdMap):
            for attr in ("_offsets_view", "_strings_view", "_int_view"):
                view = getattr(self.id_map, attr, None)
                if view is not None:
                    view.release()
                    setattr(self.id_map, attr, None)
            self.id_map = {}
        # Release the payload-level memoryview
        if self._payload_view is not None:
            self._payload_view.release()
            self._payload_view = None
        # Close mmap + file descriptor
        if self._mm is not None:
            try:
                self._mm.close()
            except BufferError:
                # External memoryview references (e.g. from LazyIndex
                # MmapPostings still in scope) prevent immediate close.
                # The OS will reclaim the mapping when the process exits
                # or when all views are garbage-collected.
                pass
            self._mm = None
        if self._file is not None:
            self._file.close()
            self._file = None

    def __enter__(self) -> "YnyHandle":
        return self

    def __exit__(self, *exc: Any) -> None:
        self.close()

    def __del__(self) -> None:
        # Safety net — rely on explicit close() in production.
        try:
            self.close()
        except Exception:
            pass

#  Serialisation (write path)

def save_yny(path: str, engine: Any) -> None:
    """Serialise an engine to ``.yny``.

    Supports both *LiteEngine* and *CoreEngine*.  When the engine
    exposes a non-empty ``doc_norms`` attribute the L2 norms are
    packed as a flat float64 array in the payload (version 3).
    LiteEngine (which has no ``doc_norms``) produces a version-2
    file as before.

    The engine's compact arrays are written with ``array.tofile()`` for
    maximum throughput.  The JSON header is kept small and contains only
    offsets + metadata.

    Args:
        path: Destination file path (should end with ``.yny``).
        engine: A built engine whose ``index`` values are
            :class:`CompactPostings` and whose ``doc_lengths`` is a
            :class:`CompactDocLengths` (or objects with the same
            internal layout: ``._doc_ids``, ``._freqs``, ``._data``).
    """
    # 1. Collect sorted token list (deterministic output) 
    tokens = sorted(engine.index.keys())

    # 2. Compute payload layout 
    offset = 0  # running offset within the payload section

    # doc_lengths comes first
    dl_data = getattr(engine.doc_lengths, "_data", None)
    if dl_data is None:
        # Fallback: if doc_lengths is a dict, convert
        dl_data = array.array("I", bytes(4 * engine.total_docs))
        for doc_id, length in engine.doc_lengths.items():
            dl_data[int(doc_id)] = int(length)
    dl_offset = offset
    dl_count = len(dl_data)
    offset += dl_count * 4

    # id_map: serialise into binary payload
    # For str values: offset_table (N+1 × uint32) + packed strings
    # For int values: flat int64 array
    id_type = getattr(engine, "id_type", "none")
    id_map_raw = engine.id_map
    idmap_meta: Dict[str, Any] = {"offset": offset}

    if id_type in ("str", "custom") and id_map_raw:
        n_docs = engine.total_docs
        # Build string data + offset table
        string_parts: list = []
        offsets_arr = array.array("I")
        running = 0
        for i in range(n_docs):
            val = id_map_raw.get(i, "")
            if val is None:
                encoded = b""
            else:
                encoded = val.encode("utf-8") if isinstance(val, str) else str(val).encode("utf-8")
            offsets_arr.append(running)
            string_parts.append(encoded)
            running += len(encoded)
        offsets_arr.append(running)  # sentinel for last entry
        idmap_meta["type"] = "str"
        idmap_meta["count"] = n_docs
        idmap_meta["offsets_bytes"] = len(offsets_arr) * 4
        idmap_meta["strings_bytes"] = running
        offset += len(offsets_arr) * 4 + running
    elif id_type == "int" and id_map_raw:
        n_docs = engine.total_docs
        int_arr = array.array("q", (int(id_map_raw.get(i, 0)) for i in range(n_docs)))
        idmap_meta["type"] = "int"
        idmap_meta["count"] = n_docs
        idmap_meta["int_bytes"] = n_docs * 8
        offset += n_docs * 8
    else:
        idmap_meta["type"] = "none"
        idmap_meta["count"] = 0

    # Postings: collect (token, ids_array, freqs_array, offsets)
    vocab: Dict[str, Dict[str, int]] = {}
    posting_arrays = []  # list of (ids_arr, freqs_arr) in token order
    for token in tokens:
        postings = engine.index[token]
        # Extract raw arrays (works for CompactPostings and MmapPostings)
        ids_arr = getattr(postings, "_doc_ids", None)
        frq_arr = getattr(postings, "_freqs", None)
        if ids_arr is None:
            # Fallback: materialise from dict-like interface
            items = sorted(postings.items())
            ids_arr = array.array("i", (k for k, _ in items))
            frq_arr = array.array("I", (v for _, v in items))
        n = len(ids_arr)
        vocab[token] = {
            "ids_off": offset,
            "ids_n": n,
            "frq_off": offset + n * 4,
            "frq_n": n,
        }
        posting_arrays.append((ids_arr, frq_arr))
        offset += n * 4 * 2  # ids + freqs

    # 2b. doc_norms (CoreEngine only) 
    # L2 norms of TF-IDF vectors: serialised as a flat float64 array.
    # Only included when the engine has non-empty doc_norms.
    raw_doc_norms = getattr(engine, "doc_norms", None)
    has_norms = bool(raw_doc_norms)
    norms_meta: Dict[str, Any] = {}
    norms_arr = None
    if has_norms:
        norms_arr = array.array("d", [0.0] * engine.total_docs)
        for doc_id, norm in raw_doc_norms.items():
            norms_arr[int(doc_id)] = norm
        norms_meta = {"offset": offset, "count": engine.total_docs}
        offset += engine.total_docs * 8

    # 3. Build header JSON 
    file_version = 3 if has_norms else 2
    header_dict = {
        "version": file_version,
        "total_docs": engine.total_docs,
        "id_type": id_type,
        "id_map_bin": idmap_meta,
        "doc_lengths": {"offset": dl_offset, "count": dl_count},
        "vocab": vocab,
        "payload_offset": 0,
    }
    if has_norms:
        header_dict["doc_norms"] = norms_meta
    # Compute payload_offset safely: use a large placeholder first so
    # the header is at its maximum possible size.  The real payload_offset
    # will have equal or fewer digits → the final header always fits.
    header_dict["payload_offset"] = 99_999_999_999  # 11-digit placeholder
    header_bytes = json.dumps(header_dict, ensure_ascii=False).encode("utf-8")
    raw_header_size = 4 + 4 + len(header_bytes)  # magic + header_len + body
    payload_offset = ((raw_header_size + _ALIGN - 1) // _ALIGN) * _ALIGN
    header_dict["payload_offset"] = payload_offset
    header_bytes = json.dumps(header_dict, ensure_ascii=False).encode("utf-8")

    # 4. Write the file
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "wb") as f:
        # Magic
        f.write(MAGIC)
        # Header length
        f.write(_UINT32.pack(len(header_bytes)))
        # Header body
        f.write(header_bytes)
        # Padding to alignment
        written = 4 + 4 + len(header_bytes)
        pad = payload_offset - written
        if pad > 0:
            f.write(b"\x00" * pad)
        # Payload: doc_lengths
        dl_data.tofile(f)
        # Payload: id_map binary
        if idmap_meta["type"] == "str":
            offsets_arr.tofile(f)
            for part in string_parts:
                f.write(part)
        elif idmap_meta["type"] == "int":
            int_arr.tofile(f)
        # Payload: postings
        for ids_arr, frq_arr in posting_arrays:
            ids_arr.tofile(f)
            frq_arr.tofile(f)
        # Payload: doc_norms (v3+)
        if norms_arr is not None:
            norms_arr.tofile(f)


def open_yny(path: str) -> YnyHandle:
    """Open a ``.yny`` file and return a handle with mmap-backed views.

    Args:
        path: Path to the ``.yny`` file.

    Returns:
        An :class:`YnyHandle` whose ``.index``, ``.doc_lengths``, etc.
        attributes are ready to use.  Call ``.close()`` when done.
    """
    return YnyHandle(path)


def yny_exists(path: str) -> bool:
    """Return ``True`` if *path* exists and starts with the YNY magic."""
    if not os.path.isfile(path):
        return False
    try:
        with open(path, "rb") as f:
            return f.read(4) == MAGIC
    except OSError:
        return False
