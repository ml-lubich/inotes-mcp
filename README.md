# inotes — Apple Notes CLI

`inotes` is a fast, scriptable command line for **Apple Notes** — list, search,
show, and create notes from your terminal, with `-j`/`--json` flags for scripts
and agents. Part of the `imsg` / `imail` / `inotes` / `wa` local-first tool
family.

```bash
inotes list --limit 20
inotes search "standup" --json
inotes create --title "Idea" --body "…"
```

---

## macOS only

`inotes` drives **Notes.app** through AppleScript (`osascript`), which only
exists on macOS. There is no Linux or Windows build, and none is planned —
the tool has nothing to talk to without Notes.app.

---

## Install

```bash
# Homebrew
brew install ml-lubich/tap/inotes

# pip
pip install inotes-mcp

# from a clone
git clone https://github.com/ml-lubich/inotes-mcp.git
cd inotes-mcp
uv tool install .
```

> The PyPI/Homebrew package is `inotes-mcp`; the installed command is always
> `inotes`.

## Permissions

`inotes` needs Automation access to Notes.app. The first time it runs a
command, macOS will prompt you to allow it — or grant it up front in
**System Settings → Privacy & Security → Automation** (allow your terminal
app to control Notes). Verify it's working with:

```bash
inotes doctor
```

---

## Quick start

```bash
inotes doctor                                        # verify Notes.app access
inotes list --limit 20                               # recent note titles
inotes list -j                                        # {"notes": [...]}
inotes search "standup" --limit 10 --json             # search titles + bodies
inotes show "My Note"                                 # exact-title lookup
inotes create --title "Idea" --body "…"               # new note
inotes create --title "Work" --body "…" --folder "Projects"
inotes version
inotes -h                                             # help at every level
```

`show` requires an exact note title match. `create --folder` targets a named
folder; omit it to use the default account.

---

## Commands

| Command | Description |
|---|---|
| `doctor` | Verify Notes.app Automation access |
| `list` | List recent note titles (`--limit`, `--json`) |
| `search` | Search note titles and bodies (`--limit`, `--json`) |
| `show` | Show a note by exact title |
| `create` | Create a note (`--title`, `--body`, `--folder`) |
| `version` | Print the installed version |
| `mcp` | Run the built-in MCP server over stdio |
| `agent schema` | Print a JSON command contract (version, tool, params per command) |
| `agent guide` | Print a markdown playbook for LLM agents |

Help is available at every level: `inotes -h`, `inotes <command> -h`,
`inotes agent -h`.

---

## Using inotes from an agent

`inotes` is CLI-first by design — cheaper on tokens than a full MCP round
trip for the common case of list/search/show/create. `inotes agent schema`
gives an agent a machine-readable contract of every command and its
parameters; `inotes agent guide` gives it a short playbook (the same rules
documented above: run `doctor` first, `--json` on `list`/`search`, exit code
0 on success). Root and agent help only render command usage; they do not
contact Notes.app. Notes automation runs only when a Notes command is invoked.

### Built-in MCP server

`inotes mcp` runs a stdio MCP server exposing the same five operations
(`doctor`, `list_notes`, `search_notes`, `show_note`, `create_note`) as MCP
tools — no separate package needed. Point any MCP client at the installed
`inotes` command:

```json
{
  "mcpServers": {
    "inotes": {
      "command": "inotes",
      "args": ["mcp"]
    }
  }
}
```

For richer CRUD than this CLI's surface covers, pair `inotes` with
[sweetrb/apple-notes-mcp](https://github.com/sweetrb/apple-notes-mcp), a full
third-party MCP server for Apple Notes.

---

## Development

```bash
git clone https://github.com/ml-lubich/inotes-mcp.git
cd inotes-mcp
python3 -m pip install -e ".[dev]"
pytest -q
inotes -h
```

A legacy bash implementation is preserved as `inotes.bash.bak` for reference.

---

MIT License · Copyright (c) 2026 Misha Lubich ([ml-lubich](https://github.com/ml-lubich))
