"""Apple Notes operations via osascript."""

from __future__ import annotations

import gzip
import html
from html.parser import HTMLParser
from pathlib import Path
import re
from urllib.parse import urlsplit
import sqlite3
import subprocess


class NotesError(Exception):
    """Notes.app interaction failed."""


class NoteNotFoundError(NotesError):
    """No note matched the exact title and optional folder."""


class AmbiguousNoteTitleError(NotesError):
    """More than one note matched the exact title and optional folder."""


_PLAIN_URL = re.compile(r"https?://[^\s<>\"'`]+", re.IGNORECASE)
_TRAILING_URL_PUNCTUATION = ".,;:!?)]}"
_LINK_SCHEMES = {"http", "https", "mailto", "tel"}
_OSASCRIPT_TIMEOUT_SECONDS = 180
_NOTE_STORE_PATH = Path.home() / "Library/Group Containers/group.com.apple.notes/NoteStore.sqlite"


class _NoteLinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.links: list[tuple[str, str]] = []
        self._anchor: tuple[str, list[str]] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() == "a" and self._anchor is None:
            href = dict(attrs).get("href") or ""
            self._anchor = (href, [])

    def handle_data(self, data: str) -> None:
        if self._anchor is not None:
            self._anchor[1].append(data)
        else:
            for match in _PLAIN_URL.finditer(data):
                url = match.group(0).rstrip(_TRAILING_URL_PUNCTUATION)
                self.links.append((url, url))

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "a" and self._anchor is not None:
            href, label_parts = self._anchor
            label = " ".join("".join(label_parts).split()) or href
            self.links.append((href, label))
            self._anchor = None


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
            timeout=_OSASCRIPT_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired as exc:
        raise NotesError(
            f"Notes automation timed out after {_OSASCRIPT_TIMEOUT_SECONDS} seconds."
        ) from exc
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
set sourceFolderIDs to {{}}
repeat with folderRef in sourceFolders
  set end of sourceFolderIDs to id of contents of folderRef as text
end repeat
set scopedNotes to {{}}
repeat with candidateNote in matchingNotes
  set candidateFolder to container of candidateNote
  set candidateFolderID to id of candidateFolder as text
  if sourceFolderIDs contains candidateFolderID then
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
    set candidateFolder to container of candidateNote
    set candidateFolder to name of candidateFolder as text
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


def extract_links_from_html(body_html: str, note_title: str) -> list[dict[str, str]]:
    """Extract external links from one note body without returning its text."""
    parser = _NoteLinkParser()
    parser.feed(body_html)
    parser.close()

    rows: list[dict[str, str]] = []
    seen_urls: set[str] = set()

    def add(url: str, label: str) -> None:
        cleaned_url = url.strip()
        parsed = urlsplit(cleaned_url)
        if parsed.scheme.lower() not in _LINK_SCHEMES:
            return
        if parsed.scheme.lower() in {"http", "https"} and not parsed.netloc:
            return
        if cleaned_url in seen_urls:
            return
        seen_urls.add(cleaned_url)
        rows.append({"note_title": note_title, "label": label.strip() or cleaned_url, "url": cleaned_url})

    for href, label in parser.links:
        add(href, label)
    return rows


def _read_varint(data: bytes, position: int) -> tuple[int, int] | None:
    value = 0
    shift = 0
    while position < len(data) and shift <= 63:
        byte = data[position]
        position += 1
        value |= (byte & 0x7F) << shift
        if byte < 0x80:
            return value, position
        shift += 7
    return None


def _parse_note_message(data: bytes, *, depth: int = 0) -> dict[int, list[object]] | None:
    """Decode Notes' gzip-compressed protobuf envelope without importing a schema."""
    if depth > 16:
        return None
    message: dict[int, list[object]] = {}
    position = 0
    fields_seen = 0
    while position < len(data) and fields_seen < 100_000:
        decoded_key = _read_varint(data, position)
        if decoded_key is None:
            return None
        key, position = decoded_key
        field_number, wire_type = key >> 3, key & 7
        if field_number == 0:
            return None
        fields_seen += 1
        value: object
        if wire_type == 0:
            decoded_value = _read_varint(data, position)
            if decoded_value is None:
                return None
            value, position = decoded_value
        elif wire_type in (1, 5):
            size = 8 if wire_type == 1 else 4
            if position + size > len(data):
                return None
            value = data[position : position + size]
            position += size
        elif wire_type == 2:
            decoded_size = _read_varint(data, position)
            if decoded_size is None:
                return None
            size, position = decoded_size
            if position + size > len(data):
                return None
            payload = data[position : position + size]
            position += size
            try:
                text_value = payload.decode("utf-8")
            except UnicodeDecodeError:
                text_value = ""
            is_readable_text = all(
                character.isprintable() or character in "\r\n\t" for character in text_value
            ) and _parse_note_message(payload, depth=depth + 1) is None
            if is_readable_text:
                value = text_value
            else:
                nested = _parse_note_message(payload, depth=depth + 1)
                if nested is None:
                    continue
                value = nested
        else:
            return None
        message.setdefault(field_number, []).append(value)
    if position != len(data):
        return None
    return message


