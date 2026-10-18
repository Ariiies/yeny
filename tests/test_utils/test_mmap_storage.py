
import array
import json
import os
import tempfile
from pathlib import Path

import pytest

from yeny.utils.mmap_storage import (
    LazyIndex,
    YnyHandle,
    MmapDocLengths,
    MmapIdMap,
    MmapPostings,
    yny_exists,
    open_yny,
    save_yny,
)
from yeny.utils.compact import CompactDocLengths, CompactPostings

@pytest.fixture
def temp_yny_file(tmp_path):
    return tmp_path / "test.yny"

@pytest.fixture
def sample_engine_data():
    return {
        "index": {
            "python": CompactPostings.from_dict({0: 5, 1: 3, 2: 1}),
            "java": CompactPostings.from_dict({1: 2, 2: 4}),
            "javascript": CompactPostings.from_dict({0: 1, 2: 3}),
        },
        "doc_lengths": CompactDocLengths.from_dict({0: 10, 1: 20, 2: 15}, total_docs=3),
        "total_docs": 3,
        "id_type": "none",
        "id_map": {},
        "doc_norms": {},
    }

class MockEngine:
    
    def __init__(self, index, doc_lengths, total_docs, id_type="none", id_map=None, doc_norms=None):
        self.index = index
        self.doc_lengths = doc_lengths
        self.total_docs = total_docs
        self.id_type = id_type
        self.id_map = id_map or {}
        self.doc_norms = doc_norms or {}

class TestSaveYny:

    def test_creates_file_magic_bytes(self, temp_yny_file):
        engine = MockEngine(
            index={"python": CompactPostings.from_dict({0: 1})},
            doc_lengths=CompactDocLengths.from_dict({0: 10}, total_docs=1),
            total_docs=1
        )
        save_yny(str(temp_yny_file), engine)
        
        assert temp_yny_file.exists()
        with open(temp_yny_file, "rb") as f:
            magic = f.read(4)
            assert magic == b"YNY\x01"

    def test_header_withtiene_metadata(self, temp_yny_file):
        engine = MockEngine(
            index={"python": CompactPostings.from_dict({0: 5, 1: 3})},
            doc_lengths=CompactDocLengths.from_dict({0: 10, 1: 20}, total_docs=2),
            total_docs=2
        )
        save_yny(str(temp_yny_file), engine)
        
        with open(temp_yny_file, "rb") as f:
            magic = f.read(4)
            assert magic == b"YNY\x01"
            header_len = int.from_bytes(f.read(4), "little")
            header_bytes = f.read(header_len)
            header = json.loads(header_bytes.decode("utf-8"))
            
            assert header["total_docs"] == 2
            assert header["version"] in [2, 3]
            assert "vocab" in header
            assert "doc_lengths" in header

    def test_payload_aligned_4096(self, temp_yny_file):
        engine = MockEngine(
            index={"python": CompactPostings.from_dict({0: 1})},
            doc_lengths=CompactDocLengths.from_dict({0: 10}, total_docs=1),
            total_docs=1
        )
        save_yny(str(temp_yny_file), engine)
        
        with open(temp_yny_file, "rb") as f:
            magic = f.read(4)
            header_len = int.from_bytes(f.read(4), "little")
            header_bytes = f.read(header_len)
            header = json.loads(header_bytes.decode("utf-8"))
            
            payload_offset = header["payload_offset"]
            assert payload_offset % 4096 == 0

    def test_serializes_doc_lengths(self, temp_yny_file):
        engine = MockEngine(
            index={"python": CompactPostings.from_dict({0: 1})},
            doc_lengths=CompactDocLengths.from_dict({0: 10, 1: 20}, total_docs=2),
            total_docs=2
        )
        save_yny(str(temp_yny_file), engine)
        
        handle = open_yny(str(temp_yny_file))
        assert handle.doc_lengths.get(0) == 10
        assert handle.doc_lengths.get(1) == 20
        handle.close()

    def test_serializes_inverted_index(self, temp_yny_file):
        engine = MockEngine(
            index={
                "python": CompactPostings.from_dict({0: 5, 1: 3}),
                "java": CompactPostings.from_dict({1: 2, 2: 4})
            },
            doc_lengths=CompactDocLengths.from_dict({0: 10, 1: 20, 2: 15}, total_docs=3),
            total_docs=3
        )
        save_yny(str(temp_yny_file), engine)
        
        handle = open_yny(str(temp_yny_file))
        assert "python" in handle.index
        assert "java" in handle.index
        assert handle.index["python"].get(0) == 5
        assert handle.index["java"].get(2) == 4
        handle.close()

    def test_serializes_id_map_str(self, temp_yny_file):
        engine = MockEngine(
            index={"python": CompactPostings.from_dict({0: 1})},
            doc_lengths=CompactDocLengths.from_dict({0: 10, 1: 20}, total_docs=2),
            total_docs=2,
            id_type="str",
            id_map={0: "doc1", 1: "doc2"}
        )
        save_yny(str(temp_yny_file), engine)
        
        handle = open_yny(str(temp_yny_file))
        assert handle.id_map[0] == "doc1"
        assert handle.id_map[1] == "doc2"
        handle.close()

    def test_serializes_id_map_int(self, temp_yny_file):
        engine = MockEngine(
            index={"python": CompactPostings.from_dict({0: 1})},
            doc_lengths=CompactDocLengths.from_dict({0: 10, 1: 20}, total_docs=2),
            total_docs=2,
            id_type="int",
            id_map={0: 100, 1: 200}
        )
        save_yny(str(temp_yny_file), engine)
        
        handle = open_yny(str(temp_yny_file))
        assert handle.id_map[0] == 100
        assert handle.id_map[1] == 200
        handle.close()

    def test_serializes_doc_norms(self, temp_yny_file):
        engine = MockEngine(
            index={"python": CompactPostings.from_dict({0: 1})},
            doc_lengths=CompactDocLengths.from_dict({0: 10, 1: 20}, total_docs=2),
            total_docs=2,
            doc_norms={0: 1.5, 1: 2.3}
        )
        save_yny(str(temp_yny_file), engine)
        
        handle = open_yny(str(temp_yny_file))
        assert handle.doc_norms is not None
        assert handle.doc_norms[0] == 1.5
        assert handle.doc_norms[1] == 2.3
        handle.close()

    def test_creates_directories_if_not_exist(self, tmp_path):
        deep_path = tmp_path / "deep" / "nested" / "dir" / "test.yny"
        engine = MockEngine(
            index={"python": CompactPostings.from_dict({0: 1})},
            doc_lengths=CompactDocLengths.from_dict({0: 10}, total_docs=1),
            total_docs=1
        )
        save_yny(str(deep_path), engine)
        assert deep_path.exists()

