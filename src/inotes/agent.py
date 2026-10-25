"""Agent-facing schema and playbook for inotes."""

from __future__ import annotations

from inotes import __version__

GUIDE = """\
# inotes — Agent Playbook

Apple Notes CLI and stdio MCP server. Prefer CLI for quick, low-overhead
operations; MCP exposes the same read and write capabilities.

## Core loop

```
inotes doctor
inotes list --limit 20 [--json]
inotes search "QUERY" --limit 20 [--json]
inotes show "Note Title" [--folder "Folder"]
inotes create --title "Title" [--body "…"] [--folder "Folder"]
inotes edit --title "Current Title" [--new-title "New Title"] [--body "Replacement body"] [--folder "Folder"]
inotes delete --title "Note Title" [--folder "Folder"] --yes
inotes pin "Note Title" [--folder "Folder"]
inotes unpin "Note Title" [--folder "Folder"]
inotes attach "Note Title" --file "/path/to/audio.wav" [--folder "Folder"]
inotes attachments "Note Title" [--folder "Folder"] [--json]
inotes links [--output PATH] [--json]
inotes update
```

`inotes -h` is the Typer root help and includes the ASCII wordmark. `-h` and
`--help` work on every command.

`--json` on `list` and `search` emits `{"notes": ["title", …]}`.
`edit` needs at least one of `--new-title` or `--body`. It
preserves omitted fields; a supplied `--body` replaces the full body, and
`--body ""` clears it. `--folder` scopes the source title match when needed;
it does not move the note.
Successful edits are read back to verify the requested changes. `delete`
requires `--yes` and removes only one uniquely matched title. `update` upgrades
the installed CLI with `uv tool upgrade inotes-mcp`; it never edits notes.
`pin` and `unpin` are idempotent and use the same exact-title/folder lookup.
They select the note and invoke Notes.app's File > Pin Note menu through
System Events because AppleScript has no pin property. This requires terminal
UI scripting access in Automation and Accessibility settings. Pinning is
available for upgraded iCloud notes and notes stored on the Mac; Recently
Deleted notes cannot be pinned. Missing permission or an unavailable menu
action is an error, not success. The command briefly brings Notes forward and
then restores the app that was frontmost.
`attach` adds one local file at a time and verifies the created attachment;
`attachments` lists attachment names and IDs on one exact-title note. Supported
file types depend on the Notes account; Exchange notes do not support file
attachments. `links` is the only command that scans all note bodies. It returns
external link URLs with the source note title and link text, without including
note bodies or following the URLs. Link reports may contain private URLs; only
write a report with `--output` when needed, and the output file is owner-only.

## Discovery

```
inotes agent schema    # machine-readable command contract
inotes agent guide     # this playbook
inotes -h              # human help
inotes <command> -h    # per-command help
```

## Rules

- Run `inotes doctor` first if Automation permissions may be missing.
- Exit code 0 on success; non-zero on failure with message on stderr.
- `show`, `edit`, and `delete` require one exact note-title match. Missing or duplicate
  titles return an error; use `--folder` to disambiguate; never guess.
- `list`, `search`, and `show` are read-only. `create`, `edit`, and `delete` write only
  when explicitly invoked.
- `update` only upgrades the installed CLI; it does not change notes.
- `pin` and `unpin` are idempotent, exact-title operations. Use `--folder` to
  disambiguate; never guess.
- `attach` and `attachments` require one exact-title match; pass `--folder` to
  disambiguate. Validate local files before attaching; unsupported account/file
  combinations are reported as errors.
- `links` intentionally reads every note body only when explicitly invoked.
  It returns link data, not note bodies, and never opens/follows URLs. Treat
  output files as private.
- Pinning uses Notes UI scripting through System Events and needs Automation
  and Accessibility access. It may fail for unsupported accounts or folders.
- `create --folder` targets a named folder; omit for the default account.
- MCP offers matching `show_note`, `create_note`, `edit_note`, `delete_note`,
  `pin_note`, `unpin_note`, `attach_file_to_note`, and
  `list_note_attachments`, and `list_note_links` tools. `list_note_links`
  scans all note bodies only when explicitly called.
"""


