from unittest.mock import patch

import pytest

from inotes import mcp

def test_mcp_tools():
    assert callable(mcp.doctor)
    assert callable(mcp.list_notes)
    assert callable(mcp.search_notes)
    assert callable(mcp.show_note)
    assert callable(mcp.create_note)

def test_mcp_run_server(monkeypatch):
    called = False
    def mock_run(*args, **kwargs):
        nonlocal called
        called = True
    monkeypatch.setattr(mcp.mcp, "run", mock_run)
    mcp.run_server()
    assert called


class TestMcpToolsDelegateToNotes:
    """Each MCP tool is a thin wrapper — valid input must reach the notes
    layer with the right arguments, and osascript is the only mocked
    boundary."""

    def test_doctor_delegates(self) -> None:
        with patch("inotes.mcp.notes.doctor", return_value=["ok"]) as m:
            assert mcp.doctor() == ["ok"]
        m.assert_called_once_with()

    def test_list_notes_delegates_with_limit(self) -> None:
        with patch("inotes.mcp.notes.list_notes", return_value=["A"]) as m:
            assert mcp.list_notes(limit=5) == ["A"]
        m.assert_called_once_with(limit=5)

    def test_list_notes_default_limit(self) -> None:
        with patch("inotes.mcp.notes.list_notes", return_value=[]) as m:
            mcp.list_notes()
        m.assert_called_once_with(limit=20)

    def test_search_notes_delegates(self) -> None:
        with patch("inotes.mcp.notes.search_notes", return_value=["Hit"]) as m:
            assert mcp.search_notes("q", limit=3) == ["Hit"]
        m.assert_called_once_with("q", limit=3)

    def test_show_note_delegates(self) -> None:
        with patch("inotes.mcp.notes.show_note", return_value="body") as m:
            assert mcp.show_note("Title") == "body"
        m.assert_called_once_with("Title")

    def test_create_note_delegates_with_defaults(self) -> None:
        with patch("inotes.mcp.notes.create_note", return_value="OK created: T") as m:
            mcp.create_note("T")
        m.assert_called_once_with("T", body="", folder="")

    def test_create_note_delegates_with_all_fields(self) -> None:
        with patch("inotes.mcp.notes.create_note", return_value="OK created: T") as m:
            mcp.create_note("T", body="B", folder="F")
        m.assert_called_once_with("T", body="B", folder="F")

    def test_notes_error_propagates_uncaught(self) -> None:
        # The MCP layer does no error translation of its own — a NotesError
        # (e.g. missing Automation permission) must surface to the MCP
        # client, not be swallowed.
        from inotes import notes as notes_module

        with patch(
            "inotes.mcp.notes.doctor",
            side_effect=notes_module.NotesError("denied"),
        ):
            with pytest.raises(notes_module.NotesError, match="denied"):
                mcp.doctor()


class TestMcpToolsInvalidInput:
    """Missing required arguments must fail fast with TypeError, not run
    osascript with a garbage value."""

    def test_show_note_missing_title_raises_type_error(self) -> None:
        with pytest.raises(TypeError):
            mcp.show_note()  # type: ignore[call-arg]

    def test_search_notes_missing_query_raises_type_error(self) -> None:
        with pytest.raises(TypeError):
            mcp.search_notes()  # type: ignore[call-arg]

    def test_create_note_missing_title_raises_type_error(self) -> None:
        with pytest.raises(TypeError):
            mcp.create_note()  # type: ignore[call-arg]

    def test_list_notes_rejects_unexpected_keyword(self) -> None:
        with pytest.raises(TypeError):
            mcp.list_notes(not_a_real_kwarg=5)  # type: ignore[call-arg]
