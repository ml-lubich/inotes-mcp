"""Typer CLI for inotes."""

from __future__ import annotations

import json
import sys
from typing import Annotated

import typer

from inotes import __version__, agent, notes

EPILOG = """\
Examples:

  inotes doctor
  inotes list --limit 20
  inotes search "standup" --json
  inotes show "My Note"
  inotes create --title "Idea" --body "…"

Agents: run `inotes agent guide` for a playbook, `inotes agent schema` for JSON.
"""

app = typer.Typer(
    name="inotes",
    help="Apple Notes CLI — list, search, show, create. Built for humans and agents.",
    epilog=EPILOG,
    no_args_is_help=True,
    rich_markup_mode="rich",
    context_settings={"help_option_names": ["-h", "--help"]},
)
agent_app = typer.Typer(
    name="agent",
    help="Machine-readable schema and playbook for LLM/automation use.",
    no_args_is_help=True,
    rich_markup_mode="rich",
    context_settings={"help_option_names": ["-h", "--help"]},
)
app.add_typer(agent_app, name="agent")


def _die(message: str, code: int = 1) -> None:
    typer.echo(message, err=True)
    raise typer.Exit(code)


def _emit_notes(items: list[str], *, as_json: bool) -> None:
    if as_json:
        typer.echo(json.dumps({"notes": items}))
        return
    for item in items:
        typer.echo(item)


@app.callback()
def main(
    ctx: typer.Context,
    version: Annotated[
        bool,
        typer.Option("--version", "-V", help="Show version and exit.", is_eager=True),
    ] = False,
) -> None:
    """inotes — Apple Notes CLI (+ MCP via apple-notes-mcp)."""
    if version:
        typer.echo(__version__)
        raise typer.Exit()
    if ctx.invoked_subcommand is None:
        typer.echo(ctx.get_help())
        raise typer.Exit()


@app.command()
def doctor() -> None:
    """Verify Notes.app Automation access."""
    try:
        lines = notes.doctor()
    except notes.NotesError:
        _die("FAIL: cannot talk to Notes.app (grant Automation)", code=1)
    for line in lines:
        typer.echo(line)


@app.command("list")
def list_cmd(
    limit: Annotated[int, typer.Option("--limit", "-n", help="Max notes to list.")] = 20,
    as_json: Annotated[bool, typer.Option("--json", help="Emit JSON on stdout.")] = False,
) -> None:
    """List recent note titles."""
    try:
        items = notes.list_notes(limit=limit)
    except notes.NotesError as exc:
        _die(str(exc))
    _emit_notes(items, as_json=as_json)


@app.command("search")
def search_cmd(
    query: Annotated[str, typer.Argument(help="Search query.")],
    limit: Annotated[int, typer.Option("--limit", "-n", help="Max matches.")] = 20,
    as_json: Annotated[bool, typer.Option("--json", help="Emit JSON on stdout.")] = False,
) -> None:
    """Search note titles and bodies."""
    try:
        items = notes.search_notes(query, limit=limit)
    except notes.NotesError as exc:
        _die(str(exc))
    _emit_notes(items, as_json=as_json)


@app.command("show")
def show_cmd(
    title: Annotated[str, typer.Argument(help="Exact note title.")],
) -> None:
    """Show a note by exact title."""
    try:
        text = notes.show_note(title)
    except notes.NotesError as exc:
        _die(str(exc))
    typer.echo(text)


@app.command("create")
def create_cmd(
    title: Annotated[str, typer.Option("--title", help="Note title.")],
    body: Annotated[str, typer.Option("--body", help="Note body.")] = "",
    folder: Annotated[str, typer.Option("--folder", help="Target folder name.")] = "",
) -> None:
    """Create a new note."""
    try:
        message = notes.create_note(title, body=body, folder=folder)
    except notes.NotesError as exc:
        _die(str(exc))
    typer.echo(message)


@app.command("version")
def version_cmd() -> None:
    """Print package version."""
    typer.echo(__version__)


@app.command("mcp")
def mcp_cmd() -> None:
    """Run built-in MCP server over stdio."""
    from inotes.mcp import run_server
    run_server()


@agent_app.command("schema")
def agent_schema_cmd() -> None:
    """Print JSON command contract for agents."""
    typer.echo(json.dumps(agent.build_schema(), indent=2))


@agent_app.command("guide")
def agent_guide_cmd() -> None:
    """Print a short markdown playbook for LLM agents."""
    sys.stdout.write(agent.build_guide())


def run() -> None:
    app()


if __name__ == "__main__":
    run()
