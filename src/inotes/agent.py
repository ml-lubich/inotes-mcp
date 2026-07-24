"""Agent-facing schema and playbook for inotes."""

from __future__ import annotations

from inotes import __version__

GUIDE = """\
# inotes — Agent Playbook

Apple Notes CLI. Prefer CLI over MCP to save tokens; use
`apple-notes-mcp` when you need rich CRUD beyond list/search/show/create.

## Core loop

```
inotes doctor
inotes list --limit 20 [--json]
inotes search "QUERY" --limit 20 [--json]
inotes show "Note Title"
inotes create --title "Title" [--body "…"] [--folder "Folder"]
```

`--json` on `list` and `search` emits `{"notes": ["title", …]}`.

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
- `show` requires an exact note title match.
- `create --folder` targets a named folder; omit for the default account.
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
                "description": "Show a note by exact title",
                "params": [
                    {"name": "title", "type": "str", "positional": True, "required": True},
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
            "version": {
                "description": "Print package version",
                "params": [],
            },
        },
    }


def build_guide() -> str:
    return GUIDE