class TestOpenYny:

    def test_abre_file_valid(self, temp_yny_file):
        engine = MockEngine(
            index={"python": CompactPostings.from_dict({0: 1})},
            doc_lengths=CompactDocLengths.from_dict({0: 10}, total_docs=1),
            total_docs=1
        )
        save_yny(str(temp_yny_file), engine)
        
        handle = open_yny(str(temp_yny_file))
        assert handle is not None
        assert handle.total_docs == 1
        handle.close()

    def test_rejects_magic_incorrect(self, tmp_path):
        bad_file = tmp_path / "bad.yny"
        with open(bad_file, "wb") as f:
            f.write(b"NOTYNY")
        
        with pytest.raises(ValueError, match="Not a valid .yny file"):
            open_yny(str(bad_file))

    def test_file_inexisting(self):
        with pytest.raises(FileNotFoundError):
            open_yny("/nonexistent/path/file.yny")

    def test_reads_total_docs_correctly(self, temp_yny_file):
        engine = MockEngine(
            index={"python": CompactPostings.from_dict({0: 1})},
            doc_lengths=CompactDocLengths.from_dict({0: 10, 1: 20, 2: 15}, total_docs=3),
            total_docs=3
        )
        save_yny(str(temp_yny_file), engine)
        
        handle = open_yny(str(temp_yny_file))
        assert handle.total_docs == 3
        handle.close()

    def test_reads_id_type_correctly(self, temp_yny_file):
        engine = MockEngine(
            index={"python": CompactPostings.from_dict({0: 1})},
            doc_lengths=CompactDocLengths.from_dict({0: 10}, total_docs=1),
            total_docs=1,
            id_type="str"
        )
        save_yny(str(temp_yny_file), engine)
        
        handle = open_yny(str(temp_yny_file))
        assert handle.id_type == "str"
        handle.close()

    def test_loads_doc_lengths_as_mmap(self, temp_yny_file):
        engine = MockEngine(
            index={"python": CompactPostings.from_dict({0: 1})},
            doc_lengths=CompactDocLengths.from_dict({0: 10, 1: 20}, total_docs=2),
            total_docs=2
        )
        save_yny(str(temp_yny_file), engine)
        
        handle = open_yny(str(temp_yny_file))
        assert isinstance(handle.doc_lengths, MmapDocLengths)
        assert handle.doc_lengths.get(0) == 10
        assert handle.doc_lengths.get(1) == 20
        handle.close()

    def test_loads_index_as_lazand_index(self, temp_yny_file):
        engine = MockEngine(
            index={
                "python": CompactPostings.from_dict({0: 5, 1: 3}),
                "java": CompactPostings.from_dict({1: 2})
            },
            doc_lengths=CompactDocLengths.from_dict({0: 10, 1: 20}, total_docs=2),
            total_docs=2
        )
        save_yny(str(temp_yny_file), engine)
        
        handle = open_yny(str(temp_yny_file))
        assert isinstance(handle.index, LazyIndex)
        assert "python" in handle.index
        assert "java" in handle.index
        handle.close()

    def test_loads_id_map_str_as_mmap(self, temp_yny_file):
        engine = MockEngine(
            index={"python": CompactPostings.from_dict({0: 1})},
            doc_lengths=CompactDocLengths.from_dict({0: 10}, total_docs=1),
            total_docs=1,
            id_type="str",
            id_map={0: "doc1", 1: "doc2"}
        )
        save_yny(str(temp_yny_file), engine)
        
        handle = open_yny(str(temp_yny_file))
        assert isinstance(handle.id_map, MmapIdMap)
        assert handle.id_map[0] == "doc1"
        handle.close()

    def test_loads_id_map_int_as_mmap(self, temp_yny_file):
        engine = MockEngine(
            index={"python": CompactPostings.from_dict({0: 1})},
            doc_lengths=CompactDocLengths.from_dict({0: 10}, total_docs=1),
            total_docs=1,
            id_type="int",
            id_map={0: 100, 1: 200}
        )
        save_yny(str(temp_yny_file), engine)
        
        handle = open_yny(str(temp_yny_file))
        assert isinstance(handle.id_map, MmapIdMap)
        assert handle.id_map[0] == 100
        handle.close()

    def test_loads_doc_norms_if_exist(self, temp_yny_file):
        engine = MockEngine(
            index={"python": CompactPostings.from_dict({0: 1})},
            doc_lengths=CompactDocLengths.from_dict({0: 10, 1: 20}, total_docs=2),
            total_docs=2,
            doc_norms={0: 1.5, 1: 2.3}
        )
        save_yny(str(temp_yny_file), engine)
        
        handle = open_yny(str(temp_yny_file))
        assert handle.doc_norms is not None
        assert handle.doc_norms[0] == 1.5
        handle.close()

