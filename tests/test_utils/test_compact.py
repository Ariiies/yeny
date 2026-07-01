
import array
import pytest
from lucis.utils.compact import (
    CompactPostings,
    CompactDocLengths,
    freeze_index,
    thaw_index,
    freeze_doc_lengths,
)

class TestCompactPostings:

    def test_from_dict_empty(self):
        postings = CompactPostings.from_dict({})
        assert len(postings) == 0
        assert bool(postings) is False

    def test_from_dict_un_element(self):
        postings = CompactPostings.from_dict({1: 5})
        assert len(postings) == 1
        assert postings.get(1) == 5

    def test_from_dict_multiple_elements(self):
        d = {3: 2, 1: 5, 2: 1}
        postings = CompactPostings.from_dict(d)
        assert len(postings) == 3
        assert postings.get(1) == 5
        assert postings.get(2) == 1
        assert postings.get(3) == 2

    def test_from_dict_sorts_band_doc_id(self):
        d = {5: 1, 1: 2, 3: 3}
        postings = CompactPostings.from_dict(d)
        keys = list(postings.keys())
        assert keys == [1, 3, 5]

    def test_from_dict_string_keys(self):
        postings = CompactPostings.from_dict({"1": 5, "2": 3})
        assert postings.get(1) == 5
        assert postings.get(2) == 3

    def test_from_dict_string_values(self):
        postings = CompactPostings.from_dict({1: "5", 2: "3"})
        assert postings.get(1) == 5
        assert postings.get(2) == 3

    def test_get_existing(self):
        postings = CompactPostings.from_dict({1: 5, 2: 3})
        assert postings.get(1) == 5
        assert postings.get(2) == 3

    def test_get_inexisting_default_zero(self):
        postings = CompactPostings.from_dict({1: 5})
        assert postings.get(99) == 0
        assert postings.get(0) == 0

    def test_get_inexisting_default_custom(self):
        postings = CompactPostings.from_dict({1: 5})
        assert postings.get(99, -1) == -1
        assert postings.get(0, 10) == 10

    def test_keys(self):
        postings = CompactPostings.from_dict({1: 5, 2: 3, 3: 1})
        keys = list(postings.keys())
        assert keys == [1, 2, 3]
        assert isinstance(keys[0], int)

    def test_values(self):
        postings = CompactPostings.from_dict({1: 5, 2: 3})
        values = list(postings.values())
        assert values == [5, 3]
        assert isinstance(values[0], int)

    def test_items(self):
        postings = CompactPostings.from_dict({1: 5, 2: 3})
        items = list(postings.items())
        assert items == [(1, 5), (2, 3)]

    def test_withtains_present(self):
        postings = CompactPostings.from_dict({1: 5, 2: 3})
        assert 1 in postings
        assert 2 in postings

    def test_withtains_absent(self):
        postings = CompactPostings.from_dict({1: 5})
        assert 99 not in postings
        assert 0 not in postings

    def test_getitem_success(self):
        postings = CompactPostings.from_dict({1: 5, 2: 3})
        assert postings[1] == 5
        assert postings[2] == 3

    def test_getitem_keyerror(self):
        postings = CompactPostings.from_dict({1: 5})
        with pytest.raises(KeyError):
            _ = postings[99]

    def test_len_correct(self):
        postings = CompactPostings.from_dict({1: 5, 2: 3, 3: 1})
        assert len(postings) == 3

    def test_len_empty(self):
        postings = CompactPostings.from_dict({})
        assert len(postings) == 0

    def test_bool_not_empty(self):
        postings = CompactPostings.from_dict({1: 5})
        assert bool(postings) is True

    def test_bool_empty(self):
        postings = CompactPostings.from_dict({})
        assert bool(postings) is False

    def test_to_dict(self):
        postings = CompactPostings.from_dict({3: 2, 1: 5, 2: 1})
        result = postings.to_dict()
        assert isinstance(result, dict)
        assert result == {1: 5, 2: 1, 3: 2}
        assert all(isinstance(k, int) for k in result.keys())
        assert all(isinstance(v, int) for v in result.values())

    def test_repr(self):
        postings = CompactPostings.from_dict({1: 5, 2: 3})
        assert "entries=2" in repr(postings)

