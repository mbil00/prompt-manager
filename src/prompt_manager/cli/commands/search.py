"""Search and list commands."""

from typing import Annotated, Literal, Optional

import typer

from prompt_manager.cli.client import APIClient, NotFoundError
from prompt_manager.cli.output import (
    console,
    format_json,
    format_yaml,
    print_category_table,
    print_error,
    print_prompt_table,
    print_success,
    print_tag_table,
    print_version_table,
)

app = typer.Typer(help="Search and list commands")


@app.command("list")
def list_prompts(
    category: Annotated[
        Optional[str], typer.Option("--category", "-c", help="Filter by category")
    ] = None,
    tags: Annotated[
        Optional[str], typer.Option("--tags", "-t", help="Filter by tags (comma-separated)")
    ] = None,
    sort: Annotated[
        Literal["recent", "popular", "updated", "created"],
        typer.Option("--sort", "-s", help="Sort order"),
    ] = "created",
    page: Annotated[
        int, typer.Option("--page", "-p", help="Page number")
    ] = 1,
    limit: Annotated[
        int, typer.Option("--limit", "-l", help="Items per page")
    ] = 20,
    json_output: Annotated[
        bool, typer.Option("--json", "-j", help="Output as JSON")
    ] = False,
    yaml_output: Annotated[
        bool, typer.Option("--yaml", "-y", help="Output as YAML")
    ] = False,
) -> None:
    """List prompts with optional filtering.

    Examples:
        pm list
        pm list --category code
        pm list --tags python,api
        pm list --sort popular
        pm list --json
    """
    tag_list = [t.strip() for t in tags.split(",")] if tags else None

    with APIClient() as client:
        result = client.list_prompts(
            page=page,
            page_size=limit,
            category=category,
            tags=tag_list,
            sort=sort,
        )

        prompts = result["items"]

        if json_output:
            console.print(format_json(result))
        elif yaml_output:
            console.print(format_yaml(result))
        else:
            if prompts:
                print_prompt_table(prompts)
                console.print(
                    f"\nPage {result['page']}/{result['pages']} "
                    f"(Total: {result['total']})"
                )
            else:
                console.print("No prompts found")


@app.command("search")
def search_prompts(
    query: Annotated[str, typer.Argument(help="Search query")],
    limit: Annotated[
        int, typer.Option("--limit", "-l", help="Max results")
    ] = 20,
    json_output: Annotated[
        bool, typer.Option("--json", "-j", help="Output as JSON")
    ] = False,
    yaml_output: Annotated[
        bool, typer.Option("--yaml", "-y", help="Output as YAML")
    ] = False,
) -> None:
    """Search prompts by content, title, or description.

    Examples:
        pm search "code review"
        pm search python --limit 5
    """
    with APIClient() as client:
        result = client.list_prompts(
            page=1,
            page_size=limit,
            search=query,
        )

        prompts = result["items"]

        if json_output:
            console.print(format_json(prompts))
        elif yaml_output:
            console.print(format_yaml(prompts))
        else:
            if prompts:
                print_prompt_table(prompts)
                console.print(f"\nFound {len(prompts)} results")
            else:
                console.print("No prompts found")


@app.command("categories")
def list_categories(
    json_output: Annotated[
        bool, typer.Option("--json", "-j", help="Output as JSON")
    ] = False,
) -> None:
    """List all categories with prompt counts.

    Examples:
        pm categories
        pm categories --json
    """
    with APIClient() as client:
        categories = client.get_categories()

        if json_output:
            console.print(format_json(categories))
        else:
            if categories:
                print_category_table(categories)
            else:
                console.print("No categories found")


@app.command("tags")
def list_tags(
    json_output: Annotated[
        bool, typer.Option("--json", "-j", help="Output as JSON")
    ] = False,
) -> None:
    """List all tags with counts.

    Examples:
        pm tags
        pm tags --json
    """
    with APIClient() as client:
        tags = client.get_tags()

        if json_output:
            console.print(format_json(tags))
        else:
            if tags:
                print_tag_table(tags)
            else:
                console.print("No tags found")


@app.command("random")
def random_prompt(
    category: Annotated[
        Optional[str], typer.Option("--category", "-c", help="Filter by category")
    ] = None,
    json_output: Annotated[
        bool, typer.Option("--json", "-j", help="Output as JSON")
    ] = False,
) -> None:
    """Get a random prompt.

    Examples:
        pm random
        pm random --category code
    """
    with APIClient() as client:
        try:
            prompt = client.get_random(category)

            if json_output:
                console.print(format_json(prompt))
            else:
                console.print(prompt["content"])

        except NotFoundError:
            print_error("No prompts found")
            raise typer.Exit(1)


@app.command("history")
def show_history(
    slug: Annotated[str, typer.Argument(help="Prompt slug")],
    version: Annotated[
        Optional[int], typer.Option("--version", "-v", help="Get specific version")
    ] = None,
    json_output: Annotated[
        bool, typer.Option("--json", "-j", help="Output as JSON")
    ] = False,
) -> None:
    """Show version history for a prompt.

    Examples:
        pm history my-prompt
        pm history my-prompt --version 2
    """
    with APIClient() as client:
        try:
            if version:
                ver = client.get_version(slug, version)
                if json_output:
                    console.print(format_json(ver))
                else:
                    console.print(f"Version {ver['version']} ({ver['changed_at']})")
                    if ver.get("change_note"):
                        console.print(f"Note: {ver['change_note']}")
                    console.print()
                    console.print(ver["content"])
            else:
                versions = client.list_versions(slug)
                if json_output:
                    console.print(format_json(versions))
                else:
                    if versions:
                        print_version_table(versions)
                    else:
                        console.print("No version history")

        except NotFoundError:
            print_error(f"Prompt '{slug}' not found")
            raise typer.Exit(1)


@app.command("restore")
def restore_version(
    slug: Annotated[str, typer.Argument(help="Prompt slug")],
    version: Annotated[int, typer.Option("--version", "-v", help="Version to restore")],
) -> None:
    """Restore a prompt to a previous version.

    Examples:
        pm restore my-prompt --version 2
    """
    with APIClient() as client:
        try:
            client.restore_version(slug, version)
            print_success(f"Restored {slug} to version {version}")
        except NotFoundError:
            print_error(f"Version {version} of prompt '{slug}' not found")
            raise typer.Exit(1)


@app.command("stats")
def show_stats(
    json_output: Annotated[
        bool, typer.Option("--json", "-j", help="Output as JSON")
    ] = False,
) -> None:
    """Show usage statistics.

    Examples:
        pm stats
        pm stats --json
    """
    with APIClient() as client:
        stats = client.get_stats()

        if json_output:
            console.print(format_json(stats))
        else:
            console.print(f"[bold]Prompt Statistics[/bold]\n")
            console.print(f"Total Prompts: {stats['total_prompts']}")
            console.print(f"Total Categories: {stats['total_categories']}")
            console.print(f"Total Tags: {stats['total_tags']}")
            console.print(f"Total Usage: {stats['total_usage']}")

            if stats["most_used"]:
                console.print("\n[bold]Most Used:[/bold]")
                for p in stats["most_used"][:5]:
                    console.print(f"  - {p['slug']} ({p['usage_count']} uses)")

            if stats["recently_used"]:
                console.print("\n[bold]Recently Used:[/bold]")
                for p in stats["recently_used"][:5]:
                    console.print(f"  - {p['slug']}")
