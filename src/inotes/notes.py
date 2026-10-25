"""Apple Notes operations via osascript."""

from __future__ import annotations

import subprocess


class NotesError(Exception):
    """Notes.app interaction failed."""


class NoteNotFoundError(NotesError):
    """No note matched the exact title and optional folder."""


class AmbiguousNoteTitleError(NotesError):
    """More than one note matched the exact title and optional folder."""


def _as_escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def _run_osascript(script: str, *argv: str) -> str:
    cmd: list[str] = ["osascript", "-"]
    cmd.extend(argv)
    try:
        result = subprocess.run(
            cmd,
            input=script,
            text=True,
            capture_output=True,
            check=False,
        )
    except OSError as exc:
        raise NotesError(str(exc)) from exc
    if result.returncode != 0:
        stderr = (result.stderr or "").strip()
        raise NotesError(stderr or f"osascript exited {result.returncode}")
    return (result.stdout or "").rstrip("\n")


def _note_matches(title: str, folder: str | None = None) -> str:
    """AppleScript statements that resolve exact titles without guessing."""
    escaped_title = _as_escape(title)
    script = f'set matchingNotes to every note whose name is "{escaped_title}"\n'
    if folder:
        escaped_folder = _as_escape(folder)
        script += f'''set sourceFolders to every folder whose name is "{escaped_folder}"
set scopedNotes to {{}}
repeat with candidateNote in matchingNotes
  if (container of candidateNote) is in sourceFolders then
    set end of scopedNotes to contents of candidateNote
  end if
end repeat
set matchingNotes to scopedNotes
'''
    script += '''set matchCount to count of matchingNotes
if matchCount is 0 then return "INOTES_ERROR_NOT_FOUND"
if matchCount > 1 then
  set matchingFolders to ""
  repeat with candidateNote in matchingNotes
    set candidateFolder to name of container of candidateNote as text
    if matchingFolders does not contain candidateFolder then
      if matchingFolders is not "" then set matchingFolders to matchingFolders & ", "
      set matchingFolders to matchingFolders & candidateFolder
    end if
  end repeat
  return "INOTES_ERROR_AMBIGUOUS:" & matchingFolders
end if
set targetNote to item 1 of matchingNotes
'''
    return script


def _raise_resolution_error(raw: str, title: str) -> None:
    if raw == "INOTES_ERROR_NOT_FOUND":
        raise NoteNotFoundError(f"Note not found: {title}")
    if raw.startswith("INOTES_ERROR_AMBIGUOUS:"):
        folders = raw.partition(":")[2]
        detail = f" (folders: {folders})" if folders else ""
        raise AmbiguousNoteTitleError(f"Ambiguous note title: {title}{detail}")


def doctor() -> list[str]:
    """Return status lines when Notes.app is reachable."""
    _run_osascript('tell application "Notes" to get name')
    return [
        "ok: Notes.app reachable",
        "mcp: apple-notes-mcp — also in tool registry",
    ]


def list_notes(limit: int = 20) -> list[str]:
    script = """\
on run argv
  set lim to (item 1 of argv) as integer
  set out to ""
  tell application "Notes"
    set nlist to notes
    set n to count of nlist
    if n > lim then set n to lim
    repeat with i from 1 to n
      set noteRef to item i of nlist
      set out to out & (name of noteRef) & linefeed
    end repeat
  end tell
  return out
end run
"""
    raw = _run_osascript(script, str(limit))
    return _split_lines(raw)


def search_notes(query: str, limit: int = 20) -> list[str]:
    script = """\
on run argv
  set q to item 1 of argv
  set lim to (item 2 of argv) as integer
  set out to ""
  set countFound to 0
  tell application "Notes"
    repeat with noteRef in notes
      if countFound ≥ lim then exit repeat
      set nm to name of noteRef
      set bodyText to ""
      try
        set bodyText to plaintext of noteRef
      end try
      if nm contains q or bodyText contains q then
        set out to out & nm & linefeed
        set countFound to countFound + 1
      end if
    end repeat
  end tell
  return out
end run
"""
    raw = _run_osascript(script, query, str(limit))
    return _split_lines(raw)


def show_note(title: str, folder: str | None = None) -> str:
    script = (
        'tell application "Notes"\n'
        f'  {_note_matches(title, folder)}'
        '  return (name of targetNote as text) & linefeed & linefeed & '
        '(plaintext of targetNote as text)\n'
        'end tell\n'
    )
    raw = _run_osascript(script)
    _raise_resolution_error(raw, title)
    return raw


