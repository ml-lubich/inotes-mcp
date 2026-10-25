"""Tests for inotes.agent — build_schema and build_guide."""

from __future__ import annotations

from inotes import __version__
from inotes import agent
from inotes.cli import app
from inotes.mcp import mcp
from typer.main import get_command


def test_build_schema_structure() -> None:
    schema = agent.build_schema()
    assert schema["version"] == __version__
    assert schema["tool"] == "inotes"
    commands = schema["commands"]
    assert isinstance(commands, dict)
    for name in ("doctor", "list", "search", "show", "create", "edit", "delete", "update", "version"):
        assert name in commands
        assert "params" in commands[name]
    assert commands["update"]["params"] == []


def test_schema_covers_all_cli_commands_and_mcp_tools() -> None:
    schema = agent.build_schema()
    cli_commands = set(get_command(app).commands) - {"agent"}
    assert set(schema["commands"]) == cli_commands
    assert set(schema["mcp_tools"]) == {
        tool.name for tool in mcp._tool_manager.list_tools()
    }


def test_build_guide_returns_playbook() -> None:
    guide = agent.build_guide()
    assert "inotes — Agent Playbook" in guide
    assert "inotes doctor" in guide
    assert "inotes agent schema" in guide
    assert "uv tool upgrade inotes-mcp" in guide
