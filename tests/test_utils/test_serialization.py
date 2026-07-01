import pytest
from lucis.utils.serialization import dumps, loads, BACKEND


class TestDumps:
    def test_serializes_simple_dict(self):
        result = dumps({"hello": "world"})
        assert '"hello"' in result
        assert '"world"' in result
        assert isinstance(result, str)

    def test_serializes_list(self):
        result = dumps([1, 2, 3])
        assert "1" in result
        assert "2" in result
        assert "3" in result
        assert isinstance(result, str)

    def test_serializes_dict_with_int_keys(self):
        result = dumps({1: "one", 2: "two"})
        assert "1" in result
        assert "2" in result
        assert isinstance(result, str)

    def test_returns_str_not_bytes(self):
        result = dumps({"test": "value"})
        assert isinstance(result, str)
        assert not isinstance(result, bytes)

    def test_unicode_characters(self):
        result = dumps({"message": "cafe nino"})
        assert "cafe" in result
        assert "nino" in result
        assert isinstance(result, str)

    def test_nested_dict(self):
        data = {
            "user": {
                "name": "John",
                "age": 30
            },
            "tags": ["python", "testing"]
        }
        result = dumps(data)
        assert isinstance(result, str)
        assert "John" in result
        assert "python" in result

    def test_numeric_values(self):
        result = dumps({"int": 42, "float": 3.14, "negative": -10})
        assert "42" in result
        assert "3.14" in result
        assert "-10" in result

    def test_boolean_values(self):
        result = dumps({"true": True, "false": False})
        assert "true" in result.lower()
        assert "false" in result.lower()

    def test_none_value(self):
        result = dumps({"null": None})
        assert "null" in result

    def test_empty_list(self):
        assert dumps([]) == "[]"

    def test_empty_dict(self):
        assert dumps({}) == "{}"


class TestLoads:
    def test_deserializes_basic_json(self):
        result = loads('{"hello": "world"}')
        assert result == {"hello": "world"}

    def test_accepts_str(self):
        json_str = '{"key": "value"}'
        result = loads(json_str)
        assert result == {"key": "value"}

    def test_accepts_bytes(self):
        json_bytes = b'{"key": "value"}'
        result = loads(json_bytes)
        assert result == {"key": "value"}

    def test_roundtrip_dumps_loads(self):
        original = {
            "name": "John",
            "age": 30,
            "tags": ["python", "testing"],
            "active": True
        }
        serialized = dumps(original)
        result = loads(serialized)
        assert result == original

    def test_deserializes_list(self):
        assert loads("[1, 2, 3]") == [1, 2, 3]

    def test_deserializes_number(self):
        assert loads("42") == 42

    def test_deserializes_string(self):
        assert loads('"hello world"') == "hello world"

    def test_deserializes_booleans(self):
        assert loads("true") is True
        assert loads("false") is False

    def test_deserializes_none(self):
        assert loads("null") is None

    def test_deserializes_unicode(self):
        result = loads('{"mensaje": "cafe nino"}')
        assert result["mensaje"] == "cafe nino"

    def test_deserializes_complex_structure(self):
        json_str = '{"users":[{"id":1,"name":"Alice"},{"id":2,"name":"Bob"}],"count":2}'
        result = loads(json_str)
        assert len(result["users"]) == 2
        assert result["users"][0]["name"] == "Alice"
        assert result["count"] == 2


class TestBackendDetection:
    def test_backend_is_string(self):
        assert isinstance(BACKEND, str)

    def test_backend_is_orjson_or_json(self):
        assert BACKEND in ("orjson", "json")

    def test_backend_orjson_available(self):
        try:
            import orjson
            assert BACKEND == "orjson"
        except ImportError:
            assert BACKEND == "json"


class TestCompatibility:
    def test_same_behavior_as_standard_json(self):
        import json

        test_data = {
            "string": "value",
            "number": 42,
            "float": 3.14,
            "bool": True,
            "null": None,
            "list": [1, 2, 3],
            "dict": {"nested": "value"},
        }

        lucis_result = dumps(test_data)
        json_result = json.dumps(test_data)

        lucis_parsed = loads(lucis_result)
        json_parsed = json.loads(json_result)

        assert lucis_parsed == json_parsed

    def test_float_handling(self):
        data = {"value": 3.14159}
        result = loads(dumps(data))
        assert abs(result["value"] - 3.14159) < 0.0001

    def test_large_numbers(self):
        data = {"big_int": 999999999999999999}
        result = loads(dumps(data))
        assert result["big_int"] == 999999999999999999

    def test_escape_special_characters(self):
        data = {"text": "Line1\\nLine2\\tTabbed"}
        result = loads(dumps(data))
        assert result["text"] == "Line1\\nLine2\\tTabbed"

    def test_quotes_in_string(self):
        data = {"text": 'He said "Hello"'}
        result = loads(dumps(data))
        assert result["text"] == 'He said "Hello"'

    def test_backslash_in_string(self):
        data = {"path": "C:\\Users\\test"}
        result = loads(dumps(data))
        assert result["path"] == "C:\\Users\\test"


class TestSpecialCases:
    def test_int_keys_in_dict(self):
        data = {1: "one", 2: "two", 3: "three"}
        result = loads(dumps(data))
        assert len(result) == 3
        assert "1" in result or 1 in result

    def test_empty_string(self):
        data = {"empty": ""}
        result = loads(dumps(data))
        assert result["empty"] == ""

    def test_whitespace_strings(self):
        data = {"text": "  spaces  ", "tab": "\t", "newline": "\n"}
        result = loads(dumps(data))
        assert result["text"] == "  spaces  "
        assert result["tab"] == "\t"
        assert result["newline"] == "\n"

    def test_zero_and_false_values(self):
        data = {"zero": 0, "false": False, "empty_str": "", "empty_list": []}
        result = loads(dumps(data))
        assert result["zero"] == 0
        assert result["false"] is False
        assert result["empty_str"] == ""
        assert result["empty_list"] == []

    def test_scientific_notation(self):
        data = {"small": 1e-10, "large": 1e10}
        result = loads(dumps(data))
        assert result["small"] == 1e-10
        assert result["large"] == 1e10

    def test_preserved_key_order(self):
        data = {"z": 1, "a": 2, "m": 3}
        result = loads(dumps(data))
        assert result["z"] == 1
        assert result["a"] == 2
        assert result["m"] == 3
