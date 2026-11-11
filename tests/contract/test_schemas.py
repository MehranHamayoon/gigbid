import json
from pathlib import Path

from mcp.shared.memory import create_connected_server_and_client_session

from agent.mcp_client import SERVERS, invoke

SNAPSHOT = Path(__file__).with_name("tool_schemas.json")


async def snapshot():
    result = {}
    for name, server in SERVERS.items():
        async with create_connected_server_and_client_session(server._mcp_server) as session:
            tools = (await session.list_tools()).tools
        result[name] = {tool.name: {"input": tool.inputSchema, "output": tool.outputSchema,
                                  "annotations": tool.annotations.model_dump(exclude_none=True)}
                        for tool in sorted(tools, key=lambda item: item.name)}
    return result


async def test_tool_schemas():
    assert await snapshot() == json.loads(SNAPSHOT.read_text(encoding="utf-8"))


async def test_portfolio_protocol_returns_evidence():
    rows = await invoke("fit_matcher", "portfolio", "search_evidence", requirement="classification with scikit-learn",
                        k=5, filters={"persona": "ai"})
    assert "ai-1-case" in {row["id"] for row in rows}


async def test_role_allowlist_denies_external_write():
    import pytest

    with pytest.raises(PermissionError):
        await invoke("scout", "marketplace", "submit_proposal")


if __name__ == "__main__":
    import asyncio

    SNAPSHOT.write_text(json.dumps(asyncio.run(snapshot()), indent=2, sort_keys=True) + "\n", encoding="utf-8")
