"""Prompt CRUD commands: get, add, edit, delete."""

import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Annotated, Optional

import typer

from prompt_manager.cli.client import APIClient, NotFoundError
from prompt_manager.cli.output import (
    console,
    format_json,
    format_yaml,
    print_error,
    print_success,
)
from prompt_manager.core.config import settings

app = typer.Typer(help="Prompt management commands")


@app.command("get")
def get_prompt(
    slug: Annotated[str, typer.Argument(help="Prompt slug")],
    json_output: Annotated[
        bool, typer.Option("--json", "-j", help="Output as JSON")
    ] = False,
    yaml_output: Annotated[
        bool, typer.Option("--yaml", "-y", help="Output as YAML")
    ] = False,
    var: Annotated[
        Optional[list[str]],
        typer.Option("--var", "-v", help="Template variable (key=value, use key=- to read from stdin)"),
    ] = None,
    stdin_var: Annotated[
        Optional[str],
        typer.Option("--stdin", "-i", help="Read stdin and use as this variable name"),
    ] = None,
    append_stdin: Annotated[
        bool, typer.Option("--append", "-a", help="Append stdin to the prompt output"),
    ] = False,
    no_usage: Annotated[
        bool, typer.Option("--no-usage", help="Don't increment usage count")
    ] = False,
) -> None:
    """Get a prompt by slug.

    For piping to other commands (like claude), use --stdin or --append:

    Examples:
        pm get my-prompt
        pm get my-prompt --json
        pm get template-prompt --var name=John --var topic=coding

        # Read stdin into a template variable
        cat error.txt | pm get explain-error --stdin error
        echo "my code" | pm get review-code --stdin code

        # Append stdin to the prompt
        cat error.txt | pm get explain-error --append

        # Pipe to claude
        cat error.txt | pm get explain-error --stdin error | claude -p
    """
    # Read stdin if needed (must be done before any other stdin operations)
    stdin_content: str | None = None
    if not sys.stdin.isatty():
        stdin_content = sys.stdin.read()

    variables: dict[str, str] = {}

    # Handle --stdin flag (shorthand for --var name=<stdin>)
    if stdin_var:
        if stdin_content is None:
            print_error("--stdin requires piped input")
            raise typer.Exit(1)
        variables[stdin_var] = stdin_content.strip()

    # Handle --var flags
    if var:
        for v in var:
            if "=" not in v:
                print_error(f"Invalid variable format: {v} (expected key=value)")
                raise typer.Exit(1)
            key, value = v.split("=", 1)
            # Support reading from stdin with key=-
            if value == "-":
                if stdin_content is None:
                    print_error(f"Variable '{key}=-' requires piped input")
                    raise typer.Exit(1)
                variables[key] = stdin_content.strip()
            else:
                variables[key] = value

    with APIClient() as client:
        try:
            prompt = client.get_prompt(slug, increment_usage=not no_usage)

            # Render template if variables provided
            if variables:
                from prompt_manager.core.templates import TemplateEngine

                engine = TemplateEngine()
                content = engine.render(prompt["content"], variables)
            else:
                content = prompt["content"]

            # Append stdin if requested
            if append_stdin and stdin_content:
                content = content.rstrip() + "\n\n" + stdin_content

            # Output based on format
            if json_output:
                if variables:
                    prompt["rendered_content"] = content
                console.print(format_json(prompt))
            elif yaml_output:
                if variables:
                    prompt["rendered_content"] = content
                console.print(format_yaml(prompt))
            else:
                # Plain output - just the content (use print for clean piping)
                print(content, end="" if content.endswith("\n") else "\n")

        except NotFoundError:
            print_error(f"Prompt '{slug}' not found")
            raise typer.Exit(1)


@app.command("add")
def add_prompt(
    slug: Annotated[str, typer.Argument(help="Prompt slug")],
    title: Annotated[
        Optional[str], typer.Option("--title", "-t", help="Prompt title")
    ] = None,
    content: Annotated[
        Optional[str], typer.Option("--content", "-c", help="Prompt content")
    ] = None,
    description: Annotated[
        Optional[str], typer.Option("--description", "-d", help="Description")
    ] = None,
    category: Annotated[
        Optional[str], typer.Option("--category", help="Category")
    ] = None,
    tags: Annotated[
        Optional[str], typer.Option("--tags", help="Comma-separated tags")
    ] = None,
    from_file: Annotated[
        Optional[Path], typer.Option("--from-file", "-f", help="Read content from file")
    ] = None,
    source_url: Annotated[
        Optional[str], typer.Option("--source-url", "-u", help="Source URL")
    ] = None,
) -> None:
    """Add a new prompt.

    Content can be provided via:
    - --content flag
    - --from-file flag
    - stdin (pipe)

    Examples:
        pm add my-prompt --title "My Prompt" --content "Hello {{name}}"
        pm add my-prompt --title "My Prompt" --from-file prompt.txt
        echo "Hello world" | pm add my-prompt --title "My Prompt"
    """
    # Determine content source
    if content:
        prompt_content = content
    elif from_file:
        if not from_file.exists():
            print_error(f"File not found: {from_file}")
            raise typer.Exit(1)
        prompt_content = from_file.read_text()
    elif not sys.stdin.isatty():
        # Read from pipe
        prompt_content = sys.stdin.read()
    else:
        print_error("Content required. Use --content, --from-file, or pipe input.")
        raise typer.Exit(1)

    # Use slug as title if not provided
    if not title:
        title = slug.replace("-", " ").title()

    # Parse tags
    tag_list = [t.strip() for t in tags.split(",")] if tags else []

    data = {
        "slug": slug,
        "title": title,
        "content": prompt_content,
        "description": description,
        "category": category,
        "tags": tag_list,
        "source_url": source_url,
    }
    # Remove None values
    data = {k: v for k, v in data.items() if v is not None}

    with APIClient() as client:
        prompt = client.create_prompt(data)
        print_success(f"Created prompt: {prompt['slug']}")


