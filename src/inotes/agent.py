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
inotes update --title "Current Title" [--new-title "New Title"] [--body "Replacement body"] [--folder "Folder"]
```

`--json` on `list` and `search` emits `{"notes": ["title", …]}`.
`update` needs at least one of `--new-title` or `--body`. It
preserves omitted fields; a supplied `--body` replaces the full body, and
`--body ""` clears it. `--folder` scopes the source title match when needed;
it does not move the note.
Successful updates are read back to verify the requested changes.

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
- `show` and `update` require one exact note-title match. Missing or duplicate
  titles return an error; use `--folder` to disambiguate; never guess.
- `list`, `search`, and `show` are read-only. `create` and `update` write only
  when explicitly invoked.
- `create --folder` targets a named folder; omit for the default account.
- MCP offers matching `show_note`, `create_note`, and `update_note` tools.
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
            "update": {
                "description": "Update a uniquely matched note; omitted fields are preserved and requested changes are read back for verification",
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
            "version": {
                "description": "Print package version",
                "params": [],
            },
        },
        "mcp_tools": {
            "show_note": {"description": "Show a uniquely matched note by exact title", "args": ["title", "folder"]},
            "create_note": {"description": "Create a note explicitly"},
            "update_note": {
                "description": "Update a uniquely matched note with the same partial-update semantics as the CLI",
                "args": ["title", "new_title", "body", "folder"],
                "requires_at_least_one_of": ["new_title", "body"],
            },
        },
    }


def build_guide() -> str:
    return GUIDE