class TestMmapPostings:

    def test_get_works_correctly(self, temp_yny_file):
        engine = MockEngine(
            index={"python": CompactPostings.from_dict({0: 5, 1: 3, 2: 1})},
            doc_lengths=CompactDocLengths.from_dict({0: 10, 1: 20, 2: 15}, total_docs=3),
            total_docs=3
        )
        save_yny(str(temp_yny_file), engine)
        
        handle = open_yny(str(temp_yny_file))
        postings = handle.index["python"]
        
        assert postings.get(0) == 5
        assert postings.get(1) == 3
        assert postings.get(2) == 1
        assert postings.get(99) == 0
        handle.close()

    def test_keys_values_items(self, temp_yny_file):
        engine = MockEngine(
            index={"python": CompactPostings.from_dict({0: 5, 1: 3})},
            doc_lengths=CompactDocLengths.from_dict({0: 10, 1: 20}, total_docs=2),
            total_docs=2
        )
        save_yny(str(temp_yny_file), engine)
        
        handle = open_yny(str(temp_yny_file))
        postings = handle.index["python"]
        
        keys = list(postings.keys())
        assert list(keys) == [0, 1]
        
        values = list(postings.values())
        assert list(values) == [5, 3]
        
        items = list(postings.items())
        assert items == [(0, 5), (1, 3)]
        handle.close()

    def test_withtains(self, temp_yny_file):
        engine = MockEngine(
            index={"python": CompactPostings.from_dict({0: 5, 1: 3})},
            doc_lengths=CompactDocLengths.from_dict({0: 10, 1: 20}, total_docs=2),
            total_docs=2
        )
        save_yny(str(temp_yny_file), engine)
        
        handle = open_yny(str(temp_yny_file))
        postings = handle.index["python"]
        
        assert 0 in postings
        assert 1 in postings
        assert 99 not in postings
        handle.close()

    def test_getitem_and_keyerror(self, temp_yny_file):
        engine = MockEngine(
            index={"python": CompactPostings.from_dict({0: 5})},
            doc_lengths=CompactDocLengths.from_dict({0: 10}, total_docs=1),
            total_docs=1
        )
        save_yny(str(temp_yny_file), engine)
        
        handle = open_yny(str(temp_yny_file))
        postings = handle.index["python"]
        
        assert postings[0] == 5
        with pytest.raises(KeyError):
            _ = postings[99]
        handle.close()

    def test_to_dict_materializa(self, temp_yny_file):
        engine = MockEngine(
            index={"python": CompactPostings.from_dict({0: 5, 1: 3})},
            doc_lengths=CompactDocLengths.from_dict({0: 10, 1: 20}, total_docs=2),
            total_docs=2
        )
        save_yny(str(temp_yny_file), engine)
        
        handle = open_yny(str(temp_yny_file))
        postings = handle.index["python"]
        result = postings.to_dict()
        
        assert isinstance(result, dict)
        assert result == {0: 5, 1: 3}
        handle.close()