class TestCompactDocLengths:

    def test_from_dict_empty(self):
        doc_lengths = CompactDocLengths.from_dict({}, total_docs=0)
        assert len(doc_lengths) == 0
        assert bool(doc_lengths) is False

    def test_from_dict_with_elements(self):
        doc_lengths = CompactDocLengths.from_dict({0: 10, 1: 20, 2: 15}, total_docs=3)
        assert doc_lengths.get(0) == 10
        assert doc_lengths.get(1) == 20
        assert doc_lengths.get(2) == 15

    def test_from_dict_total_docs_especificado(self):
        doc_lengths = CompactDocLengths.from_dict({0: 10}, total_docs=5)
        assert len(doc_lengths) == 5
        assert doc_lengths.get(0) == 10
        assert doc_lengths.get(1) == 0

    def test_from_dict_initializes_zeros(self):
        doc_lengths = CompactDocLengths.from_dict({2: 20}, total_docs=5)
        assert doc_lengths.get(0) == 0
        assert doc_lengths.get(1) == 0
        assert doc_lengths.get(2) == 20
        assert doc_lengths.get(3) == 0
        assert doc_lengths.get(4) == 0

    def test_from_dict_string_keys(self):
        doc_lengths = CompactDocLengths.from_dict({"0": 10, "1": 20}, total_docs=2)
        assert doc_lengths.get(0) == 10
        assert doc_lengths.get(1) == 20

    def test_get_valid(self):
        doc_lengths = CompactDocLengths.from_dict({0: 10, 1: 20}, total_docs=2)
        assert doc_lengths.get(0) == 10
        assert doc_lengths.get(1) == 20

    def test_get_fout_of_range(self):
        doc_lengths = CompactDocLengths.from_dict({0: 10}, total_docs=2)
        assert doc_lengths.get(99) == 0
        assert doc_lengths.get(99, -1) == -1

    def test_get_negative(self):
        doc_lengths = CompactDocLengths.from_dict({0: 10}, total_docs=2)
        assert doc_lengths.get(-1) == 0
        assert doc_lengths.get(-1, -1) == -1

    def test_getitem(self):
        doc_lengths = CompactDocLengths.from_dict({0: 10, 1: 20}, total_docs=2)
        assert doc_lengths[0] == 10
        assert doc_lengths[1] == 20

    def test_getitem_indexerror(self):
        doc_lengths = CompactDocLengths.from_dict({0: 10}, total_docs=2)
        with pytest.raises(IndexError):
            _ = doc_lengths[99]

    def test_setitem_existing(self):
        doc_lengths = CompactDocLengths.from_dict({0: 10, 1: 20}, total_docs=2)
        doc_lengths[0] = 100
        assert doc_lengths[0] == 100

    def test_setitem_extend(self):
        doc_lengths = CompactDocLengths.from_dict({0: 10}, total_docs=1)
        doc_lengths[5] = 50
        assert doc_lengths[5] == 50
        assert len(doc_lengths) == 6
        assert doc_lengths[0] == 10

    def test_setitem_extend_keeps_values(self):
        doc_lengths = CompactDocLengths.from_dict({0: 10, 2: 30}, total_docs=3)
        doc_lengths[5] = 50
        assert doc_lengths[0] == 10
        assert doc_lengths[2] == 30
        assert doc_lengths[5] == 50

    def test_keys(self):
        doc_lengths = CompactDocLengths.from_dict({}, total_docs=5)
        keys = list(doc_lengths.keys())
        assert keys == [0, 1, 2, 3, 4]

    def test_values(self):
        doc_lengths = CompactDocLengths.from_dict({0: 10, 1: 20}, total_docs=2)
        values = list(doc_lengths.values())
        assert values == [10, 20]

    def test_items(self):
        doc_lengths = CompactDocLengths.from_dict({0: 10, 1: 20}, total_docs=2)
        items = list(doc_lengths.items())
        assert items == [(0, 10), (1, 20)]

    def test_len(self):
        doc_lengths = CompactDocLengths.from_dict({}, total_docs=10)
        assert len(doc_lengths) == 10

    def test_bool_not_empty(self):
        doc_lengths = CompactDocLengths.from_dict({0: 10}, total_docs=1)
        assert bool(doc_lengths) is True

    def test_bool_empty(self):
        doc_lengths = CompactDocLengths.from_dict({}, total_docs=0)
        assert bool(doc_lengths) is False

    def test_to_dict(self):
        doc_lengths = CompactDocLengths.from_dict({0: 10, 1: 20, 2: 15}, total_docs=3)
        result = doc_lengths.to_dict()
        assert result == {0: 10, 1: 20, 2: 15}
        assert isinstance(result, dict)

class TestFreezeThawHelpers:

    def test_freeze_index(self):
        index = {
            "python": {0: 5, 1: 3},
            "java": {1: 2, 2: 4}
        }
        frozen = freeze_index(index)
        assert isinstance(frozen["python"], CompactPostings)
        assert isinstance(frozen["java"], CompactPostings)
        assert frozen["python"].get(0) == 5
        assert frozen["java"].get(2) == 4

    def test_thaw_index(self):
        compact_index = {
            "python": CompactPostings.from_dict({0: 5, 1: 3}),
            "java": CompactPostings.from_dict({1: 2})
        }
        thawed = thaw_index(compact_index)
        assert isinstance(thawed["python"], dict)
        assert isinstance(thawed["java"], dict)
        assert thawed["python"] == {0: 5, 1: 3}
        assert thawed["java"] == {1: 2}

    def test_thaw_index_mixed(self):
        mixed_index = {
            "python": CompactPostings.from_dict({0: 5}),
            "java": {1: 2}
        }
        thawed = thaw_index(mixed_index)
        assert thawed["python"] == {0: 5}
        assert thawed["java"] == {1: 2}

    def test_freeze_doc_lengths(self):
        doc_lengths = {0: 10, 1: 20, 2: 15}
        frozen = freeze_doc_lengths(doc_lengths, total_docs=3)
        assert isinstance(frozen, CompactDocLengths)
        assert frozen.get(0) == 10
        assert frozen.get(1) == 20
        assert frozen.get(2) == 15
        assert len(frozen) == 3

    def test_roundtrip_index(self):
        original = {
            "python": {0: 5, 1: 3, 2: 1},
            "java": {1: 2, 3: 4},
            "javascript": {0: 1, 2: 3, 4: 2}
        }
        frozen = freeze_index(original)
        thawed = thaw_index(frozen)
        assert thawed == original

    def test_roundtrip_doc_lengths(self):
        original = {0: 10, 1: 20, 2: 15, 3: 25}
        frozen = freeze_doc_lengths(original, total_docs=4)
        result = frozen.to_dict()
        assert result == original