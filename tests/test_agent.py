"""Tests for inotes.agent — build_schema and build_guide."""

from __future__ import annotations

from inotes import __version__
from inotes import agent


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


def test_build_guide_returns_playbook() -> None:
    guide = agent.build_guide()
    assert "inotes — Agent Playbook" in guide
    assert "inotes doctor" in guide
    assert "inotes agent schema" in guide
    assert "uv tool upgrade inotes-mcp" in guide
