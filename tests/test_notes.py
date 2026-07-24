"""Tests for inotes.notes — osascript helpers with mocked subprocess."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from inotes import notes


class TestAsEscape:
    def test_escapes_backslash_and_quotes(self) -> None:
        assert notes._as_escape('a\\b"c') == 'a\\\\b\\"c'


class TestRunOsascript:
    def test_returns_stdout_stripped(self) -> None:
        mock_result = MagicMock(returncode=0, stdout="line1\nline2\n", stderr="")
        with patch("inotes.notes.subprocess.run", return_value=mock_result):
            assert notes._run_osascript("script", "arg") == "line1\nline2"

    def test_raises_notes_error_on_failure(self) -> None:
        mock_result = MagicMock(returncode=1, stdout="", stderr="permission denied")
        with patch("inotes.notes.subprocess.run", return_value=mock_result):
            with pytest.raises(notes.NotesError, match="permission denied"):
                notes._run_osascript("script")

    def test_raises_notes_error_on_empty_stderr(self) -> None:
        mock_result = MagicMock(returncode=2, stdout="", stderr="")
        with patch("inotes.notes.subprocess.run", return_value=mock_result):
            with pytest.raises(notes.NotesError, match="osascript exited 2"):
                notes._run_osascript("script")

    def test_raises_notes_error_on_os_error(self) -> None:
        with patch("inotes.notes.subprocess.run", side_effect=OSError("no osascript")):
            with pytest.raises(notes.NotesError, match="no osascript"):
                notes._run_osascript("script")


class TestSplitLines:
    def test_returns_empty_for_blank_input(self) -> None:
        assert notes._split_lines("") == []

    def test_filters_empty_lines(self) -> None:
        assert notes._split_lines("a\n\nb\n") == ["a", "b"]


class TestDoctor:
    def test_returns_status_lines(self) -> None:
        with patch.object(notes, "_run_osascript", return_value="Notes"):
            lines = notes.doctor()
        assert lines[0] == "ok: Notes.app reachable"
        assert "mcp:" in lines[1]


class TestListNotes:
    def test_parses_note_titles(self) -> None:
        with patch.object(notes, "_run_osascript", return_value="Note A\nNote B\n"):
            items = notes.list_notes(limit=10)
        assert items == ["Note A", "Note B"]


class TestSearchNotes:
    def test_parses_search_results(self) -> None:
        with patch.object(notes, "_run_osascript", return_value="Match 1\n") as mock_run:
            items = notes.search_notes("standup", limit=5)
        assert items == ["Match 1"]
        assert mock_run.call_args[0][1:] == ("standup", "5")


class TestShowNote:
    def test_escapes_title_in_script(self) -> None:
        with patch.object(notes, "_run_osascript", return_value="Title\n\nBody") as mock_run:
            text = notes.show_note('Say "hi"')
        assert text == "Title\n\nBody"
        assert '\\"hi\\"' in mock_run.call_args[0][0]


class TestCreateNote:
    def test_creates_in_default_account(self) -> None:
        with patch.object(notes, "_run_osascript", return_value="OK created: Title") as mock_run:
            msg = notes.create_note("Title", body="Body")
        assert msg == "OK created: Title"
        script = mock_run.call_args[0][0]
        assert "make new note with properties" in script
        assert "tell folder" not in script

    def test_creates_in_named_folder(self) -> None:
        with patch.object(notes, "_run_osascript", return_value="OK created: T") as mock_run:
            notes.create_note("T", body="B", folder="Projects")
        script = mock_run.call_args[0][0]
        assert 'tell folder "Projects"' in script