def build_schema() -> dict[str, object]:
    """Return the agent command contract."""
    return {
        "version": __version__,
        "tool": "inotes",
        "commands": {
            "doctor": {
                "description": "Verify Notes.app Automation access",
                "params": [],
            },
            "list": {
                "description": "List recent note titles",
                "params": [
                    {"name": "limit", "flag": "--limit", "type": "int", "default": 20},
                    {"name": "json", "flag": "--json", "type": "bool", "default": False},
                ],
            },
            "search": {
                "description": "Search note titles and bodies",
                "params": [
                    {"name": "query", "type": "str", "positional": True, "required": True},
                    {"name": "limit", "flag": "--limit", "type": "int", "default": 20},
                    {"name": "json", "flag": "--json", "type": "bool", "default": False},
                ],
            },
            "show": {
                "description": "Show a note by unique exact title; missing or ambiguous matches are errors",
                "params": [
                    {"name": "title", "type": "str", "positional": True, "required": True},
                    {"name": "folder", "flag": "--folder", "type": "str", "required": False, "description": "Scope lookup to this folder"},
                ],
            },
            "create": {
                "description": "Create a new note",
                "params": [
                    {"name": "title", "flag": "--title", "type": "str", "required": True},
                    {"name": "body", "flag": "--body", "type": "str", "default": ""},
                    {"name": "folder", "flag": "--folder", "type": "str", "default": ""},
                ],
            },
            "edit": {
                "description": "Edit a uniquely matched note; omitted fields are preserved and requested changes are read back for verification",
                "params": [
                    {"name": "title", "flag": "--title", "type": "str", "required": True, "description": "Current exact note title"},
                    {"name": "new_title", "flag": "--new-title", "type": "str", "required": False, "description": "New title; omitted means unchanged"},
                    {"name": "body", "flag": "--body", "type": "str", "required": False, "description": "Replacement body; omitted means unchanged; empty string clears it"},
                    {"name": "folder", "flag": "--folder", "type": "str", "required": False, "description": "Scope lookup to this source folder"},
                ],
                "requires_at_least_one_of": ["new_title", "body"],
                "match_policy": "Unique exact title only; missing or ambiguous matches fail without writing",
                "success": "Read back the note and verify every requested field before reporting success",
            },
            "delete": {
                "description": "Delete a uniquely matched note after explicit confirmation",
                "params": [
                    {"name": "title", "flag": "--title", "type": "str", "required": True},
                    {"name": "folder", "flag": "--folder", "type": "str", "required": False},
                    {"name": "yes", "flag": "--yes", "type": "bool", "required": True},
                ],
                "match_policy": "Unique exact title only; missing or ambiguous matches fail without writing",
            },
            "pin": {
                "description": "Pin a note by exact title; operation is idempotent and uses Notes UI scripting",
                "params": [
                    {"name": "title", "type": "str", "positional": True, "required": True},
                    {"name": "folder", "flag": "--folder", "type": "str", "required": False},
                ],
                "permission": "Notes Automation and terminal UI scripting access through System Events",
                "supported_notes": "Upgraded iCloud notes and notes stored on this Mac; not Recently Deleted",
                "match_policy": "Unique exact title only; missing or ambiguous matches fail without UI action",
            },
            "unpin": {
                "description": "Unpin a note by exact title; operation is idempotent and uses Notes UI scripting",
                "params": [
                    {"name": "title", "type": "str", "positional": True, "required": True},
                    {"name": "folder", "flag": "--folder", "type": "str", "required": False},
                ],
                "permission": "Notes Automation and terminal UI scripting access through System Events",
                "supported_notes": "Upgraded iCloud notes and notes stored on this Mac",
                "match_policy": "Unique exact title only; missing or ambiguous matches fail without UI action",
            },
            "attach": {
                "description": "Attach one local file to a uniquely matched note and verify it was added",
                "params": [
                    {"name": "title", "type": "str", "positional": True, "required": True},
                    {"name": "file", "flag": "--file", "type": "path", "required": True},
                    {"name": "folder", "flag": "--folder", "type": "str", "required": False},
                ],
                "match_policy": "Unique exact title only; missing or ambiguous matches fail before attachment",
                "account_limit": "Exchange notes do not support file attachments; Notes.app errors surface to the caller",
            },
            "attachments": {
                "description": "List attachment names and IDs on one uniquely matched note",
                "params": [
                    {"name": "title", "type": "str", "positional": True, "required": True},
                    {"name": "folder", "flag": "--folder", "type": "str", "required": False},
                    {"name": "json", "flag": "--json", "type": "bool", "default": False},
                ],
                "match_policy": "Unique exact title only",
            },
            "links": {
                "description": "Scan all Notes bodies for external hyperlinks and plain HTTP(S) URLs",
                "params": [
                    {"name": "output", "flag": "--output", "type": "path", "required": False, "description": "Write a private link report; no file is created when omitted"},
                    {"name": "json", "flag": "--json", "type": "bool", "default": False},
                ],
                "fields": ["note_title", "link_text", "url"],
                "privacy": "Only this explicit command reads all note bodies; output excludes bodies and does not follow URLs",
            },
            "update": {
                "description": "Upgrade the installed inotes CLI using uv",
                "params": [],
                "command": ["uv", "tool", "upgrade", "inotes-mcp"],
            },
            "version": {
                "description": "Print package version",
                "params": [],
            },
            "mcp": {
                "description": "Run the built-in MCP server over stdio",
                "params": [],
            },
        },
        "mcp_tools": {
            "doctor": {"description": "Verify Notes.app Automation access", "args": []},
            "list_notes": {"description": "List recent note titles", "args": ["limit"]},
            "search_notes": {"description": "Search note titles and bodies", "args": ["query", "limit"]},
            "show_note": {"description": "Show a uniquely matched note by exact title", "args": ["title", "folder"]},
            "create_note": {"description": "Create a note explicitly"},
            "edit_note": {
                "description": "Edit a uniquely matched note with the same partial-update semantics as the CLI",
                "args": ["title", "new_title", "body", "folder"],
                "requires_at_least_one_of": ["new_title", "body"],
            },
            "delete_note": {"description": "Delete one uniquely matched note by exact title", "args": ["title", "folder"]},
            "pin_note": {"description": "Pin one uniquely matched note via Notes UI scripting; idempotent", "args": ["title", "folder"]},
            "unpin_note": {"description": "Unpin one uniquely matched note via Notes UI scripting; idempotent", "args": ["title", "folder"]},
            "attach_file_to_note": {"description": "Attach one local file to a uniquely matched note", "args": ["title", "file_path", "folder"]},
            "list_note_attachments": {"description": "List names and IDs of a note's attachments", "args": ["title", "folder"]},
            "list_note_links": {
                "description": "Scan all Notes bodies for external hyperlinks and plain HTTP(S) URLs",
                "args": [],
                "fields": ["note_title", "link_text", "url"],
                "privacy": "Returns links, not note bodies, and never follows URLs",
            },
        },
    }


def build_guide() -> str:
    return GUIDE