@app.command("edit")
def edit_prompt(
    slug: Annotated[str, typer.Argument(help="Prompt slug")],
    title: Annotated[
        Optional[str], typer.Option("--title", "-t", help="New title")
    ] = None,
    content: Annotated[
        Optional[str], typer.Option("--content", "-c", help="New content")
    ] = None,
    description: Annotated[
        Optional[str], typer.Option("--description", "-d", help="New description")
    ] = None,
    category: Annotated[
        Optional[str], typer.Option("--category", help="New category")
    ] = None,
    tags: Annotated[
        Optional[str], typer.Option("--tags", help="New tags (comma-separated)")
    ] = None,
    editor: Annotated[
        bool, typer.Option("--editor", "-e", help="Open content in editor")
    ] = False,
    change_note: Annotated[
        Optional[str], typer.Option("--note", "-n", help="Change note for version history")
    ] = None,
) -> None:
    """Edit an existing prompt.

    Without flags, opens the prompt content in your editor.
    With flags, updates specific fields directly.

    Examples:
        pm edit my-prompt                    # Open in editor
        pm edit my-prompt --title "New Title"
        pm edit my-prompt --tags "python,api"
    """
    with APIClient() as client:
        try:
            prompt = client.get_prompt(slug, increment_usage=False)
        except NotFoundError:
            print_error(f"Prompt '{slug}' not found")
            raise typer.Exit(1)

        update_data: dict = {}

        # If no specific fields and no editor flag, default to editor mode
        if not any([title, content, description, category, tags]) or editor:
            # Open in editor
            editor_cmd = os.environ.get("EDITOR", settings.editor)
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".txt", delete=False
            ) as f:
                f.write(prompt["content"])
                temp_path = f.name

            try:
                subprocess.run([editor_cmd, temp_path], check=True)
                with open(temp_path) as f:
                    new_content = f.read()

                if new_content != prompt["content"]:
                    update_data["content"] = new_content
                else:
                    print_warning("No changes made")
                    return
            finally:
                os.unlink(temp_path)
        else:
            if title:
                update_data["title"] = title
            if content:
                update_data["content"] = content
            if description:
                update_data["description"] = description
            if category:
                update_data["category"] = category
            if tags:
                update_data["tags"] = [t.strip() for t in tags.split(",")]

        if change_note:
            update_data["change_note"] = change_note

        if update_data:
            client.update_prompt(slug, update_data)
            print_success(f"Updated prompt: {slug}")


def print_warning(message: str) -> None:
    """Print warning message."""
    console.print(f"[yellow]{message}[/yellow]")


@app.command("delete")
def delete_prompt(
    slug: Annotated[str, typer.Argument(help="Prompt slug")],
    force: Annotated[
        bool, typer.Option("--force", "-f", help="Skip confirmation")
    ] = False,
) -> None:
    """Delete a prompt.

    Examples:
        pm delete my-prompt
        pm delete my-prompt --force
    """
    with APIClient() as client:
        try:
            prompt = client.get_prompt(slug, increment_usage=False)
        except NotFoundError:
            print_error(f"Prompt '{slug}' not found")
            raise typer.Exit(1)

        if not force:
            confirm = typer.confirm(
                f"Delete prompt '{prompt['title']}' ({slug})?"
            )
            if not confirm:
                print_warning("Cancelled")
                raise typer.Exit(0)

        client.delete_prompt(slug)
        print_success(f"Deleted prompt: {slug}")


@app.command("note")
def add_note(
    slug: Annotated[str, typer.Argument(help="Prompt slug")],
    success: Annotated[
        Optional[str], typer.Option("--success", "-s", help="Success note")
    ] = None,
    failure: Annotated[
        Optional[str], typer.Option("--failure", "-f", help="Failure note")
    ] = None,
) -> None:
    """Add success or failure notes to a prompt.

    Examples:
        pm note my-prompt --success "Worked great for code review"
        pm note my-prompt --failure "Didn't work well with long inputs"
    """
    if not success and not failure:
        print_error("Provide --success or --failure note")
        raise typer.Exit(1)

    update_data: dict = {}

    with APIClient() as client:
        try:
            prompt = client.get_prompt(slug, increment_usage=False)
        except NotFoundError:
            print_error(f"Prompt '{slug}' not found")
            raise typer.Exit(1)

        if success:
            existing = prompt.get("success_notes") or ""
            update_data["success_notes"] = (
                f"{existing}\n\n---\n\n{success}" if existing else success
            )

        if failure:
            existing = prompt.get("failure_notes") or ""
            update_data["failure_notes"] = (
                f"{existing}\n\n---\n\n{failure}" if existing else failure
            )

        client.update_prompt(slug, update_data)
        print_success(f"Added note to: {slug}")
