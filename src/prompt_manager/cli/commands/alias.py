"""CLI alias management commands."""

import os
import stat
import tomllib
from pathlib import Path
from typing import Annotated

import typer

from prompt_manager.cli.client import APIClient, APIError
from prompt_manager.cli.output import (
    console,
    format_json,
    print_error,
    print_success,
    print_table,
    print_warning,
)
from prompt_manager.core.config import settings

app = typer.Typer(help="Alias management commands")

ALIAS_FILE = settings.config_dir / "aliases.toml"
DEFAULT_BIN_DIR = Path.home() / ".local" / "bin"


def ensure_config_dir() -> None:
    """Ensure config directory exists."""
    settings.config_dir.mkdir(parents=True, exist_ok=True)


def load_aliases() -> dict[str, str]:
    """Load aliases from TOML file."""
    if ALIAS_FILE.exists():
        with open(ALIAS_FILE, "rb") as f:
            return tomllib.load(f)
    return {}


def save_aliases(aliases: dict[str, str]) -> None:
    """Save aliases to TOML file."""
    ensure_config_dir()

    lines = []
    for name, slug in sorted(aliases.items()):
        lines.append(f'{name} = "{slug}"')

    ALIAS_FILE.write_text("\n".join(lines) + "\n" if lines else "")


def is_valid_alias_name(name: str) -> bool:
    """Check if alias name is valid (alphanumeric and hyphens/underscores)."""
    return all(c.isalnum() or c in "-_" for c in name) and len(name) > 0


def get_wrapper_script(slug: str) -> str:
    """Generate wrapper script content for an alias."""
    return f'''#!/bin/bash
exec pm get {slug} "$@"
'''


def check_path_contains(directory: Path) -> bool:
    """Check if directory is in PATH."""
    path_dirs = os.environ.get("PATH", "").split(os.pathsep)
    return str(directory) in path_dirs


@app.command("add")
def add_alias(
    name: Annotated[str, typer.Argument(help="Alias name (e.g., pmge)")],
    slug: Annotated[str, typer.Argument(help="Prompt slug to alias")],
) -> None:
    """Register a new alias.

    Creates a shortcut name for a prompt slug.

    Examples:
        pm alias add pmge explain-error
        pm alias add pmcr code-review
    """
    if not is_valid_alias_name(name):
        print_error("Alias name must contain only alphanumeric characters, hyphens, and underscores")
        raise typer.Exit(1)

    aliases = load_aliases()

    if name in aliases:
        print_warning(f"Alias '{name}' already exists (current: {aliases[name]})")
        if not typer.confirm("Overwrite?"):
            raise typer.Exit(0)

    aliases[name] = slug
    save_aliases(aliases)
    print_success(f"Added alias: {name} -> {slug}")


@app.command("list")
def list_aliases(
    json_output: Annotated[
        bool, typer.Option("--json", "-j", help="Output as JSON")
    ] = False,
) -> None:
    """List all registered aliases.

    Examples:
        pm alias list
        pm alias list --json
    """
    aliases = load_aliases()

    if json_output:
        console.print(format_json(aliases))
        return

    if not aliases:
        console.print("No aliases registered")
        console.print("Use 'pm alias add <name> <slug>' to create one")
        return

    data = [{"name": name, "slug": slug} for name, slug in sorted(aliases.items())]
    columns = [("name", "Alias"), ("slug", "Prompt Slug")]
    print_table(data, columns, title="Registered Aliases")


@app.command("remove")
def remove_alias(
    name: Annotated[str, typer.Argument(help="Alias name to remove")],
    remove_script: Annotated[
        bool, typer.Option("--remove-script", "-r", help="Also remove installed wrapper script")
    ] = False,
) -> None:
    """Remove an alias.

    Examples:
        pm alias remove pmge
        pm alias remove pmge --remove-script
    """
    aliases = load_aliases()

    if name not in aliases:
        print_error(f"Alias '{name}' not found")
        raise typer.Exit(1)

    del aliases[name]
    save_aliases(aliases)
    print_success(f"Removed alias: {name}")

    if remove_script:
        script_path = DEFAULT_BIN_DIR / name
        if script_path.exists():
            script_path.unlink()
            print_success(f"Removed script: {script_path}")


