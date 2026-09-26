"""CLI help and agent schema smoke tests."""

from __future__ import annotations

import json

import pytest
from typer.testing import CliRunner

from inotes.cli import app

runner = CliRunner()

HELP_TARGETS: list[list[str]] = [
    ["-h"],
    ["--help"],
    ["doctor", "-h"],
    ["doctor", "--help"],
    ["list", "-h"],
    ["list", "--help"],
    ["search", "-h"],
    ["search", "--help"],
    ["show", "-h"],
    ["show", "--help"],
    ["create", "-h"],
    ["create", "--help"],
    ["version", "-h"],
    ["version", "--help"],
    ["agent", "-h"],
    ["agent", "--help"],
    ["agent", "schema", "-h"],
    ["agent", "schema", "--help"],
    ["agent", "guide", "-h"],
    ["agent", "guide", "--help"],
]


@pytest.mark.parametrize("args", HELP_TARGETS, ids=lambda args: " ".join(args) or "root")
def test_cli_help(args: list[str]) -> None:
    result = runner.invoke(app, args)
    assert result.exit_code == 0, result.output
    assert "Usage:" in result.output or "inotes" in result.output


def test_agent_schema_json() -> None:
    result = runner.invoke(app, ["agent", "schema"])
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["version"] == "0.1.1"
    assert payload["tool"] == "inotes"
    commands = payload["commands"]
    assert isinstance(commands, dict)
    for name in ("doctor", "list", "search", "show", "create", "version"):
        assert name in commands
        assert "params" in commands[name]
    assert any(p.get("name") == "limit" for p in commands["list"]["params"])
    assert any(p.get("name") == "query" for p in commands["search"]["params"])
