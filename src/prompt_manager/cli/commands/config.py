"""CLI configuration commands."""

import tomllib
from pathlib import Path
from typing import Annotated

import typer

from prompt_manager.cli.output import console, format_json, print_error, print_success
from prompt_manager.core.config import settings

app = typer.Typer(help="Configuration commands")

CONFIG_FILE = settings.config_dir / "config.toml"


def ensure_config_dir() -> None:
    """Ensure config directory exists."""
    settings.config_dir.mkdir(parents=True, exist_ok=True)


def load_config() -> dict:
    """Load configuration from file."""
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, "rb") as f:
            return tomllib.load(f)
    return {}


def save_config(config: dict) -> None:
    """Save configuration to file."""
    ensure_config_dir()

    lines = []
    for key, value in config.items():
        if isinstance(value, str):
            lines.append(f'{key} = "{value}"')
        elif isinstance(value, bool):
            lines.append(f"{key} = {str(value).lower()}")
        else:
            lines.append(f"{key} = {value}")

    CONFIG_FILE.write_text("\n".join(lines) + "\n")


@app.command("show")
def show_config(
    json_output: Annotated[
        bool, typer.Option("--json", "-j", help="Output as JSON")
    ] = False,
) -> None:
    """Show current configuration.

    Examples:
        pm config show
        pm config show --json
    """
    config = {
        "api_url": settings.api_url,
        "api_key": settings.api_key[:8] + "..." if len(settings.api_key) > 8 else "***",
        "default_format": settings.default_format,
        "editor": settings.editor,
        "database_url": settings.database_url,
        "config_file": str(CONFIG_FILE),
        "config_file_exists": CONFIG_FILE.exists(),
    }

    if json_output:
        console.print(format_json(config))
    else:
        console.print("[bold]Current Configuration[/bold]\n")
        for key, value in config.items():
            console.print(f"  {key}: {value}")


@app.command("set")
def set_config(
    key: Annotated[str, typer.Argument(help="Configuration key")],
    value: Annotated[str, typer.Argument(help="Configuration value")],
) -> None:
    """Set a configuration value.

    Available keys:
    - api-url: API server URL
    - api-key: API authentication key
    - default-format: Default output format (plain, json, yaml, table)
    - editor: Editor command for 'edit' command

    Examples:
        pm config set api-url http://localhost:8000
        pm config set api-key my-secret-key
        pm config set default-format json
        pm config set editor nano
    """
    # Map CLI keys to config keys
    key_map = {
        "api-url": "api_url",
        "api-key": "api_key",
        "default-format": "default_format",
        "editor": "editor",
    }

    config_key = key_map.get(key)
    if not config_key:
        print_error(f"Unknown configuration key: {key}")
        console.print(f"Available keys: {', '.join(key_map.keys())}")
        raise typer.Exit(1)

    # Validate format option
    if config_key == "default_format" and value not in ["plain", "json", "yaml", "table"]:
        print_error(f"Invalid format: {value}")
        console.print("Valid formats: plain, json, yaml, table")
        raise typer.Exit(1)

    config = load_config()
    config[config_key] = value
    save_config(config)

    print_success(f"Set {key} = {value}")


@app.command("get")
def get_config(
    key: Annotated[str, typer.Argument(help="Configuration key")],
) -> None:
    """Get a configuration value.

    Examples:
        pm config get api-url
    """
    key_map = {
        "api-url": "api_url",
        "api-key": "api_key",
        "default-format": "default_format",
        "editor": "editor",
    }

    config_key = key_map.get(key)
    if not config_key:
        print_error(f"Unknown configuration key: {key}")
        raise typer.Exit(1)

    value = getattr(settings, config_key, None)
    if value:
        # Mask API key
        if config_key == "api_key" and len(value) > 8:
            value = value[:8] + "..."
        console.print(value)
    else:
        console.print("")


@app.command("path")
def config_path() -> None:
    """Show configuration file path.

    Examples:
        pm config path
    """
    console.print(str(CONFIG_FILE))