class TestMmapDocLengths:

    def test_get_works(self, temp_yny_file):
        engine = MockEngine(
            index={"python": CompactPostings.from_dict({0: 1})},
            doc_lengths=CompactDocLengths.from_dict({0: 10, 1: 20, 2: 15}, total_docs=3),
            total_docs=3
        )
        save_yny(str(temp_yny_file), engine)
        
        handle = open_yny(str(temp_yny_file))
        assert handle.doc_lengths.get(0) == 10
        assert handle.doc_lengths.get(1) == 20
        assert handle.doc_lengths.get(2) == 15
        handle.close()

    def test_getitem(self, temp_yny_file):
        engine = MockEngine(
            index={"python": CompactPostings.from_dict({0: 1})},
            doc_lengths=CompactDocLengths.from_dict({0: 10, 1: 20}, total_docs=2),
            total_docs=2
        )
        save_yny(str(temp_yny_file), engine)
        
        handle = open_yny(str(temp_yny_file))
        assert handle.doc_lengths[0] == 10
        assert handle.doc_lengths[1] == 20
        handle.close()

    def test_setitem_lanza_typeerror(self, temp_yny_file):
        engine = MockEngine(
            index={"python": CompactPostings.from_dict({0: 1})},
            doc_lengths=CompactDocLengths.from_dict({0: 10}, total_docs=1),
            total_docs=1
        )
        save_yny(str(temp_yny_file), engine)
        
        handle = open_yny(str(temp_yny_file))
        with pytest.raises(TypeError, match="read-only"):
            handle.doc_lengths[0] = 100
        handle.close()

    def test_to_dict(self, temp_yny_file):
        engine = MockEngine(
            index={"python": CompactPostings.from_dict({0: 1})},
            doc_lengths=CompactDocLengths.from_dict({0: 10, 1: 20}, total_docs=2),
            total_docs=2
        )
        save_yny(str(temp_yny_file), engine)
        
        handle = open_yny(str(temp_yny_file))
        result = handle.doc_lengths.to_dict()
        assert result == {0: 10, 1: 20}
        handle.close()

