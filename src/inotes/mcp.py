try:
    from mcp.server.fastmcp import FastMCP
except ImportError:
    from mcp.server.mcpserver import MCPServer as FastMCP
from inotes import notes

mcp = FastMCP("inotes")

@mcp.tool()
def doctor() -> list[str]:
    """Verify Notes.app Automation access."""
    return notes.doctor()

@mcp.tool()
def list_notes(limit: int = 20) -> list[str]:
    """List recent note titles."""
    return notes.list_notes(limit=limit)

@mcp.tool()
def search_notes(query: str, limit: int = 20) -> list[str]:
    """Search note titles and bodies."""
    return notes.search_notes(query, limit=limit)

@mcp.tool()
def show_note(title: str, folder: str | None = None) -> str:
    """Show note content by unique exact title, optionally scoped to a folder."""
    if folder is None:
        return notes.show_note(title)
    return notes.show_note(title, folder=folder)


@mcp.tool()
def pin_note(title: str, folder: str | None = None) -> str:
    """Pin one uniquely matched note via Notes UI scripting; safe to repeat."""
    return notes.pin_note(title, folder=folder)


@mcp.tool()
def unpin_note(title: str, folder: str | None = None) -> str:
    """Unpin one uniquely matched note via Notes UI scripting; safe to repeat."""
    return notes.unpin_note(title, folder=folder)


@mcp.tool()
def list_note_links() -> list[dict[str, str]]:
    """Extract external links from all note bodies without returning body text."""
    return notes.list_note_links()


@mcp.tool()
def attach_file_to_note(title: str, file_path: str, folder: str | None = None) -> dict[str, str]:
    """Attach one local file to a uniquely matched note and verify it."""
    return notes.attach_file_to_note(title, file_path, folder=folder)


@mcp.tool()
def list_note_attachments(title: str, folder: str | None = None) -> list[dict[str, str]]:
    """List attachment IDs and names on one note."""
    return notes.list_note_attachments(title, folder=folder)

@mcp.tool()
def create_note(title: str, body: str = "", folder: str = "") -> str:
    """Create a new note in Apple Notes."""
    return notes.create_note(title, body=body, folder=folder)


@mcp.tool()
def edit_note(
    title: str,
    new_title: str | None = None,
    body: str | None = None,
    folder: str | None = None,
) -> str:
    """Edit supplied fields on a uniquely matched note; omitted fields stay unchanged."""
    return notes.update_note(title, new_title=new_title, body=body, folder=folder)


@mcp.tool()
def delete_note(title: str, folder: str | None = None) -> str:
    """Delete one uniquely matched note by exact title."""
    return notes.delete_note(title, folder=folder)

def run_server():
    mcp.run(transport="stdio")
