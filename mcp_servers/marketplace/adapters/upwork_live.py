"""Official Upwork Streamable HTTP adapter. Requires a registered OAuth client."""
import json
import os

from langchain_mcp_adapters.client import MultiServerMCPClient


class UpworkAdapter:
    def __init__(self, token: str):
        self.client = MultiServerMCPClient({"upwork": {"transport": "streamable_http",
            "url": "https://mcp.upwork.com/mcp", "headers": {"Authorization": f"Bearer {token}"}}})
        self.mapping = json.loads(os.getenv("UPWORK_TOOL_MAP", "{}"))

    async def read(self, tool, arguments):
        return await self._call(tool, arguments)

    async def write(self, tool, arguments):
        if tool == "submit_proposal":
            raise ValueError("Confirm the draft directly in Upwork")
        if arguments.get("dry_run"):
            return {"status": "preview", "connects": 0, "payload": arguments["payload"], "stage": None}
        return await self._call(f"{tool}_draft" if tool == "send_message" else tool, arguments["payload"])

    async def _call(self, tool, arguments):
        if tool not in self.mapping:
            raise ValueError(f"An approved Upwork tool mapping is required for {tool}")
        async with self.client.session("upwork") as session:
            result = await session.call_tool(self.mapping[tool], arguments)
        if result.isError:
            raise RuntimeError("Upwork MCP returned an error")
        return result.structuredContent or {"content": [item.model_dump() for item in result.content]}
