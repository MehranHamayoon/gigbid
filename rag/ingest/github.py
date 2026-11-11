"""Read only explicitly requested, publicly visible files through GitHub MCP."""
import os
from base64 import b64decode
from pathlib import PurePosixPath

import httpx
from langchain_mcp_adapters.client import MultiServerMCPClient

from rag.ingest.loaders import ingest

MAX_BYTES = 200_000
EXTENSIONS = {".md", ".txt", ".py", ".ts", ".tsx", ".js", ".sql", ".json"}


def extract_content(result):
    blocks = (result.structuredContent or {}).get("content")
    if not blocks:
        blocks = [item.model_dump() for item in result.content]
    for block in blocks:
        resource = block.get("resource") or {}
        if isinstance(resource.get("blob"), str):
            return b64decode(resource["blob"], validate=True)
        if isinstance(resource.get("text"), str):
            return resource["text"].encode()
    raise ValueError("GitHub MCP did not return file contents")


async def import_file(tenant, persona, owner, repo, file, skills):
    token = os.getenv("GITHUB_MCP_TOKEN")
    if not token:
        raise ValueError("GitHub MCP import requires a configured read-only token")
    path = PurePosixPath(file)
    if path.is_absolute() or ".." in path.parts or path.suffix.casefold() not in EXTENSIONS:
        raise ValueError("Choose a supported repository README or source file")
    async with httpx.AsyncClient(timeout=8, follow_redirects=False) as client:
        metadata = await client.get(f"https://api.github.com/repos/{owner}/{repo}")
        if not metadata.is_success or metadata.json().get("private", True):
            raise ValueError("Only public GitHub repositories can be imported")
    mcp = MultiServerMCPClient({"github": {"transport": "streamable_http",
          "url": "https://api.githubcopilot.com/mcp/x/repos/readonly",
          "headers": {"Authorization": f"Bearer {token}", "X-MCP-Tools": "get_file_contents"}}})
    async with mcp.session("github") as session:
        result = await session.call_tool("get_file_contents", {"owner": owner, "repo": repo, "path": file})
    if result.isError:
        raise ValueError("GitHub MCP could not read the file")
    data = extract_content(result)
    if len(data) > MAX_BYTES:
        raise ValueError("Choose a GitHub file smaller than 200 KB")
    return ingest(tenant, persona, path.name, data, skills, "readme" if path.suffix == ".md" else "code", "Software")