@app.command("suggest")
def suggest_aliases(
    json_output: Annotated[
        bool, typer.Option("--json", "-j", help="Output as JSON")
    ] = False,
) -> None:
    """Suggest aliases based on frequently used prompts.

    Queries the API for most-used prompts and shows them as candidates.

    Examples:
        pm alias suggest
        pm alias suggest --json
    """
    try:
        with APIClient() as client:
            stats = client.get_stats()
    except APIError as e:
        print_error(f"Failed to get stats: {e}")
        raise typer.Exit(1)

    most_used = stats.get("most_used", [])
    if not most_used:
        console.print("No usage data available yet")
        console.print("Use some prompts first with 'pm get <slug>'")
        return

    aliases = load_aliases()
    aliased_slugs = set(aliases.values())

    suggestions = []
    for prompt in most_used:
        slug = prompt["slug"]
        status = "aliased" if slug in aliased_slugs else "available"
        suggestions.append({
            "slug": slug,
            "usage_count": prompt.get("usage_count", 0),
            "status": status,
        })

    if json_output:
        console.print(format_json(suggestions))
        return

    columns = [("slug", "Slug"), ("usage_count", "Uses"), ("status", "Status")]
    print_table(suggestions, columns, title="Alias Candidates")

    available = [s for s in suggestions if s["status"] == "available"]
    if available:
        console.print(f"\nTo add an alias: pm alias add <name> <slug>")


@app.command("install")
def install_alias(
    name: Annotated[str, typer.Argument(help="Alias name to install")],
    bin_dir: Annotated[
        Path, typer.Option("--bin-dir", "-b", help="Installation directory")
    ] = DEFAULT_BIN_DIR,
) -> None:
    """Install an alias as a wrapper script.

    Creates an executable script in ~/.local/bin/ (or specified directory).

    Examples:
        pm alias install pmge
        pm alias install pmge --bin-dir /usr/local/bin
    """
    aliases = load_aliases()

    if name not in aliases:
        print_error(f"Alias '{name}' not found")
        console.print("Use 'pm alias add <name> <slug>' first")
        raise typer.Exit(1)

    slug = aliases[name]

    # Ensure bin directory exists
    bin_dir.mkdir(parents=True, exist_ok=True)

    # Create wrapper script
    script_path = bin_dir / name
    script_content = get_wrapper_script(slug)
    script_path.write_text(script_content)

    # Make executable
    script_path.chmod(script_path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

    print_success(f"Installed: {script_path}")

    # Check if in PATH
    if not check_path_contains(bin_dir):
        print_warning(f"Warning: {bin_dir} is not in your PATH")
        console.print(f"Add this to your shell config: export PATH=\"{bin_dir}:$PATH\"")


@app.command("export")
def export_aliases() -> None:
    """Output shell alias definitions for sourcing.

    Prints alias definitions that can be added to your shell config.

    Examples:
        pm alias export
        pm alias export >> ~/.bashrc
    """
    aliases = load_aliases()

    if not aliases:
        console.print("# No aliases to export")
        return

    console.print("# Prompt Manager aliases")
    for name, slug in sorted(aliases.items()):
        console.print(f"alias {name}='pm get {slug}'")


@app.command("sync")
def sync_aliases(
    bin_dir: Annotated[
        Path, typer.Option("--bin-dir", "-b", help="Installation directory")
    ] = DEFAULT_BIN_DIR,
) -> None:
    """Install all aliases as wrapper scripts.

    Creates executable scripts for all registered aliases.

    Examples:
        pm alias sync
        pm alias sync --bin-dir ~/bin
    """
    aliases = load_aliases()

    if not aliases:
        console.print("No aliases to sync")
        console.print("Use 'pm alias add <name> <slug>' first")
        return

    # Ensure bin directory exists
    bin_dir.mkdir(parents=True, exist_ok=True)

    installed = 0
    for name, slug in aliases.items():
        script_path = bin_dir / name
        script_content = get_wrapper_script(slug)
        script_path.write_text(script_content)
        script_path.chmod(script_path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        installed += 1

    print_success(f"Installed {installed} wrapper script(s) to {bin_dir}")

    # Check if in PATH
    if not check_path_contains(bin_dir):
        print_warning(f"Warning: {bin_dir} is not in your PATH")
        console.print(f"Add this to your shell config: export PATH=\"{bin_dir}:$PATH\"")
