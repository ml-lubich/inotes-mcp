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
inotes update
```

`--json` on `list` and `search` emits `{"notes": ["title", …]}`.
`edit` needs at least one of `--new-title` or `--body`. It
preserves omitted fields; a supplied `--body` replaces the full body, and
`--body ""` clears it. `--folder` scopes the source title match when needed;
it does not move the note.
Successful edits are read back to verify the requested changes. `delete`
requires `--yes` and removes only one uniquely matched title. `update` upgrades
the installed CLI with `uv tool upgrade inotes-mcp`; it never edits notes.

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
- `create --folder` targets a named folder; omit for the default account.
- MCP offers matching `show_note`, `create_note`, `edit_note`, and `delete_note` tools.
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
            "update": {
                "description": "Upgrade the installed inotes CLI using uv",
                "params": [],
                "command": ["uv", "tool", "upgrade", "inotes-mcp"],
            },
            "version": {
                "description": "Print package version",
                "params": [],
            },
        },
        "mcp_tools": {
            "show_note": {"description": "Show a uniquely matched note by exact title", "args": ["title", "folder"]},
            "create_note": {"description": "Create a note explicitly"},
            "edit_note": {
                "description": "Edit a uniquely matched note with the same partial-update semantics as the CLI",
                "args": ["title", "new_title", "body", "folder"],
                "requires_at_least_one_of": ["new_title", "body"],
            },
            "delete_note": {"description": "Delete one uniquely matched note by exact title", "args": ["title", "folder"]},
        },
    }


def build_guide() -> str:
    return GUIDE
