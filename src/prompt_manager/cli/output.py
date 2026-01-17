"""Output formatters for CLI."""

import json
from typing import Any

from rich.console import Console
from rich.table import Table

console = Console()
err_console = Console(stderr=True)


def format_plain(content: str) -> str:
    """Return plain text content."""
    return content


def format_json(data: Any) -> str:
    """Format data as JSON."""
    return json.dumps(data, indent=2, default=str)


def format_yaml(data: Any) -> str:
    """Format data as YAML-like output."""
    def _format_value(value: Any, indent: int = 0) -> str:
        prefix = "  " * indent
        if isinstance(value, dict):
            if not value:
                return "{}"
            lines = []
            for k, v in value.items():
                formatted = _format_value(v, indent + 1)
                if isinstance(v, (dict, list)) and v:
                    lines.append(f"{prefix}{k}:")
                    lines.append(formatted)
                else:
                    lines.append(f"{prefix}{k}: {formatted}")
            return "\n".join(lines)
        elif isinstance(value, list):
            if not value:
                return "[]"
            lines = []
            for item in value:
                formatted = _format_value(item, indent + 1)
                if isinstance(item, dict):
                    lines.append(f"{prefix}- ")
                    lines.append(formatted)
                else:
                    lines.append(f"{prefix}- {formatted}")
            return "\n".join(lines)
        elif value is None:
            return "null"
        elif isinstance(value, bool):
            return str(value).lower()
        else:
            return str(value)

    return _format_value(data)


def print_table(
    data: list[dict[str, Any]],
    columns: list[tuple[str, str]],
    title: str | None = None,
) -> None:
    """Print data as a rich table."""
    table = Table(title=title, show_header=True, header_style="bold")

    for col_key, col_name in columns:
        table.add_column(col_name)

    for row in data:
        values = []
        for col_key, _ in columns:
            value = row.get(col_key, "")
            if isinstance(value, list):
                value = ", ".join(str(v) for v in value)
            elif value is None:
                value = ""
            values.append(str(value))
        table.add_row(*values)

    console.print(table)


def print_prompt_table(prompts: list[dict[str, Any]]) -> None:
    """Print prompts in a table format."""
    columns = [
        ("slug", "Slug"),
        ("title", "Title"),
        ("category", "Category"),
        ("tags", "Tags"),
        ("usage_count", "Uses"),
    ]
    print_table(prompts, columns)


def print_version_table(versions: list[dict[str, Any]]) -> None:
    """Print versions in a table format."""
    columns = [
        ("version", "Version"),
        ("changed_at", "Changed At"),
        ("change_note", "Note"),
    ]
    print_table(versions, columns)


def print_category_table(categories: list[dict[str, Any]]) -> None:
    """Print categories in a table format."""
    columns = [
        ("category", "Category"),
        ("count", "Count"),
    ]
    print_table(categories, columns)


def print_tag_table(tags: list[dict[str, Any]]) -> None:
    """Print tags in a table format."""
    columns = [
        ("tag", "Tag"),
        ("count", "Count"),
    ]
    print_table(tags, columns)


def print_error(message: str) -> None:
    """Print error message."""
    err_console.print(f"[red]Error:[/red] {message}")


def print_success(message: str) -> None:
    """Print success message."""
    console.print(f"[green]{message}[/green]")


def print_warning(message: str) -> None:
    """Print warning message."""
    console.print(f"[yellow]{message}[/yellow]")
