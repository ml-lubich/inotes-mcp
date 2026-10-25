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
def create_note(title: str, body: str = "", folder: str = "") -> str:
    """Create a new note in Apple Notes."""
    return notes.create_note(title, body=body, folder=folder)


@mcp.tool()
def update_note(
    title: str,
    new_title: str | None = None,
    body: str | None = None,
    folder: str | None = None,
) -> str:
    """Update supplied fields on a uniquely matched note; omitted fields stay unchanged."""
    return notes.update_note(title, new_title=new_title, body=body, folder=folder)

def run_server():
    mcp.run(transport="stdio")
