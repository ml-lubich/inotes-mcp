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

    def test_version_flag_real_invocation(self) -> None:
        # Regression: without invoke_without_command=True on the Typer app,
        # `inotes -V` (an eager option with no subcommand) fails with
        # "Missing command." instead of printing the version and exiting 0.
        result = runner.invoke(app, ["-V"])
        assert result.exit_code == 0, result.output
        assert result.output.strip() == "0.1.1"

    def test_long_version_flag_real_invocation(self) -> None:
        result = runner.invoke(app, ["--version"])
        assert result.exit_code == 0, result.output
        assert result.output.strip() == "0.1.1"

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

    def test_list_json_short_flag(self) -> None:
        with patch("inotes.cli.notes.list_notes", return_value=["Note A"]):
            result = runner.invoke(app, ["list", "-j"])
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

    def test_show_can_disambiguate_exact_title_by_folder(self) -> None:
        with patch("inotes.cli.notes.show_note", return_value="Title\n\nBody") as mock_show:
            result = runner.invoke(app, ["show", "Title", "--folder", "Work"])
        assert result.exit_code == 0, result.output
        mock_show.assert_called_once_with("Title", folder="Work")


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


class TestUpdateCmd:
    def test_update_success_for_body_and_title(self) -> None:
        with patch("inotes.cli.notes.update_note", return_value="OK updated: New title") as mock_update:
            result = runner.invoke(app, [
                "update", "--title", "Old title", "--new-title", "New title",
                "--body", "Revised body", "--folder", "Work",
            ])
        assert result.exit_code == 0, result.output
        assert "OK updated" in result.output
        mock_update.assert_called_once_with(
            "Old title", new_title="New title", body="Revised body", folder="Work",
        )

    def test_update_requires_at_least_one_field(self) -> None:
        with patch("inotes.cli.notes.update_note") as mock_update:
            result = runner.invoke(app, ["update", "--title", "Old title", "--folder", "Work"])
        assert result.exit_code != 0
        assert "at least one" in result.output.lower()
        mock_update.assert_not_called()

    @pytest.mark.parametrize("message", ["Note not found: Missing", "Ambiguous note title: Shared"])
    def test_update_reports_missing_or_ambiguous_title(self, message: str) -> None:
        with patch("inotes.cli.notes.update_note", side_effect=notes.NotesError(message)):
            result = runner.invoke(app, ["update", "--title", "Missing", "--body", "Changed"])
        assert result.exit_code == 1
        assert message.split(":", 1)[0] in result.output

    def test_update_help_documents_partial_edits(self) -> None:
        for flag in ("-h", "--help"):
            result = runner.invoke(app, ["update", flag])
            assert result.exit_code == 0, result.output
            assert "--title" in result.output
            assert "--new-title" in result.output
            assert "--body" in result.output
            assert "--folder" in result.output
            assert "omitted" in result.output.lower() or "preserved" in result.output.lower()


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


class TestBadArgExitCodes:
    """Missing/invalid required args must fail with click's usage exit code (2),
    not crash with a traceback or silently succeed."""

    def test_create_without_title_is_a_usage_error(self) -> None:
        result = runner.invoke(app, ["create", "--body", "no title given"])
        assert result.exit_code == 2

    def test_search_without_query_is_a_usage_error(self) -> None:
        result = runner.invoke(app, ["search"])
        assert result.exit_code == 2

    def test_show_without_title_is_a_usage_error(self) -> None:
        result = runner.invoke(app, ["show"])
        assert result.exit_code == 2

    def test_unknown_option_is_a_usage_error(self) -> None:
        result = runner.invoke(app, ["list", "--not-a-real-flag"])
        assert result.exit_code == 2

    def test_unknown_subcommand_is_a_usage_error(self) -> None:
        result = runner.invoke(app, ["not-a-real-command"])
        assert result.exit_code == 2

    def test_list_limit_not_an_integer_is_a_usage_error(self) -> None:
        result = runner.invoke(app, ["list", "--limit", "not-a-number"])
        assert result.exit_code == 2


class TestLimitEdgeCasesAtCliLevel:
    def test_list_limit_zero(self) -> None:
        with patch("inotes.cli.notes.list_notes", return_value=[]) as mock_list:
            result = runner.invoke(app, ["list", "--limit", "0"])
        assert result.exit_code == 0
        mock_list.assert_called_once_with(limit=0)

    def test_list_negative_limit_reaches_notes_layer_unmodified(self) -> None:
        with patch("inotes.cli.notes.list_notes", return_value=[]) as mock_list:
            result = runner.invoke(app, ["list", "--limit", "-1"])
        assert result.exit_code == 0
        mock_list.assert_called_once_with(limit=-1)

    def test_search_huge_limit(self) -> None:
        with patch("inotes.cli.notes.search_notes", return_value=[]) as mock_search:
            result = runner.invoke(app, ["search", "q", "--limit", "10000000"])
        assert result.exit_code == 0
        mock_search.assert_called_once_with("q", limit=10_000_000)


class TestNoColorEnvVar:
    """NO_COLOR must not change exit codes or break output parsing —
    only styling."""

    def test_help_exit_code_unaffected_by_no_color(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("NO_COLOR", "1")
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "Usage:" in result.output

    def test_json_output_still_valid_json_with_no_color(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("NO_COLOR", "1")
        with patch("inotes.cli.notes.list_notes", return_value=["Note A"]):
            result = runner.invoke(app, ["list", "--json"])
        assert result.exit_code == 0
        assert json.loads(result.output) == {"notes": ["Note A"]}


class TestUnicodeAndInjectionArgsAtCliLevel:
    """The CLI layer itself does no validation/escaping of note content —
    confirm arbitrary text (unicode, quotes, newlines) flows through to the
    notes backend unchanged, and back out unchanged."""

    def test_create_with_unicode_title_and_body(self) -> None:
        title = "\U0001f680 café אב"
        with patch(
            "inotes.cli.notes.create_note", return_value=f"OK created: {title}"
        ) as mock_create:
            result = runner.invoke(app, ["create", "--title", title, "--body", "hi"])
        assert result.exit_code == 0
        mock_create.assert_called_once_with(title, body="hi", folder="")
        assert title in result.output

    def test_search_with_quotes_and_backslashes(self) -> None:
        query = 'say "hi"\\bye'
        with patch("inotes.cli.notes.search_notes", return_value=["Hit"]) as mock_search:
            result = runner.invoke(app, ["search", query])
        assert result.exit_code == 0
        mock_search.assert_called_once_with(query, limit=20)

    def test_show_title_with_embedded_newline_argument(self) -> None:
        title = "Line1\nLine2"
        with patch("inotes.cli.notes.show_note", return_value="body") as mock_show:
            result = runner.invoke(app, ["show", title])
        assert result.exit_code == 0
        mock_show.assert_called_once_with(title)
