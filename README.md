# inotes — Apple Notes CLI

`inotes` is a Typer command line for **Apple Notes** — list, search, read,
create, edit, delete, pin, unpin, attach local files, and inventory note links.
Part of the `imsg` / `imail` / `inotes` / `wa` local-first tool family.

```bash
inotes list --limit 20
inotes search "standup" --json
inotes show "Project Plan"
inotes create --title "Idea" --body "…"
inotes edit --title "Idea" --body "Revised text"
inotes pin "Project Plan"
inotes unpin "Project Plan"
inotes attach "Project Plan" --file ./demo.wav
inotes attachments "Project Plan" --json
inotes links --output ./inotes-links.md
inotes update
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
inotes edit --title "Idea" --body "Revised text"      # replace body
inotes edit --title "Idea" --new-title "New Idea"    # rename only
inotes edit --title "Shared" --body "Revised" --folder "Work" # disambiguate duplicate title
inotes delete --title "Old Note" --yes                # permanent; explicit confirmation required
inotes pin "Important Note" --folder "Work"         # pin exact title in folder
inotes unpin "Important Note"                       # unpin; safe to repeat
inotes attach "Project Plan" --file ./demo.wav      # attach a local media file
inotes attachments "Project Plan" --json             # inspect file attachments
inotes links --output ./inotes-links.md              # inventory links across notes
inotes update                                           # upgrade the installed CLI
inotes version
inotes -h                                             # help at every level
```

`show`, `edit`, and `delete` require one exact title match. If a title is missing or
ambiguous, `inotes` reports an error instead of choosing a note silently. When
editing, omitted fields stay as they are; `--body` replaces the whole body,
and `--body ""` intentionally clears it. Use `--folder` on `show`, `edit`, or `delete`
to scope an exact-title match when duplicate titles exist; it does not move the
note. A successful edit is read back and verified. `delete` requires `--yes`
and removes only a uniquely matched note. Reads and searches never write to
Notes. `create --folder` targets a named folder; omit it to use the default
account. `inotes update` upgrades a uv-managed installation with
`uv tool upgrade inotes-mcp`; Homebrew/pip installations should use their
package manager's upgrade command.

`pin` and `unpin` use the same exact-title matching and optional `--folder`
disambiguation as `show`. They are idempotent: repeating the requested state
does not toggle it back. AppleScript does not expose a pin property, so these
commands select the note and use Notes.app's **File → Pin Note** menu through
System Events. This requires UI scripting access: allow the terminal to control
Notes and System Events in Automation settings, and enable the terminal under
**System Settings → Privacy & Security → Accessibility**. Pinning is supported
for upgraded iCloud notes and notes stored on the Mac; Recently Deleted notes
cannot be pinned. A missing permission or unavailable menu action is an error,
not a success. See [Apple's pinning guide](https://support.apple.com/en-euro/guide/notes/apdb54e469b6/mac).

`attach` takes one local file per invocation and verifies it appears on the
uniquely matched note. Notes accepts common files and media; support depends on
the account type. Apple documents that Exchange notes cannot attach files. See
[Apple's attachment guide](https://support.apple.com/guide/notes/add-photos-pdfs-and-more-not95edd2813/mac).
Use `attachments` to list attachment names and IDs for one note.

`links` is the only command that scans every note body. It extracts external
hyperlinks and plain HTTP(S) URLs, returning the source note title, link label,
and URL without including note bodies or following links. A report can contain
private URLs; `--output` writes it to a file with owner-only permissions. No
report is created unless that option is supplied.

---

## Commands

| Command | Description |
|---|---|
| `doctor` | Verify Notes.app Automation access |
| `list` | List recent note titles (`--limit`, `--json`) |
| `search` | Search note titles and bodies (`--limit`, `--json`) |
| `show` | Show a note by exact title |
| `create` | Create a note (`--title`, `--body`, `--folder`) |
| `edit` | Edit a uniquely matched note's title/body (`--folder` scopes the source match) |
| `delete` | Permanently delete a uniquely matched note (`--yes` required) |
| `pin` | Pin one uniquely matched note (`--folder` scopes duplicate titles) |
| `unpin` | Unpin one uniquely matched note (`--folder` scopes duplicate titles) |
| `attach` | Attach a local file to one uniquely matched note (`--file`, optional `--folder`) |
| `attachments` | List file attachments on one note (`--json`, optional `--folder`) |
| `links` | Inventory note hyperlinks and plain URLs; optionally write a private report (`--output`) |
| `update` | Upgrade the installed CLI with uv |
| `version` | Print the installed version |
| `mcp` | Run the built-in MCP server over stdio |
| `agent schema` | Print a JSON command contract (version, tool, params per command) |
| `agent guide` | Print a markdown playbook for LLM agents |

Help is available at every level: `inotes -h`, `inotes <command> -h`,
`inotes agent -h`.

---

## Using inotes from an agent

`inotes` is CLI-first by design — cheaper on tokens than a full MCP round
trip for the common case of list/search/show/create/edit/delete/pin/unpin/attach/attachments. `inotes agent schema`
gives an agent a machine-readable contract of every command and its
parameters; `inotes agent guide` gives it a short playbook (the same rules
documented above: run `doctor` first, `--json` on `list`/`search`, exit code
0 on success). Root and agent help only render command usage; they do not
contact Notes.app. Notes automation runs only when a Notes command is invoked.

### Built-in MCP server

`inotes mcp` runs a stdio MCP server exposing the CLI's Notes operations
(`doctor`, `list_notes`, `search_notes`, `show_note`, `create_note`,
`edit_note`, `delete_note`, `pin_note`, `unpin_note`, `attach_file_to_note`,
`list_note_attachments`, `list_note_links`) as MCP
tools — no separate package needed. `inotes agent schema` lists every CLI
command and registered MCP tool. Point any MCP client at the installed
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
