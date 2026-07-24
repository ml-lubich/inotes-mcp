"""Apple Notes operations via osascript."""

from __future__ import annotations

import subprocess


class NotesError(Exception):
    """Notes.app interaction failed."""


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


def show_note(title: str) -> str:
    escaped = _as_escape(title)
    script = f"""\
tell application "Notes"
  set noteRef to first note whose name is "{escaped}"
  return (name of noteRef) & linefeed & linefeed & (plaintext of noteRef)
end tell
"""
    return _run_osascript(script)


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