def _iter_note_strings(message: dict[int, list[object]]):
    for field_number, values in message.items():
        for value in values:
            if isinstance(value, str):
                yield field_number, value
            elif isinstance(value, dict):
                yield from _iter_note_strings(value)


def _iter_note_messages(message: dict[int, list[object]]):
    yield message
    for values in message.values():
        for value in values:
            if isinstance(value, dict):
                yield from _iter_note_messages(value)


def _is_supported_link(url: str) -> bool:
    parsed = urlsplit(url.strip())
    return parsed.scheme.lower() in _LINK_SCHEMES and (
        parsed.scheme.lower() not in {"http", "https"} or bool(parsed.netloc)
    )


def _links_from_note_store_blob(
    blob: bytes | None,
    note_title: str,
    note_id: int,
    links: list[dict[str, str]],
    seen: set[tuple[int, str]],
) -> None:
    if not blob:
        return
    try:
        decoded = gzip.decompress(blob)
    except (OSError, EOFError) as exc:
        raise NotesError("Notes returned an unreadable compressed note record; no partial inventory was written.") from exc
    message = _parse_note_message(decoded)
    if message is None:
        raise NotesError("Notes returned an unsupported note data format; no partial inventory was written.")

    def add(url: str, label: str) -> None:
        cleaned = url.strip().rstrip(_TRAILING_URL_PUNCTUATION)
        if not _is_supported_link(cleaned):
            return
        key = (note_id, cleaned)
        if key not in seen:
            seen.add(key)
            links.append({"note_title": note_title, "label": label.strip() or cleaned, "url": cleaned})

    # Links in Notes' rich-text protobuf are stored on a text run's field-5
    # attributes; field 9 carries the target URL and field 2 carries its label.
    for run in _iter_note_messages(message):
        labels = [value for value in run.get(2, []) if isinstance(value, str) and value.strip()]
        attributes = [value for value in run.get(5, []) if isinstance(value, dict)]
        for attribute in attributes:
            for _, value in _iter_note_strings(attribute):
                if _is_supported_link(value):
                    add(value, labels[0] if labels else value)

    # Plain URLs are text in the note body and have no rich-text URL attribute.
    for _, text_value in _iter_note_strings(message):
        for match in _PLAIN_URL.finditer(text_value):
            url = match.group(0).rstrip(_TRAILING_URL_PUNCTUATION)
            add(url, url)