class TestMmapIdMap:

    def test_getitem_type_int(self, temp_yny_file):
        engine = MockEngine(
            index={"python": CompactPostings.from_dict({0: 1})},
            doc_lengths=CompactDocLengths.from_dict({0: 10, 1: 20}, total_docs=2),
            total_docs=2,
            id_type="int",
            id_map={0: 100, 1: 200}
        )
        save_yny(str(temp_yny_file), engine)
        
        handle = open_yny(str(temp_yny_file))
        assert handle.id_map[0] == 100
        assert handle.id_map[1] == 200
        handle.close()

    def test_getitem_type_str_decodifica(self, temp_yny_file):
        engine = MockEngine(
            index={"python": CompactPostings.from_dict({0: 1})},
            doc_lengths=CompactDocLengths.from_dict({0: 10, 1: 20}, total_docs=2),
            total_docs=2,
            id_type="str",
            id_map={0: "doc1", 1: "doc2"}
        )
        save_yny(str(temp_yny_file), engine)
        
        handle = open_yny(str(temp_yny_file))
        assert handle.id_map[0] == "doc1"
        assert handle.id_map[1] == "doc2"
        handle.close()

    def test_get_with_default(self, temp_yny_file):
        engine = MockEngine(
            index={"python": CompactPostings.from_dict({0: 1})},
            doc_lengths=CompactDocLengths.from_dict({0: 10}, total_docs=1),
            total_docs=1,
            id_type="int",
            id_map={0: 100}
        )
        save_yny(str(temp_yny_file), engine)
        
        handle = open_yny(str(temp_yny_file))
        assert handle.id_map.get(0) == 100
        assert handle.id_map.get(99, -1) == -1
        handle.close()

    def test_withtains(self, temp_yny_file):
        engine = MockEngine(
            index={"python": CompactPostings.from_dict({0: 1})},
            doc_lengths=CompactDocLengths.from_dict({0: 10}, total_docs=2),
            total_docs=2,
            id_type="int",
            id_map={0: 100, 1: 200}
        )
        save_yny(str(temp_yny_file), engine)
        
        handle = open_yny(str(temp_yny_file))
        assert 0 in handle.id_map
        assert 1 in handle.id_map
        assert 99 not in handle.id_map
        handle.close()

    def test_to_dict(self, temp_yny_file):
        engine = MockEngine(
            index={"python": CompactPostings.from_dict({0: 1})},
            doc_lengths=CompactDocLengths.from_dict({0: 10}, total_docs=2),
            total_docs=2,
            id_type="int",
            id_map={0: 100, 1: 200}
        )
        save_yny(str(temp_yny_file), engine)
        
        handle = open_yny(str(temp_yny_file))
        result = handle.id_map.to_dict()
        assert result == {0: 100, 1: 200}
        handle.close()

class TestLazyIndex:

    def test_getitem_creates_mmap_postings(self, temp_yny_file):
        engine = MockEngine(
            index={"python": CompactPostings.from_dict({0: 5, 1: 3})},
            doc_lengths=CompactDocLengths.from_dict({0: 10, 1: 20}, total_docs=2),
            total_docs=2
        )
        save_yny(str(temp_yny_file), engine)
        
        handle = open_yny(str(temp_yny_file))
        postings = handle.index["python"]
        assert isinstance(postings, MmapPostings)
        assert postings.get(0) == 5
        handle.close()

    def test_withtains(self, temp_yny_file):
        engine = MockEngine(
            index={"python": CompactPostings.from_dict({0: 1})},
            doc_lengths=CompactDocLengths.from_dict({0: 10}, total_docs=1),
            total_docs=1
        )
        save_yny(str(temp_yny_file), engine)
        
        handle = open_yny(str(temp_yny_file))
        assert "python" in handle.index
        assert "java" not in handle.index
        handle.close()

    def test_get_with_default(self, temp_yny_file):
        engine = MockEngine(
            index={"python": CompactPostings.from_dict({0: 1})},
            doc_lengths=CompactDocLengths.from_dict({0: 10}, total_docs=1),
            total_docs=1
        )
        save_yny(str(temp_yny_file), engine)
        
        handle = open_yny(str(temp_yny_file))
        result = handle.index.get("python")
        assert isinstance(result, MmapPostings)
        
        result = handle.index.get("nonexistent", "default")
        assert result == "default"
        handle.close()

    def test_keys_values_items(self, temp_yny_file):
        engine = MockEngine(
            index={
                "python": CompactPostings.from_dict({0: 1}),
                "java": CompactPostings.from_dict({1: 2})
            },
            doc_lengths=CompactDocLengths.from_dict({0: 10, 1: 20}, total_docs=2),
            total_docs=2
        )
        save_yny(str(temp_yny_file), engine)
        
        handle = open_yny(str(temp_yny_file))
        
        keys = list(handle.index.keys())
        assert set(keys) == {"python", "java"}
        
        values = list(handle.index.values())
        assert all(isinstance(v, MmapPostings) for v in values)
        
        items = list(handle.index.items())
        assert len(items) == 2
        handle.close()

    def test_len(self, temp_yny_file):
        engine = MockEngine(
            index={
                "python": CompactPostings.from_dict({0: 1}),
                "java": CompactPostings.from_dict({1: 2}),
                "javascript": CompactPostings.from_dict({2: 3})
            },
            doc_lengths=CompactDocLengths.from_dict({0: 10, 1: 20, 2: 30}, total_docs=3),
            total_docs=3
        )
        save_yny(str(temp_yny_file), engine)
        
        handle = open_yny(str(temp_yny_file))
        assert len(handle.index) == 3
        handle.close()

    def test_clear_releases_referencias(self, temp_yny_file):
        engine = MockEngine(
            index={"python": CompactPostings.from_dict({0: 1})},
            doc_lengths=CompactDocLengths.from_dict({0: 10}, total_docs=1),
            total_docs=1
        )
        save_yny(str(temp_yny_file), engine)
        
        handle = open_yny(str(temp_yny_file))
        assert len(handle.index) > 0
        handle.index.clear()
        assert len(handle.index._token_idx) == 0
        handle.close()

