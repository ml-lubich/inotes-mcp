from unittest.mock import patch

import pytest

from inotes import mcp, notes

def test_mcp_tools():
    assert callable(mcp.doctor)
    assert callable(mcp.list_notes)
    assert callable(mcp.search_notes)
    assert callable(mcp.show_note)
    assert callable(mcp.create_note)
    assert callable(mcp.edit_note)
    assert callable(mcp.delete_note)
    assert callable(mcp.pin_note)
    assert callable(mcp.unpin_note)
    assert callable(mcp.attach_file_to_note)
    assert callable(mcp.list_note_attachments)
    assert callable(mcp.list_note_links)

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

    def test_show_note_can_scope_to_folder(self) -> None:
        with patch("inotes.mcp.notes.show_note", return_value="body") as m:
            assert mcp.show_note("Title", folder="Work") == "body"
        m.assert_called_once_with("Title", folder="Work")

    def test_create_note_delegates_with_defaults(self) -> None:
        with patch("inotes.mcp.notes.create_note", return_value="OK created: T") as m:
            mcp.create_note("T")
        m.assert_called_once_with("T", body="", folder="")

    def test_create_note_delegates_with_all_fields(self) -> None:
        with patch("inotes.mcp.notes.create_note", return_value="OK created: T") as m:
            mcp.create_note("T", body="B", folder="F")
        m.assert_called_once_with("T", body="B", folder="F")

    def test_edit_note_delegates_partial_fields_and_scope(self) -> None:
        with patch("inotes.mcp.notes.update_note", return_value="OK updated: New title") as m:
            result = mcp.edit_note("Old title", new_title="New title", body="New body", folder="Work")
        assert result == "OK updated: New title"
        m.assert_called_once_with(
            "Old title", new_title="New title", body="New body", folder="Work",
        )

    def test_edit_note_preserves_omitted_fields_by_default(self) -> None:
        with patch("inotes.mcp.notes.update_note", side_effect=ValueError("at least one update field is required")) as m:
            with pytest.raises(ValueError, match="at least one"):
                mcp.edit_note("Title")
        m.assert_called_once_with("Title", new_title=None, body=None, folder=None)

    def test_delete_note_delegates_scope(self) -> None:
        with patch("inotes.mcp.notes.delete_note", return_value="OK deleted: Title") as m:
            assert mcp.delete_note("Title", folder="Work") == "OK deleted: Title"
        m.assert_called_once_with("Title", folder="Work")

    @pytest.mark.parametrize(
        ("tool", "core", "state"),
        [("pin_note", "pin_note", "PINNED"), ("unpin_note", "unpin_note", "UNPINNED")],
    )
    def test_pin_tools_delegate_with_optional_folder(self, tool: str, core: str, state: str) -> None:
        with patch(f"inotes.mcp.notes.{core}", return_value=state) as mock_action:
            assert getattr(mcp, tool)("Shared", folder="Work") == state
        mock_action.assert_called_once_with("Shared", folder="Work")

    @pytest.mark.parametrize("tool", ["pin_note", "unpin_note"])
    def test_pin_tool_propagates_permission_and_resolution_errors(self, tool: str) -> None:
        with patch(f"inotes.mcp.notes.{tool}", side_effect=notes.NotesError("UI scripting permission required")):
            with pytest.raises(notes.NotesError, match="permission"):
                getattr(mcp, tool)("Title")

    def test_attach_file_to_note_delegates_path_and_folder(self) -> None:
        expected = {"id": "att-1", "name": "audio.wav", "title": "Voice note"}
        with patch("inotes.mcp.notes.attach_file_to_note", return_value=expected) as mock_attach:
            result = mcp.attach_file_to_note("Voice note", "/tmp/audio.wav", folder="Audio")
        assert result == expected
        mock_attach.assert_called_once_with("Voice note", "/tmp/audio.wav", folder="Audio")

    def test_list_note_attachments_delegates_scope(self) -> None:
        expected = [{"id": "att-1", "name": "photo.png"}]
        with patch("inotes.mcp.notes.list_note_attachments", return_value=expected) as mock_list:
            assert mcp.list_note_attachments("Idea", folder="Media") == expected
        mock_list.assert_called_once_with("Idea", folder="Media")

    def test_list_note_links_delegates(self) -> None:
        expected = [{"note_title": "Reference", "label": "Example", "url": "https://example.test"}]
        with patch("inotes.mcp.notes.list_note_links", return_value=expected) as mock_list:
            assert mcp.list_note_links() == expected
        mock_list.assert_called_once_with()

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

    def test_edit_note_missing_title_raises_type_error(self) -> None:
        with pytest.raises(TypeError):
            mcp.edit_note()  # type: ignore[call-arg]

    @pytest.mark.parametrize("tool", ["pin_note", "unpin_note"])
    def test_pin_tool_missing_title_raises_type_error(self, tool: str) -> None:
        with pytest.raises(TypeError):
            getattr(mcp, tool)()  # type: ignore[call-arg]

    def test_list_notes_rejects_unexpected_keyword(self) -> None:
        with pytest.raises(TypeError):
            mcp.list_notes(not_a_real_kwarg=5)  # type: ignore[call-arg]
