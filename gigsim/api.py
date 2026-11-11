"""Internal-only REST surface for the student-built simulator."""
import hmac
import os

from fastapi import Depends, FastAPI, Header, HTTPException

from gigsim.service import write
from mcp_servers.marketplace.adapters.gigsim import read_local

app = FastAPI(title="GigBid local marketplace")


def authenticated(authorization: str = Header(default="")):
    token = os.getenv("GIGBID_INTERNAL_TOKEN", "")
    if not token or not hmac.compare_digest(authorization, f"Bearer {token}"):
        raise HTTPException(401, "Internal service token required")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/read/{tool}", dependencies=[Depends(authenticated)])
def read(tool: str, arguments: dict):
    try:
        return read_local(tool, arguments)
    except (KeyError, ValueError) as exc:
        raise HTTPException(400, str(exc)) from exc


@app.post("/write/{tool}", dependencies=[Depends(authenticated)])
def change(tool: str, arguments: dict):
    if tool not in {"send_message", "create_proposal_draft", "submit_proposal"}:
        raise HTTPException(404)
    try:
        return write(tool, **arguments)
    except (KeyError, ValueError) as exc:
        raise HTTPException(409, str(exc)) from exc
