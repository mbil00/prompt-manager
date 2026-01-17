"""Jinja2 template rendering for prompts."""

import re
from typing import Any

from jinja2 import Environment, StrictUndefined, TemplateSyntaxError, UndefinedError


class TemplateEngine:
    """Jinja2-based template engine for prompts."""

    def __init__(self):
        self.env = Environment(
            undefined=StrictUndefined,
            autoescape=False,  # We're not generating HTML
            keep_trailing_newline=True,
        )

    def is_template(self, content: str) -> bool:
        """Check if content contains Jinja2 template syntax."""
        # Check for {{ }} variable syntax or {% %} block syntax
        return bool(re.search(r"\{\{.*?\}\}|\{%.*?%\}", content))

    def extract_variables(self, content: str) -> list[str]:
        """Extract variable names from a template."""
        variables: set[str] = set()

        # Match {{ variable }} or {{ variable | filter }}
        var_pattern = re.compile(r"\{\{\s*(\w+)(?:\s*\|.*?)?\s*\}\}")
        variables.update(var_pattern.findall(content))

        # Match {% for item in items %} style loops
        for_pattern = re.compile(r"\{%\s*for\s+\w+\s+in\s+(\w+)\s*%\}")
        variables.update(for_pattern.findall(content))

        # Match {% if variable %} style conditions
        if_pattern = re.compile(r"\{%\s*if\s+(\w+)(?:\s|\})")
        variables.update(if_pattern.findall(content))

        # Filter out Jinja2 builtins and common loop variables
        builtins = {"loop", "true", "false", "none", "True", "False", "None"}
        return sorted(variables - builtins)

    def render(self, content: str, variables: dict[str, Any]) -> str:
        """Render a template with the given variables."""
        try:
            template = self.env.from_string(content)
            return template.render(**variables)
        except TemplateSyntaxError as e:
            raise TemplateRenderError(f"Template syntax error: {e.message}") from e
        except UndefinedError as e:
            raise TemplateRenderError(f"Missing variable: {e.message}") from e

    def validate_template(self, content: str) -> tuple[bool, str | None]:
        """Validate template syntax without rendering."""
        try:
            self.env.parse(content)
            return True, None
        except TemplateSyntaxError as e:
            return False, f"Syntax error at line {e.lineno}: {e.message}"


class TemplateRenderError(Exception):
    """Exception raised when template rendering fails."""

    pass
