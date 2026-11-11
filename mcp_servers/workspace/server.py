from contextlib import closing
from datetime import datetime, timedelta, timezone
from hashlib import sha256

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations

from agent.storage import open_db, utc

mcp = FastMCP("GigBid Workspace", stateless_http=True, json_response=True)
READ = ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=True)
WRITE = ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=True)


@mcp.tool(annotations=READ)
def free_calendar_slots(user_id: str) -> list[str]:
    """Return the next three simulated calendar slots in UTC."""
    now = datetime.now(timezone.utc)
    return [(now + timedelta(days=day)).replace(hour=15, minute=0, second=0, microsecond=0).isoformat()
            for day in (1, 2, 3)]


def record(user_id, kind, value, key):
    with closing(open_db("workspace.sqlite")) as conn, conn:
        conn.execute("CREATE TABLE IF NOT EXISTS drafts (tenant TEXT,id TEXT,kind TEXT,value TEXT,date TEXT,PRIMARY KEY(tenant,id))")
        conn.execute("INSERT OR IGNORE INTO drafts VALUES (?,?,?,?,?)", (user_id, key, kind, value, utc()))
    return {"id": key, "status": "tentative" if kind == "hold" else "draft"}


@mcp.tool(annotations=WRITE)
def create_tentative_hold(user_id: str, start: str, title: str) -> dict:
    """Create a tentative calendar hold in the local workspace without inviting anyone."""
    datetime.fromisoformat(start)
    return record(user_id, "hold", f"{start} {title}", sha256(f"{start}{title}".encode()).hexdigest())


@mcp.tool(annotations=WRITE)
def create_email_draft(user_id: str, subject: str, body: str) -> dict:
    """Save a local email draft without sending it."""
    return record(user_id, "email", f"{subject}\n{body}", sha256(f"{subject}{body}".encode()).hexdigest())
