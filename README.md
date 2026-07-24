# inotes — Apple Notes CLI (+ MCP)

**imsg-style** local Notes tool. Name family: `imsg` · `imail` · `inotes` · `wa`.

| Surface | Binary | When |
|---------|--------|------|
| **CLI (prefer)** | `inotes` | list/search/show/create — saves tokens |
| **MCP** | `apple-notes-mcp` | rich CRUD in agents |

## Install

**pip (editable dev):**

```bash
git clone https://github.com/ml-lubich/inotes.git
cd inotes
python3 -m pip install -e ".[dev]"
```

**Homebrew (when published):**

```bash
brew install ml-lubich/tap/inotes
```

Requires macOS with Notes.app. Grant **Automation → Notes** when prompted.

## Usage

```bash
inotes doctor
inotes list --limit 20
inotes list --json
inotes search "standup" --limit 10 --json
inotes show "My Note"
inotes create --title "Idea" --body "…"
inotes create --title "Work" --body "…" --folder "Projects"
inotes version
inotes -h
```

## Agents

CLI-first — use MCP only when you need operations beyond this surface.

```bash
inotes agent schema   # JSON command contract (version, tool, params)
inotes agent guide    # markdown playbook
```

Pair with [sweetrb/apple-notes-mcp](https://github.com/sweetrb/apple-notes-mcp) for full MCP tooling.

## Development

```bash
python3 -m pip install -e ".[dev]"
pytest -q
inotes -h
```

Legacy bash implementation preserved as `inotes.bash.bak`.
