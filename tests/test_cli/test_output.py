"""Tests for CLI output formatters."""

import json

import pytest

from prompt_manager.cli.output import format_json, format_plain, format_yaml


class TestOutputFormatters:
    """Tests for output formatting functions."""

    def test_format_plain(self) -> None:
        """Test plain text formatting."""
        result = format_plain("Hello world")
        assert result == "Hello world"

    def test_format_json(self) -> None:
        """Test JSON formatting."""
        data = {"name": "test", "value": 123}
        result = format_json(data)
        parsed = json.loads(result)
        assert parsed == data

    def test_format_json_nested(self) -> None:
        """Test JSON formatting with nested data."""
        data = {"name": "test", "nested": {"key": "value"}, "list": [1, 2, 3]}
        result = format_json(data)
        parsed = json.loads(result)
        assert parsed == data

    def test_format_yaml_simple(self) -> None:
        """Test YAML formatting with simple data."""
        data = {"name": "test", "value": 123}
        result = format_yaml(data)
        assert "name: test" in result
        assert "value: 123" in result

    def test_format_yaml_nested(self) -> None:
        """Test YAML formatting with nested data."""
        data = {"outer": {"inner": "value"}}
        result = format_yaml(data)
        assert "outer:" in result
        assert "inner: value" in result

    def test_format_yaml_list(self) -> None:
        """Test YAML formatting with lists."""
        data = {"items": ["a", "b", "c"]}
        result = format_yaml(data)
        assert "items:" in result
        assert "- a" in result

    def test_format_yaml_empty_dict(self) -> None:
        """Test YAML formatting with empty dict."""
        data = {"empty": {}}
        result = format_yaml(data)
        assert "empty: {}" in result

    def test_format_yaml_empty_list(self) -> None:
        """Test YAML formatting with empty list."""
        data = {"empty": []}
        result = format_yaml(data)
        assert "empty: []" in result

    def test_format_yaml_none(self) -> None:
        """Test YAML formatting with None."""
        data = {"value": None}
        result = format_yaml(data)
        assert "value: null" in result

    def test_format_yaml_bool(self) -> None:
        """Test YAML formatting with booleans."""
        data = {"yes": True, "no": False}
        result = format_yaml(data)
        assert "yes: true" in result
        assert "no: false" in result