def _list_note_links_from_store(path: Path) -> list[dict[str, str]]:
    """Fast read-only path for the local Notes store; fallback handles other layouts."""
    uri = path.resolve().as_uri() + "?mode=ro"
    try:
        db = sqlite3.connect(uri, uri=True, timeout=5)
    except sqlite3.Error as exc:
        raise _NoteStoreUnsupported from exc
    try:
        tables = {row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if not {"ZICCLOUDSYNCINGOBJECT", "ZICNOTEDATA"}.issubset(tables):
            raise _NoteStoreUnsupported
        note_columns = {row[1] for row in db.execute("PRAGMA table_info(ZICCLOUDSYNCINGOBJECT)")}
        data_columns = {row[1] for row in db.execute("PRAGMA table_info(ZICNOTEDATA)")}
        if not {"Z_PK", "ZTITLE1"}.issubset(note_columns) or not {"ZNOTE", "ZDATA"}.issubset(data_columns):
            raise _NoteStoreUnsupported
        query = '''\
SELECT note.Z_PK, note.ZTITLE1, data.ZDATA
FROM ZICCLOUDSYNCINGOBJECT AS note
LEFT JOIN ZICNOTEDATA AS data ON data.ZNOTE = note.Z_PK
WHERE note.ZTITLE1 IS NOT NULL AND data.ZNOTE IS NOT NULL
ORDER BY note.Z_PK
'''
        links: list[dict[str, str]] = []
        seen: set[tuple[int, str]] = set()
        for note_id, note_title, body_blob in db.execute(query):
            _links_from_note_store_blob(body_blob, str(note_title), int(note_id), links, seen)
        return links
    except sqlite3.Error as exc:
        raise _NoteStoreUnsupported from exc
    finally:
        db.close()


class _NoteStoreUnsupported(Exception):
    """Private on-disk Notes schema is unavailable; use the AppleScript fallback."""


def list_note_links() -> list[dict[str, str]]:
    """Scan all Notes HTML bodies once and return only external link records."""
    if _NOTE_STORE_PATH.is_file():
        try:
            return _list_note_links_from_store(_NOTE_STORE_PATH)
        except _NoteStoreUnsupported:
            pass
    script = '''\
tell application "Notes"
  set recordSeparator to ASCII character 30
  set fieldSeparator to ASCII character 31
  set outputText to ""
  set skippedCount to 0
  set allNotes to every note
  repeat with noteRef in allNotes
    try
      set noteProps to properties of noteRef
      set noteTitle to name of noteProps as text
      set noteID to id of noteProps as text
      set noteBody to body of noteProps as text
      if outputText is not "" then set outputText to outputText & recordSeparator
      set outputText to outputText & noteTitle & fieldSeparator & noteID & fieldSeparator & noteBody
    on error
      set skippedCount to skippedCount + 1
    end try
  end repeat
  if outputText is not "" then set outputText to outputText & recordSeparator
  return outputText & "INOTES_META" & fieldSeparator & (skippedCount as text)
end tell
'''
    raw = _run_osascript(script)
    links: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    records = raw.split(chr(30))
    metadata_prefix = "INOTES_META" + chr(31)
    if records and records[-1].startswith(metadata_prefix):
        try:
            skipped_count = int(records.pop().partition(metadata_prefix)[2])
        except ValueError as exc:
            raise NotesError("Notes returned malformed link scan metadata.") from exc
        if skipped_count:
            suffix = "note" if skipped_count == 1 else "notes"
            raise NotesError(
                f"Could not read link data from {skipped_count} {suffix}; no partial inventory was written."
            )
    for record in records:
        if not record:
            continue
        fields = record.split(chr(31), 2)
        if len(fields) != 3:
            raise NotesError("Notes returned malformed data while scanning links.")
        note_title, note_id, body_html = fields
        for link in extract_links_from_html(body_html, note_title):
            key = (note_id, link["url"])
            if key not in seen:
                seen.add(key)
                links.append(link)
    return links


def attach_file_to_note(
    title: str,
    file_path: str | Path,
    folder: str | None = None,
) -> dict[str, str]:
    """Attach one local file to a uniquely matched note and verify it."""
    path = Path(file_path).expanduser()
    if not path.is_file():
        raise ValueError(f"Attachment path must be an existing regular file: {path}")
    resolved_path = str(path.resolve())
    script = f'''on run argv
tell application "Notes"
  {_note_matches(title, folder)}  set fileAlias to POSIX file (item 1 of argv) as alias
  set newAttachment to make new attachment at end of attachments of targetNote with data fileAlias
  set attachmentID to id of newAttachment as text
  set attachmentName to name of newAttachment as text
  set verified to false
  repeat with attachmentRef in attachments of targetNote
    if (id of attachmentRef as text) is attachmentID then set verified to true
  end repeat
  if not verified then return "INOTES_ERROR_ATTACHMENT_VERIFY_FAILED"
  return "OK_ATTACHMENT" & (ASCII character 31) & attachmentID & (ASCII character 31) & attachmentName & (ASCII character 31) & (name of targetNote as text)
end tell
end run
'''
    raw = _run_osascript(script, resolved_path)
    _raise_resolution_error(raw, title)
    if raw == "INOTES_ERROR_ATTACHMENT_VERIFY_FAILED":
        raise NotesError(f"Could not verify attachment on note {title!r}.")
    fields = raw.split(chr(31), 3)
    if len(fields) != 4 or fields[0] != "OK_ATTACHMENT":
        raise NotesError(f"Unexpected Notes attachment result for {title!r}.")
    return {"id": fields[1], "name": fields[2], "title": fields[3]}


def list_note_attachments(title: str, folder: str | None = None) -> list[dict[str, str]]:
    """List attachment IDs and names on one uniquely matched note."""
    script = (
        'tell application "Notes"\n'
        f'  {_note_matches(title, folder)}'
        '  set recordSeparator to ASCII character 30\n'
        '  set fieldSeparator to ASCII character 31\n'
        '  set outputText to ""\n'
        '  repeat with attachmentRef in attachments of targetNote\n'
        '    if outputText is not "" then set outputText to outputText & recordSeparator\n'
        '    set outputText to outputText & (id of attachmentRef as text) & fieldSeparator & (name of attachmentRef as text)\n'
        '  end repeat\n'
        '  return outputText\n'
        'end tell\n'
    )
    raw = _run_osascript(script)
    _raise_resolution_error(raw, title)
    rows: list[dict[str, str]] = []
    for record in raw.split(chr(30)):
        if not record:
            continue
        fields = record.split(chr(31), 1)
        if len(fields) != 2:
            raise NotesError(f"Notes returned malformed attachment data for {title!r}.")
        rows.append({"id": fields[0], "name": fields[1]})
    return rows


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
    if escaped_body is not None:
        writes += f'  set body of targetNote to "{escaped_body}"\n'
    if escaped_new_title is not None:
        writes += f'  set name of targetNote to "{escaped_new_title}"\n'

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
    changed = "PINNED" if pinned else "UNPINNED"
    already = "ALREADY_PINNED" if pinned else "ALREADY_UNPINNED"
    script = (
        'tell application "System Events"\n'
        '  set previousFrontmost to name of first application process whose frontmost is true\n'
        'end tell\n'
        'tell application "Notes"\n'
        f'  {_note_matches(title, folder)}'
        '  set selection of application "Notes" to {targetNote}\n'
        '  show targetNote\n'
        'end tell\n'
        'tell application "System Events"\n'
        '  set notesProcess to process "Notes"\n'
        '  set frontmost of notesProcess to true\n'
        '  delay 0.3\n'
        '  set pinResult to "INOTES_ERROR_PIN_UI_STATE_UNKNOWN"\n'
        '  set fileMenuOpened to false\n'
        '  try\n'
        '    tell notesProcess\n'
        '      if frontmost then\n'
        '      if exists menu bar item "File" of menu bar 1 then\n'
        '        click menu bar item "File" of menu bar 1\n'
        '        set fileMenu to menu 1 of menu bar item "File" of menu bar 1\n'
        '        set fileMenuOpened to true\n'
        '        set canPin to false\n'
        '        set canUnpin to false\n'
        '        try\n'
        '          set canPin to enabled of menu item "Pin Note" of fileMenu\n'
        '        end try\n'
        '        try\n'
        '          set canUnpin to enabled of menu item "Unpin Note" of fileMenu\n'
        '        end try\n'
    )
    if pinned:
        script += (
            '        if canPin and not canUnpin then\n'
            f'          click menu item "{action}" of fileMenu\n'
            '          delay 0.2\n'
            '          click menu bar item "File" of menu bar 1\n'
            '          set verifyMenu to menu 1 of menu bar item "File" of menu bar 1\n'
            '          set verifiedUnpin to false\n'
            '          try\n'
            '            set verifiedUnpin to enabled of menu item "Unpin Note" of verifyMenu\n'
            '          end try\n'
            f'          if verifiedUnpin then set pinResult to "{changed}"\n'
            '        else if canUnpin and not canPin then\n'
            f'          set pinResult to "{already}"\n'
            '        else\n'
            '          set pinResult to "INOTES_ERROR_PIN_NOT_SUPPORTED"\n'
            '        end if\n'
        )
    else:
        script += (
            '        if canUnpin and not canPin then\n'
            f'          click menu item "{action}" of fileMenu\n'
            '          delay 0.2\n'
            '          click menu bar item "File" of menu bar 1\n'
            '          set verifyMenu to menu 1 of menu bar item "File" of menu bar 1\n'
            '          set verifiedPin to false\n'
            '          try\n'
            '            set verifiedPin to enabled of menu item "Pin Note" of verifyMenu\n'
            '          end try\n'
            f'          if verifiedPin then set pinResult to "{changed}"\n'
            '        else if canPin and not canUnpin then\n'
            f'          set pinResult to "{already}"\n'
            '        else\n'
            '          set pinResult to "INOTES_ERROR_PIN_NOT_SUPPORTED"\n'
            '        end if\n'
        )
    script += (
        '      else\n'
        '        set pinResult to "INOTES_ERROR_PIN_UI_STATE_UNKNOWN"\n'
        '      end if\n'
        '      else\n'
        '        set pinResult to "INOTES_ERROR_PIN_UI_STATE_UNKNOWN"\n'
        '      end if\n'
        '    end tell\n'
        '  on error errorMessage number errorNumber\n'
        '    set pinResult to "INOTES_ERROR_PIN_UI:" & errorMessage\n'
        '  end try\n'
        '  if fileMenuOpened and frontmost of notesProcess then\n'
        '    try\n'
        '      key code 53\n'
        '    end try\n'
        '  end if\n'
        '  if previousFrontmost is not "Notes" then\n'
        '    try\n'
        '      set frontmost of process previousFrontmost to true\n'
        '    end try\n'
        '  end if\n'
        '  return pinResult\n'
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
    if result.startswith("INOTES_ERROR_PIN_UI:"):
        detail = result.partition(":")[2].strip()
        raise NotesError(
            "Notes pinning uses UI scripting. Allow your terminal to control Notes and System Events "
            "in Privacy & Security > Automation, and enable it under Accessibility. "
            f"Pin state was not confirmed: {detail}"
        )
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
