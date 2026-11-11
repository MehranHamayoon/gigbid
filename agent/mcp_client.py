import asyncio
import json
import os
import time

from langchain_mcp_adapters.client import MultiServerMCPClient
from mcp.shared.memory import create_connected_server_and_client_session

from mcp_servers.marketplace import server as marketplace
from mcp_servers.portfolio import server as portfolio
from mcp_servers.workspace import server as workspace

SERVERS = {"marketplace": marketplace.mcp, "portfolio": portfolio.mcp, "workspace": workspace.mcp}
TOOLS = {
    "scout": {"search_jobs", "get_job"},
    "risk_assessor": {"get_client_history"},
    "fit_matcher": {"search_evidence"},
    "pricing": {"get_client_history", "get_connects_balance"},
    "writer": {"get_case_study"},
    "approvals": {"create_proposal_draft", "submit_proposal", "send_message"},
    "client_liaison": {"list_messages", "free_calendar_slots"},
    "dashboard": {"search_jobs", "get_job", "get_connects_balance", "list_messages", "list_pipeline"},
}


class ToolUnavailable(RuntimeError):
    pass


async def invoke(role, server, name, **arguments):
    if name not in TOOLS[role]:
        raise PermissionError(f"{role} cannot call {name}")
    url = os.getenv(f"GIGBID_{server.upper()}_MCP_URL")
    for attempt in range(3):
        try:
            async with asyncio.timeout(12):
                if url:
                    client = MultiServerMCPClient({server: {"transport": "streamable_http", "url": url,
                        "headers": {"Authorization": f"Bearer {os.environ['GIGBID_INTERNAL_TOKEN']}"}}})
                    async with client.session(server) as session:
                        result = await session.call_tool(name, arguments)
                else:
                    async with create_connected_server_and_client_session(SERVERS[server]._mcp_server) as session:
                        result = await session.call_tool(name, arguments)
            if result.isError:
                details = " ".join(getattr(item, "text", "") for item in result.content)
                if "unavailable" in details.lower() or "rate limit" in details.lower() or "Server error" in details:
                    raise ToolUnavailable(details)
                raise ValueError(details)
            content = result.structuredContent
            if content is not None:
                return content["result"] if list(content) == ["result"] else content
            data = [json.loads(item.text) for item in result.content]
            return data[0] if len(data) == 1 else data
        except (ToolUnavailable, TimeoutError, OSError, ExceptionGroup) as exc:
            if attempt == 2:
                raise ToolUnavailable(f"{server.capitalize()} unavailable") from exc
            await asyncio.sleep(0.2 * (2 ** attempt))
