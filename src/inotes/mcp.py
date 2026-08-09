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
def show_note(title: str) -> str:
    """Show note content by exact title."""
    return notes.show_note(title)

@mcp.tool()
def create_note(title: str, body: str = "", folder: str = "") -> str:
    """Create a new note in Apple Notes."""
    return notes.create_note(title, body=body, folder=folder)

def run_server():
    mcp.run(transport="stdio")
