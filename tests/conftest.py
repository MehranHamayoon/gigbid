import pytest


@pytest.fixture(autouse=True)
def isolate_storage(tmp_path, monkeypatch):
    import agent.storage
    import worker.main
    from mcp_servers.marketplace.server import windows

    monkeypatch.setattr(agent.storage, "STATE", tmp_path)
    monkeypatch.setattr(worker.main, "STATE", tmp_path)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("OLLAMA_BASE_URL", raising=False)
    monkeypatch.delenv("GIGSIM_BASE_URL", raising=False)
    monkeypatch.setenv("MARKETPLACE_MODE", "gigsim")
    windows.clear()