class TestYnyHandleLifecycle:

    def test_withtext_manager_enter(self, temp_yny_file):
        engine = MockEngine(
            index={"python": CompactPostings.from_dict({0: 1})},
            doc_lengths=CompactDocLengths.from_dict({0: 10}, total_docs=1),
            total_docs=1
        )
        save_yny(str(temp_yny_file), engine)
        
        with open_yny(str(temp_yny_file)) as handle:
            assert handle is not None
            assert handle.total_docs == 1

    def test_withtext_manager_exit_closes(self, temp_yny_file):
        engine = MockEngine(
            index={"python": CompactPostings.from_dict({0: 1})},
            doc_lengths=CompactDocLengths.from_dict({0: 10}, total_docs=1),
            total_docs=1
        )
        save_yny(str(temp_yny_file), engine)
        
        with open_yny(str(temp_yny_file)) as handle:
            assert handle.total_docs == 1
        assert handle._mm is None
        assert handle._file is None

    def test_close_releases_memoryviews(self, temp_yny_file):
        engine = MockEngine(
            index={"python": CompactPostings.from_dict({0: 1})},
            doc_lengths=CompactDocLengths.from_dict({0: 10}, total_docs=1),
            total_docs=1
        )
        save_yny(str(temp_yny_file), engine)
        
        handle = open_yny(str(temp_yny_file))
        assert handle._payload_view is not None
        handle.close()
        assert handle._payload_view is None

    def test_close_closes_mmap(self, temp_yny_file):
        engine = MockEngine(
            index={"python": CompactPostings.from_dict({0: 1})},
            doc_lengths=CompactDocLengths.from_dict({0: 10}, total_docs=1),
            total_docs=1
        )
        save_yny(str(temp_yny_file), engine)
        
        handle = open_yny(str(temp_yny_file))
        assert handle._mm is not None
        handle.close()
        assert handle._mm is None

    def test_close_closes_file_descriptor(self, temp_yny_file):
        engine = MockEngine(
            index={"python": CompactPostings.from_dict({0: 1})},
            doc_lengths=CompactDocLengths.from_dict({0: 10}, total_docs=1),
            total_docs=1
        )
        save_yny(str(temp_yny_file), engine)
        
        handle = open_yny(str(temp_yny_file))
        assert handle._file is not None
        handle.close()
        assert handle._file is None

    def test_multiple_close_not_causan_error(self, temp_yny_file):
        engine = MockEngine(
            index={"python": CompactPostings.from_dict({0: 1})},
            doc_lengths=CompactDocLengths.from_dict({0: 10}, total_docs=1),
            total_docs=1
        )
        save_yny(str(temp_yny_file), engine)
        
        handle = open_yny(str(temp_yny_file))
        handle.close()
        handle.close()
        handle.close()

    def test_del_as_safetand_net(self, temp_yny_file):
        engine = MockEngine(
            index={"python": CompactPostings.from_dict({0: 1})},
            doc_lengths=CompactDocLengths.from_dict({0: 10}, total_docs=1),
            total_docs=1
        )
        save_yny(str(temp_yny_file), engine)
        
        handle = open_yny(str(temp_yny_file))
        del handle

class TestYnyExists:

    def test_returns_true_file_valid(self, temp_yny_file):
        engine = MockEngine(
            index={"python": CompactPostings.from_dict({0: 1})},
            doc_lengths=CompactDocLengths.from_dict({0: 10}, total_docs=1),
            total_docs=1
        )
        save_yny(str(temp_yny_file), engine)
        
        assert yny_exists(str(temp_yny_file)) is True

    def test_returns_false_file_inexisting(self):
        assert yny_exists("/nonexistent/file.yny") is False

    def test_returns_false_magic_incorrect(self, tmp_path):
        bad_file = tmp_path / "bad.yny"
        with open(bad_file, "wb") as f:
            f.write(b"NOTYNY")
        
        assert yny_exists(str(bad_file)) is False

    def test_returns_false_file_empty(self, tmp_path):
        empty_file = tmp_path / "empty.yny"
        empty_file.touch()
        
        assert yny_exists(str(empty_file)) is False