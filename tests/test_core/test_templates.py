"""Tests for template engine."""

import pytest

from prompt_manager.core.templates import TemplateEngine, TemplateRenderError


class TestTemplateEngine:
    """Tests for TemplateEngine."""

    @pytest.fixture
    def engine(self) -> TemplateEngine:
        return TemplateEngine()

    def test_is_template_with_variables(self, engine: TemplateEngine) -> None:
        """Test detection of template variables."""
        assert engine.is_template("Hello {{ name }}")
        assert engine.is_template("{{name}}")
        assert engine.is_template("Hello {{ name }}, welcome!")

    def test_is_template_with_blocks(self, engine: TemplateEngine) -> None:
        """Test detection of template blocks."""
        assert engine.is_template("{% if condition %}yes{% endif %}")
        assert engine.is_template("{% for item in items %}{{ item }}{% endfor %}")

    def test_is_template_plain_text(self, engine: TemplateEngine) -> None:
        """Test that plain text is not detected as template."""
        assert not engine.is_template("Hello world")
        assert not engine.is_template("No templates here")
        assert not engine.is_template("{ not a template }")

    def test_extract_variables_simple(self, engine: TemplateEngine) -> None:
        """Test variable extraction from simple templates."""
        variables = engine.extract_variables("Hello {{ name }}")
        assert "name" in variables

    def test_extract_variables_multiple(self, engine: TemplateEngine) -> None:
        """Test extraction of multiple variables."""
        content = "Hello {{ name }}, welcome to {{ place }}!"
        variables = engine.extract_variables(content)
        assert "name" in variables
        assert "place" in variables

    def test_extract_variables_with_filter(self, engine: TemplateEngine) -> None:
        """Test extraction with Jinja2 filters."""
        content = "{{ name | upper }}"
        variables = engine.extract_variables(content)
        assert "name" in variables

    def test_extract_variables_from_loop(self, engine: TemplateEngine) -> None:
        """Test extraction from for loops."""
        content = "{% for item in items %}{{ item }}{% endfor %}"
        variables = engine.extract_variables(content)
        assert "items" in variables

    def test_render_simple(self, engine: TemplateEngine) -> None:
        """Test simple template rendering."""
        content = "Hello {{ name }}!"
        result = engine.render(content, {"name": "World"})
        assert result == "Hello World!"

    def test_render_multiple_variables(self, engine: TemplateEngine) -> None:
        """Test rendering with multiple variables."""
        content = "Hello {{ name }}, welcome to {{ place }}!"
        result = engine.render(content, {"name": "Alice", "place": "Wonderland"})
        assert result == "Hello Alice, welcome to Wonderland!"

    def test_render_missing_variable(self, engine: TemplateEngine) -> None:
        """Test that missing variables raise an error."""
        content = "Hello {{ name }}!"
        with pytest.raises(TemplateRenderError):
            engine.render(content, {})

    def test_render_plain_text(self, engine: TemplateEngine) -> None:
        """Test rendering plain text passes through."""
        content = "Hello world!"
        result = engine.render(content, {})
        assert result == "Hello world!"

    def test_validate_template_valid(self, engine: TemplateEngine) -> None:
        """Test validation of valid template."""
        content = "Hello {{ name }}!"
        valid, error = engine.validate_template(content)
        assert valid
        assert error is None

    def test_validate_template_invalid(self, engine: TemplateEngine) -> None:
        """Test validation of invalid template."""
        content = "Hello {{ name }"  # Missing closing braces
        valid, error = engine.validate_template(content)
        assert not valid
        assert error is not None