def update_note(
    title: str,
    *,
    new_title: str | None = None,
    body: str | None = None,
    folder: str | None = None,
) -> str:
    """Update explicitly supplied fields on one exact-title note and verify it."""
    if new_title is None and body is None:
        raise ValueError("at least one update field (--new-title or --body) is required")

    escaped_new_title = _as_escape(new_title) if new_title is not None else None
    escaped_body = _as_escape(body) if body is not None else None
    writes = ""
    if escaped_new_title is not None:
        writes += f'  set name of targetNote to "{escaped_new_title}"\n'
    if escaped_body is not None:
        writes += f'  set body of targetNote to "{escaped_body}"\n'

    # Match uniquely before writing. Verify in Notes.app and then read the
    # same note back by immutable Notes ID. No retry path repeats the write.
    script = (
        'tell application "Notes"\n'
        f'  {_note_matches(title, folder)}'
        f'{writes}'
        '  set finalTitle to name of targetNote as text\n'
        '  set verifiedPlaintext to plaintext of targetNote as text\n'
    )
    if new_title is not None:
        script += f'  if finalTitle is not "{escaped_new_title}" then error "INOTES_UPDATE_VERIFY_FAILED"\n'
    if body is not None:
        script += f'  if verifiedPlaintext is not "{escaped_body}" then error "INOTES_UPDATE_VERIFY_FAILED"\n'
    script += '  return "OK updated: " & finalTitle & (ASCII character 31) & (id of targetNote as text)\nend tell\n'

    result = _run_osascript(script)
    _raise_resolution_error(result, title)
    message, separator, note_id = result.partition(chr(31))
    if separator:
        verify_script = (
            'tell application "Notes"\n'
            f'  set matchingNotes to every note whose id is "{_as_escape(note_id)}"\n'
            '  if (count of matchingNotes) is not 1 then error "INOTES_UPDATE_VERIFY_FAILED"\n'
            '  set targetNote to item 1 of matchingNotes\n'
        )
    else:
        # Compatibility fallback for bridges that cannot return the note ID.
        final_title = new_title if new_title is not None else title
        verify_script = 'tell application "Notes"\n' + f'  {_note_matches(final_title, folder)}'
    verify_script += (
        '  set finalTitle to name of targetNote as text\n'
        '  set verifiedPlaintext to plaintext of targetNote as text\n'
    )
    if new_title is not None:
        verify_script += f'  if finalTitle is not "{escaped_new_title}" then error "INOTES_UPDATE_VERIFY_FAILED"\n'
    if body is not None:
        verify_script += f'  if verifiedPlaintext is not "{escaped_body}" then error "INOTES_UPDATE_VERIFY_FAILED"\n'
    verify_script += '  return "OK verified"\nend tell\n'
    _run_osascript(verify_script)
    return message


def delete_note(title: str, folder: str | None = None) -> str:
    """Delete one uniquely matched note and verify it no longer exists."""
    script = (
        'tell application "Notes"\n'
        f'  {_note_matches(title, folder)}'
        '  set deletedTitle to name of targetNote as text\n'
        '  set deletedId to id of targetNote as text\n'
        '  delete targetNote\n'
        '  set remainingNotes to every note whose id is deletedId\n'
        '  if (count of remainingNotes) is not 0 then error "INOTES_DELETE_VERIFY_FAILED"\n'
        '  return "OK deleted: " & deletedTitle\n'
        'end tell\n'
    )
    result = _run_osascript(script)
    _raise_resolution_error(result, title)
    return result


