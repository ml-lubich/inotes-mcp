---
name: inotes
description: Query and create Apple Notes from the CLI or via MCP. Use when a task needs to list, search, read, or create notes in Notes.app — triggers like "check my notes", "find the note about X", "what's in Apple Notes", "create a note", "add this to Notes". macOS only (drives Notes.app via AppleScript). Read-only by default: never send, delete, or modify a note unless the user explicitly asks.
---

# inotes

Fast, scriptable CLI for Apple Notes — list, search, show, create. Talks to
Notes.app over AppleScript (`osascript`); macOS only.

## Install

```bash
# from an existing local clone
uv tool install -e ~/dev/inotes-mcp

# fresh clone
git clone https://github.com/ml-lubich/inotes-mcp && uv tool install -e ./inotes-mcp
```

Installs the `inotes` command (entry point: `inotes.cli:app`).

## CLI commands

```
inotes doctor                                # verify Notes.app Automation access
inotes list --limit 20 [--json]              # recent note titles
inotes search "standup" --limit 10 [--json]  # search titles + bodies
inotes show "My Note"                        # exact-title lookup, prints body
inotes create --title "Idea" --body "…" [--folder "Projects"]
inotes version                               # print installed version
inotes agent schema                          # JSON command contract for agents
inotes agent guide                           # markdown playbook for agents
inotes -h / inotes <command> -h              # help at every level
```

`show` requires an exact title match. `create --folder` targets a named
folder; omit it to use the default account.

## MCP server

Built into the same binary — no separate package. Launch over stdio:

```bash
inotes mcp
```

Claude Code:

```bash
claude mcp add inotes -- inotes mcp
```

Exposes 5 tools: `doctor`, `list_notes`, `search_notes`, `show_note`, `create_note`
(same behavior as the CLI commands above).

## macOS permissions

Requires **Automation** access from your terminal/agent app to **Notes**
(System Settings → Privacy & Security → Automation). macOS prompts on first
use; verify with:

```bash
inotes doctor
```

Harmless trigger for the permission popup (read-only, doesn't touch a note):

```bash
osascript -e 'tell application "Notes" to get name'
```

## Safety rules

- Read-only by default: `doctor`, `list`, `search`, `show` never modify data.
- `create` is the only mutating command — only run it when the user explicitly
  asks to create/add a note. Never delete or edit existing notes (this tool
  has no delete/edit command).
- Never run `create` in a test, demo, or exploratory context against the
  user's real Notes — that would create a real note.
