"""Tests for inotes.notes — osascript helpers with mocked subprocess."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from inotes import notes


class TestAsEscape:
    def test_escapes_backslash_and_quotes(self) -> None:
        assert notes._as_escape('a\\b"c') == 'a\\\\b\\"c'

    def test_empty_string_passes_through(self) -> None:
        assert notes._as_escape("") == ""

    def test_whitespace_only_passes_through(self) -> None:
        assert notes._as_escape("   \t  ") == "   \t  "

    def test_unicode_emoji_passes_through_unescaped(self) -> None:
        # _as_escape only targets backslash/quote; AppleScript string literals
        # don't need extra escaping for unicode, so this should be a no-op.
        text = "café \U0001f600 אבג"  # café, emoji, RTL Hebrew
        assert notes._as_escape(text) == text

    def test_zero_width_and_control_chars_pass_through(self) -> None:
        text = "a​b‍c"  # zero-width space / joiner
        assert notes._as_escape(text) == text

    def test_backslash_quote_injection_attempt_is_neutralized(self) -> None:
        # A string crafted to close the AppleScript string literal and inject
        # another statement must come out fully escaped, not broken open.
        payload = '"; tell application "Finder" to activate --'
        escaped = notes._as_escape(payload)
        assert escaped == '\\"; tell application \\"Finder\\" to activate --'
        # no bare, unescaped quote remains that could terminate the literal
        assert escaped.replace('\\"', "").count('"') == 0

    def test_repeated_backslash_quote_sequences(self) -> None:
        assert notes._as_escape('\\"\\"') == '\\\\\\"\\\\\\"'


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

    def test_whitespace_only_line_is_kept(self) -> None:
        # A line of only spaces is truthy in Python, so it survives the
        # blank-line filter (only literally-empty lines are dropped).
        assert notes._split_lines("a\n   \nb\n") == ["a", "   ", "b"]

    def test_KNOWN_LIMITATION_newline_in_title_is_mis_split(self) -> None:
        """Documents a real, unfixed limitation — not a passing spec.

        list_notes/search_notes join note titles with `linefeed` in the
        AppleScript layer, so a note whose *title* itself contains a literal
        newline is indistinguishable from two separate notes once it reaches
        `_split_lines`. Fixing this needs a different IPC delimiter in the
        AppleScript scripts in notes.py (e.g. NUL or a rare sentinel), which
        is a behavior change beyond a one-line patch, so it is left as-is.
        This test locks in the *current* (buggy) behavior so a future change
        to the delimiter scheme is a deliberate, visible diff here.
        """
        raw_output_for_one_note_titled_two_lines = "Note\nTitle\nOther Note\n"
        assert notes._split_lines(raw_output_for_one_note_titled_two_lines) == [
            "Note",
            "Title",
            "Other Note",
        ]


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

    def test_zero_limit_passed_through_as_string(self) -> None:
        with patch.object(notes, "_run_osascript", return_value="") as mock_run:
            items = notes.list_notes(limit=0)
        assert items == []
        assert mock_run.call_args[0][1:] == ("0",)

    def test_negative_limit_passed_through_as_string(self) -> None:
        # AppleScript's `if n > lim` makes any negative lim behave like 0
        # notes returned; this locks in that the Python layer doesn't reject
        # or mangle a negative value before it reaches osascript.
        with patch.object(notes, "_run_osascript", return_value="") as mock_run:
            items = notes.list_notes(limit=-1)
        assert items == []
        assert mock_run.call_args[0][1:] == ("-1",)

    def test_huge_limit_passed_through_as_string(self) -> None:
        with patch.object(notes, "_run_osascript", return_value="Note A\n") as mock_run:
            items = notes.list_notes(limit=10_000_000)
        assert items == ["Note A"]
        assert mock_run.call_args[0][1:] == ("10000000",)


class TestSearchNotes:
    def test_parses_search_results(self) -> None:
        with patch.object(notes, "_run_osascript", return_value="Match 1\n") as mock_run:
            items = notes.search_notes("standup", limit=5)
        assert items == ["Match 1"]
        assert mock_run.call_args[0][1:] == ("standup", "5")

    def test_zero_limit_returns_no_matches(self) -> None:
        with patch.object(notes, "_run_osascript", return_value="") as mock_run:
            items = notes.search_notes("q", limit=0)
        assert items == []
        assert mock_run.call_args[0][1:] == ("q", "0")

    def test_unicode_emoji_rtl_query_reaches_osascript_unescaped(self) -> None:
        query = "café \U0001f600 אב"
        with patch.object(notes, "_run_osascript", return_value="") as mock_run:
            notes.search_notes(query, limit=5)
        assert mock_run.call_args[0][1] == query

    def test_html_body_in_query_is_not_escaped_specially(self) -> None:
        # notes.py has no HTML-awareness; a query containing markup should
        # travel through as an ordinary string, unmodified beyond _as_escape
        # (search_notes doesn't even escape the query — it's passed as an
        # osascript CLI argv item, not embedded into the script text).
        query = '<b>bold</b> & "quoted"'
        with patch.object(notes, "_run_osascript", return_value="") as mock_run:
            notes.search_notes(query, limit=5)
        assert mock_run.call_args[0][1] == query


class TestShowNote:
    def test_escapes_title_in_script(self) -> None:
        with patch.object(notes, "_run_osascript", return_value="Title\n\nBody") as mock_run:
            text = notes.show_note('Say "hi"')
        assert text == "Title\n\nBody"
        assert '\\"hi\\"' in mock_run.call_args[0][0]

    def test_empty_title_still_produces_a_valid_script(self) -> None:
        with patch.object(notes, "_run_osascript", return_value="") as mock_run:
            notes.show_note("")
        assert 'name is ""' in mock_run.call_args[0][0]

    def test_unicode_emoji_rtl_title_embedded_unescaped(self) -> None:
        title = "café \U0001f600 אב"
        with patch.object(notes, "_run_osascript", return_value="ok") as mock_run:
            notes.show_note(title)
        assert f'name is "{title}"' in mock_run.call_args[0][0]

    def test_very_long_title_is_not_truncated(self) -> None:
        title = "x" * 10_000
        with patch.object(notes, "_run_osascript", return_value="ok") as mock_run:
            notes.show_note(title)
        assert f'name is "{title}"' in mock_run.call_args[0][0]

    def test_returns_body_with_embedded_html_verbatim(self) -> None:
        body_with_html = "Title\n\n<div>note</div> & <script>x</script>"
        with patch.object(notes, "_run_osascript", return_value=body_with_html):
            text = notes.show_note("Title")
        assert text == body_with_html

    def test_can_scope_exact_title_lookup_to_folder(self) -> None:
        with patch.object(notes, "_run_osascript", return_value="Title\n\nBody") as mock_run:
            notes.show_note("Title", folder="Work")
        script = mock_run.call_args.args[0]
        assert 'name is "Title"' in script
        assert 'every folder whose name is "Work"' in script

    def test_show_resolves_exact_title_and_rejects_duplicate_titles(self) -> None:
        with patch.object(notes, "_run_osascript", return_value="Title\n\nBody") as mock_run:
            notes.show_note("Title")
        script = mock_run.call_args_list[0].args[0]
        assert "name is" in script
        assert "count of matchingNotes" in script
        assert "ambiguous" in script.lower()
        assert "container of" in script

    @pytest.mark.parametrize("message", ["Note not found: Missing", "Ambiguous note title: Shared"])
    def test_show_reports_missing_and_ambiguous_titles(self, message: str) -> None:
        with patch.object(notes, "_run_osascript", side_effect=notes.NotesError(message)):
            with pytest.raises(notes.NotesError, match=message.split(":", 1)[0]):
                notes.show_note("Missing" if "Missing" in message else "Shared")


class TestUpdateNote:
    def test_requires_at_least_one_update_field_without_running_osascript(self) -> None:
        with patch.object(notes, "_run_osascript") as mock_run:
            with pytest.raises(ValueError, match="at least one"):
                notes.update_note("Title")
        mock_run.assert_not_called()

    def test_updates_only_supplied_body_and_verifies_readback(self) -> None:
        with patch.object(notes, "_run_osascript", return_value="OK updated: Title") as mock_run:
            result = notes.update_note("Title", body="Revised body")
        assert "updated" in result.lower()
        script = mock_run.call_args_list[0].args[0]
        assert "count of matchingNotes" in script
        assert "set body of targetNote" in script
        assert "plaintext of targetNote" in script
        assert "set name of targetNote" not in script

    def test_explicit_empty_body_clears_note_body(self) -> None:
        with patch.object(notes, "_run_osascript", return_value="OK updated: Title") as mock_run:
            notes.update_note("Title", body="")
        script = mock_run.call_args_list[0].args[0]
        assert "body of targetNote" in script
        assert 'set body of targetNote to ""' in script

    def test_updates_only_supplied_title_and_can_scope_to_folder(self) -> None:
        with patch.object(notes, "_run_osascript", return_value="OK updated: New title") as mock_run:
            notes.update_note("Old title", new_title="New title", folder="Work")
        script = mock_run.call_args_list[0].args[0]
        assert 'name is "Old title"' in script
        assert 'every folder whose name is "Work"' in script
        assert 'set name of targetNote to "New title"' in script
        assert "set body of targetNote" not in script

    @pytest.mark.parametrize("message", ["Note not found: Missing", "Ambiguous note title: Shared"])
    def test_update_does_not_write_when_title_is_missing_or_ambiguous(self, message: str) -> None:
        with patch.object(notes, "_run_osascript", side_effect=notes.NotesError(message)) as mock_run:
            with pytest.raises(notes.NotesError, match=message.split(":", 1)[0]):
                notes.update_note("Missing" if "Missing" in message else "Shared", body="Changed")
        assert mock_run.call_count == 1
        script = mock_run.call_args_list[0].args[0]
        assert script.index("count of matchingNotes") < script.index("set body of targetNote")

    def test_update_passes_escaped_user_values(self) -> None:
        title = 'Say "hi"\\bye'
        body = 'New "quoted" body'
        with patch.object(notes, "_run_osascript", return_value="OK updated") as mock_run:
            notes.update_note(title, new_title=title, body=body)
        script = mock_run.call_args_list[0].args[0]
        assert notes._as_escape(title) in script
        assert notes._as_escape(body) in script
        assert f'name is "{title}"' not in script

    def test_update_verification_failure_is_reported(self) -> None:
        with patch.object(notes, "_run_osascript", side_effect=["WRITE_OK", notes.NotesError("readback mismatch")]):
            with pytest.raises(notes.NotesError, match="readback"):
                notes.update_note("Title", body="New body")


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

    def test_empty_title_and_body_still_creates(self) -> None:
        with patch.object(notes, "_run_osascript", return_value="OK created: ") as mock_run:
            notes.create_note("", body="")
        script = mock_run.call_args[0][0]
        assert 'name:""' in script and 'body:""' in script

    def test_unicode_emoji_title_and_body(self) -> None:
        title = "\U0001f680 launch"
        body = "café notes אב"
        with patch.object(notes, "_run_osascript", return_value=f"OK created: {title}") as mock_run:
            notes.create_note(title, body=body)
        script = mock_run.call_args[0][0]
        assert title in script and body in script

    def test_newline_in_body_is_preserved_literally(self) -> None:
        body = "line1\nline2\nline3"
        with patch.object(notes, "_run_osascript", return_value="OK created: T") as mock_run:
            notes.create_note("T", body=body)
        script = mock_run.call_args[0][0]
        assert body in script

    def test_html_in_body_is_stored_verbatim(self) -> None:
        body = "<b>bold</b> & <script>alert(1)</script>"
        with patch.object(notes, "_run_osascript", return_value="OK created: T") as mock_run:
            notes.create_note("T", body=body)
        assert body in mock_run.call_args[0][0]

    def test_folder_name_with_slash_is_escaped_not_split(self) -> None:
        # A folder name containing a path-like separator must still be
        # treated as one literal AppleScript string, not a nested path.
        with patch.object(notes, "_run_osascript", return_value="OK created: T") as mock_run:
            notes.create_note("T", body="B", folder="Work/2026 Projects")
        script = mock_run.call_args[0][0]
        assert 'tell folder "Work/2026 Projects"' in script

    def test_quote_and_backslash_in_folder_name_is_escaped(self) -> None:
        with patch.object(notes, "_run_osascript", return_value="OK created: T") as mock_run:
            notes.create_note("T", body="B", folder='Say "hi"\\bye')
        script = mock_run.call_args[0][0]
        assert 'tell folder "Say \\"hi\\"\\\\bye"' in script

    def test_injection_attempt_in_title_is_neutralized(self) -> None:
        payload = '"; tell application "Finder" to activate --'
        with patch.object(notes, "_run_osascript", return_value="OK created: x") as mock_run:
            notes.create_note(payload, body="B")
        script = mock_run.call_args[0][0]
        # the raw, unescaped payload must not appear verbatim inside the
        # `name:"..."` literal — only its escaped form should.
        assert f'name:"{payload}"' not in script
        assert notes._as_escape(payload) in script


class TestDeleteNote:
    def test_delete_requires_one_resolved_note_before_mutating(self) -> None:
        with patch.object(notes, "_run_osascript", return_value="OK deleted: Title") as mock_run:
            result = notes.delete_note("Title", folder="Work")
        assert result == "OK deleted: Title"
        script = mock_run.call_args.args[0]
        assert "count of matchingNotes" in script
        assert 'every folder whose name is "Work"' in script
        assert script.index("count of matchingNotes") < script.index("delete targetNote")

    @pytest.mark.parametrize("message", ["Note not found: Missing", "Ambiguous note title: Shared"])
    def test_delete_does_not_mutate_missing_or_ambiguous_title(self, message: str) -> None:
        with patch.object(notes, "_run_osascript", side_effect=notes.NotesError(message)) as mock_run:
            with pytest.raises(notes.NotesError):
                notes.delete_note("Shared")
        assert mock_run.call_count == 1


class TestPinUnpinNote:
    @pytest.mark.parametrize(
        ("operation", "expected"),
        [("pin_note", "PINNED"), ("unpin_note", "UNPINNED")],
    )
    def test_pin_actions_use_exact_title_and_file_menu(self, operation: str, expected: str) -> None:
        with patch.object(notes, "_run_osascript", return_value=expected) as mock_run:
            result = getattr(notes, operation)("Shared", folder="Work")
        assert result == expected
        script = mock_run.call_args.args[0]
        assert 'name is "Shared"' in script
        assert 'every folder whose name is "Work"' in script
        assert script.index("count of matchingNotes") < script.index('tell application "System Events"')
        assert 'menu item "Pin Note"' in script
        assert 'menu item "Unpin Note"' in script
        assert "set selection of application \"Notes\"" in script

    @pytest.mark.parametrize(
        ("operation", "already", "opposite"),
        [
            ("pin_note", "ALREADY_PINNED", "Unpin Note"),
            ("unpin_note", "ALREADY_UNPINNED", "Pin Note"),
        ],
    )
    def test_already_requested_state_is_reported_without_toggling(
        self, operation: str, already: str, opposite: str,
    ) -> None:
        with patch.object(notes, "_run_osascript", return_value=already) as mock_run:
            result = getattr(notes, operation)("Title")
        assert result == already
        script = mock_run.call_args.args[0]
        assert f'return "{already}"' in script
        assert f'menu item "{opposite}"' in script

    @pytest.mark.parametrize(
        ("operation", "raw", "error_type"),
        [
            ("pin_note", "INOTES_ERROR_NOT_FOUND", notes.NoteNotFoundError),
            ("unpin_note", "INOTES_ERROR_AMBIGUOUS:Work, Home", notes.AmbiguousNoteTitleError),
        ],
    )
    def test_missing_or_ambiguous_titles_fail_before_ui_scripting(
        self, operation: str, raw: str, error_type: type[Exception],
    ) -> None:
        with patch.object(notes, "_run_osascript", return_value=raw) as mock_run:
            with pytest.raises(error_type):
                getattr(notes, operation)("Title")
        script = mock_run.call_args.args[0]
        resolution_marker = raw.partition(":")[0]
        assert script.index(resolution_marker) < script.index('tell application "System Events"')

    @pytest.mark.parametrize(
        "raw",
        ["INOTES_ERROR_PIN_NOT_SUPPORTED", "INOTES_ERROR_PIN_UI_STATE_UNKNOWN"],
    )
    def test_unsupported_note_or_unverifiable_menu_state_fails(self, raw: str) -> None:
        with patch.object(notes, "_run_osascript", return_value=raw):
            with pytest.raises(notes.NotesError):
                notes.pin_note("Title")

    def test_ui_scripting_permission_error_is_actionable_and_propagated(self) -> None:
        message = "not authorized to send Apple Events to System Events; allow Accessibility access"
        with patch.object(notes, "_run_osascript", side_effect=notes.NotesError(message)):
            with pytest.raises(notes.NotesError, match="Accessibility"):
                notes.unpin_note("Title")