def _set_note_pin_state(title: str, *, pinned: bool, folder: str | None = None) -> str:
    """Set pin state through Notes.app's File menu and verify the menu state."""
    action = "Pin Note" if pinned else "Unpin Note"
    opposite = "Unpin Note" if pinned else "Pin Note"
    changed = "PINNED" if pinned else "UNPINNED"
    already = "ALREADY_PINNED" if pinned else "ALREADY_UNPINNED"
    script = (
        'tell application "Notes"\n'
        f'  {_note_matches(title, folder)}'
        '  if (name of container of targetNote as text) is "Recently Deleted" then return "INOTES_ERROR_PIN_NOT_SUPPORTED"\n'
        '  set selection of application "Notes" to {targetNote}\n'
        '  activate\n'
        'end tell\n'
        'tell application "System Events"\n'
        '  tell process "Notes"\n'
        '    if not (exists menu bar item "File" of menu bar 1) then return "INOTES_ERROR_PIN_UI_STATE_UNKNOWN"\n'
        '    click menu bar item "File" of menu bar 1\n'
        '    set fileMenu to menu 1 of menu bar item "File" of menu bar 1\n'
        '    set canPin to false\n'
        '    set canUnpin to false\n'
        '    try\n'
        '      set canPin to enabled of menu item "Pin Note" of fileMenu\n'
        '    end try\n'
        '    try\n'
        '      set canUnpin to enabled of menu item "Unpin Note" of fileMenu\n'
        '    end try\n'
    )
    if pinned:
        script += (
            '    if canPin and not canUnpin then\n'
            f'      click menu item "{action}" of fileMenu\n'
            '      click menu bar item "File" of menu bar 1\n'
            '      set verifyMenu to menu 1 of menu bar item "File" of menu bar 1\n'
            '      set verifiedUnpin to false\n'
            '      try\n'
            '        set verifiedUnpin to enabled of menu item "Unpin Note" of verifyMenu\n'
            '      end try\n'
            '      key code 53\n'
            f'      if verifiedUnpin then return "{changed}"\n'
            '      return "INOTES_ERROR_PIN_UI_STATE_UNKNOWN"\n'
            '    else if canUnpin and not canPin then\n'
            '      key code 53\n'
            f'      return "{already}"\n'
            '    end if\n'
        )
    else:
        script += (
            '    if canUnpin and not canPin then\n'
            f'      click menu item "{action}" of fileMenu\n'
            '      click menu bar item "File" of menu bar 1\n'
            '      set verifyMenu to menu 1 of menu bar item "File" of menu bar 1\n'
            '      set verifiedPin to false\n'
            '      try\n'
            '        set verifiedPin to enabled of menu item "Pin Note" of verifyMenu\n'
            '      end try\n'
            '      key code 53\n'
            f'      if verifiedPin then return "{changed}"\n'
            '      return "INOTES_ERROR_PIN_UI_STATE_UNKNOWN"\n'
            '    else if canPin and not canUnpin then\n'
            '      key code 53\n'
            f'      return "{already}"\n'
            '    end if\n'
        )
    script += (
        '    key code 53\n'
        '    return "INOTES_ERROR_PIN_NOT_SUPPORTED"\n'
        '  end tell\n'
        'end tell\n'
    )

    try:
        result = _run_osascript(script)
    except NotesError as exc:
        raise NotesError(
            "Notes pinning uses UI scripting. Allow your terminal to control Notes and System Events "
            "in Privacy & Security > Automation, and enable it under Accessibility. "
            f"Pin state was not confirmed: {exc}"
        ) from exc
    _raise_resolution_error(result, title)
    if result == "INOTES_ERROR_PIN_NOT_SUPPORTED":
        raise NotesError(
            "This note cannot be pinned here. Notes does not support pinning Recently Deleted notes "
            "or notes in unsupported accounts."
        )
    if result == "INOTES_ERROR_PIN_UI_STATE_UNKNOWN":
        raise NotesError(
            "Notes did not expose a verifiable Pin Note/Unpin Note menu state. "
            "Check the selected note, account support, and UI scripting permissions."
        )
    if result not in {changed, already}:
        raise NotesError(f"Unexpected Notes pin result: {result or 'empty response'}")
    return result


def pin_note(title: str, folder: str | None = None) -> str:
    """Pin one uniquely matched note, or report that it is already pinned."""
    return _set_note_pin_state(title, pinned=True, folder=folder)


def unpin_note(title: str, folder: str | None = None) -> str:
    """Unpin one uniquely matched note, or report that it is already unpinned."""
    return _set_note_pin_state(title, pinned=False, folder=folder)


def create_note(title: str, body: str = "", folder: str = "") -> str:
    te = _as_escape(title)
    be = _as_escape(body)
    fe = _as_escape(folder)
    if folder:
        script = f"""\
tell application "Notes"
  tell folder "{fe}"
    make new note with properties {{name:"{te}", body:"{be}"}}
  end tell
end tell
return "OK created: {te}"
"""
    else:
        script = f"""\
tell application "Notes"
  make new note with properties {{name:"{te}", body:"{be}"}}
end tell
return "OK created: {te}"
"""
    return _run_osascript(script)


def _split_lines(raw: str) -> list[str]:
    if not raw:
        return []
    return [line for line in raw.splitlines() if line]
