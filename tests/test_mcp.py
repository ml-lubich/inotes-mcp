from inotes import mcp

def test_mcp_tools():
    assert callable(mcp.doctor)
    assert callable(mcp.list_notes)
    assert callable(mcp.search_notes)
    assert callable(mcp.show_note)
    assert callable(mcp.create_note)

def test_mcp_run_server(monkeypatch):
    called = False
    def mock_run(*args, **kwargs):
        nonlocal called
        called = True
    monkeypatch.setattr(mcp.mcp, "run", mock_run)
    mcp.run_server()
    assert called
