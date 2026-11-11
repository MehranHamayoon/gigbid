import hmac
import os
import time
from collections import defaultdict, deque
from hashlib import sha256
from typing import Annotated

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations
from pydantic import BaseModel, Field

from agent.settings import settings
from agent.storage import encode
from apps.api.auth.oauth_store import load
from gigsim.service import audit
from mcp_servers.marketplace.adapters.gigsim import GigSimAdapter
from mcp_servers.marketplace.adapters.upwork_live import UpworkAdapter

mcp = FastMCP("GigBid Marketplace", stateless_http=True, json_response=True)
READ = ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=True)
DRAFT = ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=True)
WRITE = ToolAnnotations(readOnlyHint=False, destructiveHint=True, idempotentHint=True)
windows = defaultdict(deque)


class DraftPayload(BaseModel):
    job_id: str = Field(min_length=1, max_length=100)
    text: str = Field(min_length=12, max_length=5000)
    amount: int = Field(default=0, ge=0, le=100_000)


class WriteResult(BaseModel):
    status: str
    connects: int
    payload: dict
    stage: str | None = None


def signature(tool, user_id, key, payload):
    secret = os.getenv("APP_SECRET_KEY", "gigbid-local-internal-only")
    return hmac.new(secret.encode(), encode([tool, user_id, key, payload]).encode(), sha256).hexdigest()


def mode():
    return os.getenv("MARKETPLACE_MODE", settings()["marketplace"]["mode"])


def adapter(user_id):
    if mode() == "upwork":
        token = load(user_id)
        if not token:
            raise ValueError("Connect Upwork with OAuth in Settings")
        return UpworkAdapter(token)
    return GigSimAdapter()


def rate_limit(user_id):
    now = time.monotonic()
    window = windows[user_id]
    while window and now - window[0] >= 60:
        window.popleft()
    if len(window) >= settings()["marketplace"]["max_requests_per_minute"]:
        raise RuntimeError("Marketplace rate limit reached")
    window.append(now)


async def read(tool, user_id, trace_id, **arguments):
    if os.getenv("GIGBID_MARKETPLACE_DISABLED") == "1":
        raise RuntimeError("Marketplace unavailable")
    if tool in {"search_jobs", "get_job"}:
        rate_limit(user_id)
    result = await adapter(user_id).read(tool, {"user_id": user_id, **arguments})
    audit(user_id, trace_id, tool, arguments, result)
    return result


async def write(tool, payload, user_id, trace_id, idempotency_key, dry_run, approval, weekly_limit):
    if os.getenv("GIGBID_MARKETPLACE_DISABLED") == "1":
        raise RuntimeError("Marketplace unavailable")
    data = payload.model_dump()
    if not dry_run and not hmac.compare_digest(approval, signature(tool, user_id, idempotency_key, data)):
        raise ValueError("The graph must authorize the exact marketplace write")
    return WriteResult.model_validate(await adapter(user_id).write(tool, {
        "user": user_id, "trace_id": trace_id, "key": idempotency_key, "payload": data,
        "dry_run": dry_run, "weekly_limit": weekly_limit,
    }))


@mcp.tool(annotations=READ)
async def search_jobs(user_id: str, trace_id: str, query: str = "", category: str = "") -> list[dict]:
    """Find jobs by title, description or skills and optionally filter by category."""
    return await read("search_jobs", user_id, trace_id, query=query, category=category)


@mcp.tool(annotations=READ)
async def get_job(job_id: str, user_id: str, trace_id: str) -> dict:
    """Read one job by marketplace job ID."""
    return await read("get_job", user_id, trace_id, job_id=job_id)


@mcp.tool(annotations=READ)
async def get_client_history(client_id: str, user_id: str, trace_id: str) -> dict:
    """Read a client's payment verification, public rating, and historical spend."""
    return await read("get_client_history", user_id, trace_id, client_id=client_id)


@mcp.tool(annotations=READ)
async def get_connects_balance(user_id: str, trace_id: str) -> dict:
    """Read available Connects and the amount spent over the past week."""
    return await read("get_connects_balance", user_id, trace_id)


@mcp.tool(annotations=READ)
async def list_messages(user_id: str, trace_id: str, job_id: str = "") -> list[dict]:
    """Read the user's marketplace messages, optionally for one job."""
    return await read("list_messages", user_id, trace_id, job_id=job_id)


@mcp.tool(annotations=READ)
async def list_pipeline(user_id: str, trace_id: str) -> list[dict]:
    """Read current proposal stages and approved Connects spending."""
    return await read("list_pipeline", user_id, trace_id)


Key = Annotated[str, Field(min_length=12, max_length=160)]
Limit = Annotated[int, Field(ge=0, le=100)]


@mcp.tool(annotations=DRAFT)
async def create_proposal_draft(payload: DraftPayload, user_id: str, trace_id: str, idempotency_key: Key,
                                dry_run: bool = True, approval: str = "", weekly_limit: Limit = 30) -> WriteResult:
    """Preview or create a proposal draft without spending Connects."""
    return await write("create_proposal_draft", payload, user_id, trace_id, idempotency_key, dry_run, approval, weekly_limit)


@mcp.tool(annotations=WRITE)
async def submit_proposal(payload: DraftPayload, user_id: str, trace_id: str, idempotency_key: Key,
                          dry_run: bool = True, approval: str = "", weekly_limit: Limit = 30) -> WriteResult:
    """Preview or submit an approved simulator draft, deducting Connects once."""
    return await write("submit_proposal", payload, user_id, trace_id, idempotency_key, dry_run, approval, weekly_limit)


@mcp.tool(annotations=WRITE)
async def send_message(payload: DraftPayload, user_id: str, trace_id: str, idempotency_key: Key,
                        dry_run: bool = True, approval: str = "", weekly_limit: Limit = 30) -> WriteResult:
    """Preview or send an approved response in the simulator conversation."""
    return await write("send_message", payload, user_id, trace_id, idempotency_key, dry_run, approval, weekly_limit)
