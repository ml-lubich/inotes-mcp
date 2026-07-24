"""CLI command tests with mocked notes backend."""

from __future__ import annotations

import json
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from inotes.cli import app
from inotes import notes

runner = CliRunner()


class TestMainCallback:
    def test_version_flag_via_callback(self) -> None:
        import typer
        from unittest.mock import MagicMock

        from inotes.cli import main

        ctx = MagicMock()
        ctx.invoked_subcommand = None
        with pytest.raises(typer.Exit):
            main(ctx, version=True)

    def test_no_subcommand_shows_help(self) -> None:
        result = runner.invoke(app, [])
        assert result.exit_code in (0, 2)
        assert "Usage:" in result.output or "inotes" in result.output

    def test_callback_help_when_no_subcommand(self) -> None:
        import typer
        from unittest.mock import MagicMock

        from inotes.cli import main

        ctx = MagicMock()
        ctx.invoked_subcommand = None
        ctx.get_help.return_value = "Usage: inotes"
        with pytest.raises(typer.Exit):
            main(ctx, version=False)
        ctx.get_help.assert_called_once()


class TestDoctorCmd:
    def test_doctor_success(self) -> None:
        with patch(
            "inotes.cli.notes.doctor",
            return_value=["ok: Notes.app reachable", "mcp: apple-notes-mcp"],
        ):
            result = runner.invoke(app, ["doctor"])
        assert result.exit_code == 0
        assert "ok: Notes.app reachable" in result.output

    def test_doctor_failure(self) -> None:
        with patch("inotes.cli.notes.doctor", side_effect=notes.NotesError("denied")):
            result = runner.invoke(app, ["doctor"])
        assert result.exit_code == 1
        assert "FAIL:" in result.stderr or "FAIL:" in result.output


class TestListCmd:
    def test_list_plain(self) -> None:
        with patch("inotes.cli.notes.list_notes", return_value=["Note A", "Note B"]):
            result = runner.invoke(app, ["list", "--limit", "5"])
        assert result.exit_code == 0
        assert "Note A" in result.output
        assert "Note B" in result.output

    def test_list_json(self) -> None:
        with patch("inotes.cli.notes.list_notes", return_value=["Note A"]):
            result = runner.invoke(app, ["list", "--json"])
        assert result.exit_code == 0
        assert json.loads(result.output) == {"notes": ["Note A"]}

    def test_list_failure(self) -> None:
        with patch(
            "inotes.cli.notes.list_notes",
            side_effect=notes.NotesError("list fail"),
        ):
            result = runner.invoke(app, ["list"])
        assert result.exit_code == 1


class TestSearchCmd:
    def test_search_plain(self) -> None:
        with patch("inotes.cli.notes.search_notes", return_value=["Hit"]):
            result = runner.invoke(app, ["search", "standup"])
        assert result.exit_code == 0
        assert "Hit" in result.output

    def test_search_json(self) -> None:
        with patch("inotes.cli.notes.search_notes", return_value=["Hit"]):
            result = runner.invoke(app, ["search", "q", "--json"])
        assert result.exit_code == 0
        assert json.loads(result.output) == {"notes": ["Hit"]}

    def test_search_failure(self) -> None:
        with patch(
            "inotes.cli.notes.search_notes",
            side_effect=notes.NotesError("search fail"),
        ):
            result = runner.invoke(app, ["search", "q"])
        assert result.exit_code == 1


class TestShowCmd:
    def test_show_success(self) -> None:
        with patch("inotes.cli.notes.show_note", return_value="Title\n\nBody"):
            result = runner.invoke(app, ["show", "Title"])
        assert result.exit_code == 0
        assert "Body" in result.output

    def test_show_failure(self) -> None:
        with patch(
            "inotes.cli.notes.show_note",
            side_effect=notes.NotesError("not found"),
        ):
            result = runner.invoke(app, ["show", "Missing"])
        assert result.exit_code == 1


class TestCreateCmd:
    def test_create_success(self) -> None:
        with patch("inotes.cli.notes.create_note", return_value="OK created: Idea"):
            result = runner.invoke(
                app,
                ["create", "--title", "Idea", "--body", "text", "--folder", "Work"],
            )
        assert result.exit_code == 0
        assert "OK created" in result.output

    def test_create_failure(self) -> None:
        with patch(
            "inotes.cli.notes.create_note",
            side_effect=notes.NotesError("create fail"),
        ):
            result = runner.invoke(app, ["create", "--title", "Idea"])
        assert result.exit_code == 1


class TestVersionCmd:
    def test_version_command(self) -> None:
        result = runner.invoke(app, ["version"])
        assert result.exit_code == 0
        assert "0.1." in result.output


class TestAgentCmds:
    def test_agent_schema(self) -> None:
        result = runner.invoke(app, ["agent", "schema"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["tool"] == "inotes"

    def test_agent_guide(self) -> None:
        result = runner.invoke(app, ["agent", "guide"])
        assert result.exit_code == 0
        assert "inotes — Agent Playbook" in result.output


class TestRunEntry:
    def test_run_invokes_app(self) -> None:
        from inotes.cli import run

        with patch("inotes.cli.app") as mock_app:
            run()
        mock_app.assert_called_once()
