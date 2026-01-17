"""Main CLI entry point."""

from typing import Optional

import typer

from prompt_manager.cli.commands import config as config_cmd
from prompt_manager.cli.commands import prompt as prompt_cmd
from prompt_manager.cli.commands import search as search_cmd

app = typer.Typer(
    name="pm",
    help="Prompt Manager - A personal prompt management CLI",
    no_args_is_help=True,
)

# Add command groups
app.add_typer(config_cmd.app, name="config")

# Add individual commands from prompt module
app.command("get")(prompt_cmd.get_prompt)
app.command("add")(prompt_cmd.add_prompt)
app.command("edit")(prompt_cmd.edit_prompt)
app.command("delete")(prompt_cmd.delete_prompt)
app.command("note")(prompt_cmd.add_note)

# Add individual commands from search module
app.command("list")(search_cmd.list_prompts)
app.command("search")(search_cmd.search_prompts)
app.command("categories")(search_cmd.list_categories)
app.command("tags")(search_cmd.list_tags)
app.command("random")(search_cmd.random_prompt)
app.command("history")(search_cmd.show_history)
app.command("restore")(search_cmd.restore_version)
app.command("stats")(search_cmd.show_stats)


@app.command("serve")
def serve(
    host: str = typer.Option("0.0.0.0", "--host", "-h", help="Host to bind to"),
    port: int = typer.Option(8000, "--port", "-p", help="Port to bind to"),
    reload: bool = typer.Option(False, "--reload", "-r", help="Enable auto-reload"),
) -> None:
    """Start the API server.

    Examples:
        pm serve
        pm serve --port 8080
        pm serve --reload
    """
    import uvicorn

    uvicorn.run(
        "prompt_manager.api.main:app",
        host=host,
        port=port,
        reload=reload,
    )


@app.command("init-db")
def init_db() -> None:
    """Initialize the database.

    Creates all tables if they don't exist.

    Examples:
        pm init-db
    """
    import asyncio

    from prompt_manager.core.database import init_db as _init_db

    asyncio.run(_init_db())
    typer.echo("Database initialized successfully")


@app.callback()
def main(
    version: Optional[bool] = typer.Option(
        None, "--version", "-V", help="Show version and exit"
    ),
) -> None:
    """Prompt Manager - A personal prompt management CLI."""
    if version:
        from prompt_manager import __version__

        typer.echo(f"Prompt Manager v{__version__}")
        raise typer.Exit()


if __name__ == "__main__":
    app()
