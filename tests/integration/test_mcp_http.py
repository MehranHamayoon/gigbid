from fastapi.testclient import TestClient

from mcp_servers.http import serve


def test_compose_service_host_preserves_bearer_and_host_checks(monkeypatch):
    monkeypatch.setenv("GIGBID_INTERNAL_TOKEN", "integration-test")
    init = {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {
        "protocolVersion": "2025-11-25", "capabilities": {},
        "clientInfo": {"name": "compose-check", "version": "1"},
    }}
    headers = {"Accept": "application/json, text/event-stream", "Authorization": "Bearer integration-test"}
    with TestClient(serve("portfolio"), base_url="http://portfolio:8000") as client:
        assert client.post("/mcp", json=init).status_code == 401
        assert client.post("/mcp", json=init, headers={**headers, "Host": "unapproved.invalid"}).status_code == 421
        response = client.post("/mcp", json=init, headers=headers)
        assert response.status_code == 200
        assert response.json()["result"]["serverInfo"]["name"] == "GigBid Portfolio"
