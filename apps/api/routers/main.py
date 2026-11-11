import os
import sqlite3
from collections import Counter
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, Response, UploadFile

from agent.handoffs import Approval
from agent.mcp_client import ToolUnavailable, invoke
from apps.api.auth import oauth_store, session
from apps.api.schemas.models import (
    Balance,
    Credentials,
    Health,
    Job,
    Message,
    PipelineCard,
    Preferences,
    Run,
    RunStart,
    Signup,
    User,
)
from apps.api.streaming import stream
from mcp_servers.marketplace.server import mode
from rag.ingest import loaders
from worker import queue
from worker.main import config

router = APIRouter()


def demo_enabled():
    return os.getenv("GIGBID_DEMO_ACCESS", "1" if os.getenv("APP_ENV") != "production" else "0") == "1"


async def market(account, tool, **kwargs):
    try:
        return await invoke("dashboard", "marketplace", tool, user_id=account["id"], trace_id=uuid4().hex, **kwargs)
    except ToolUnavailable as exc:
        raise HTTPException(503, "Marketplace unavailable. Queued work will retry.") from exc
    except ValueError as exc:
        raise HTTPException(404, "Marketplace item unavailable") from exc


@router.get("/status", response_model=Health)
async def status(request: Request):
    state = "available"
    if os.getenv("GIGBID_MARKETPLACE_DISABLED") == "1" or (
            os.getenv("GIGBID_ENABLE_TEST_CONTROLS") == "1" and request.headers.get("x-gigbid-test-outage") == "1"):
        state = "unavailable"
    elif os.getenv("GIGBID_MARKETPLACE_MCP_URL"):
        try:
            account = session.user(request)
            await market(account, "get_connects_balance")
        except HTTPException as exc:
            if exc.status_code == 503:
                state = "unavailable"
    return Health(status="ok", marketplace=state, mode=mode(), demo_access=demo_enabled())


@router.post("/auth/demo", response_model=User)
def demo(response: Response):
    if not demo_enabled():
        raise HTTPException(404)
    user_id = session.register("Demo reviewer", f"demo-{uuid4().hex}@example.invalid", uuid4().hex, ready=True)
    session.session(response, user_id)
    return User(id=user_id, name="Demo reviewer", email="reviewer@example.invalid",
                settings=Preferences(**{**session.DEFAULTS, "onboarded": True}))


@router.post("/auth/register", status_code=201)
def signup(body: Signup, response: Response):
    try:
        user_id = session.register(body.name, body.email, body.password)
    except sqlite3.IntegrityError as exc:
        raise HTTPException(409, "That email already has an account") from exc
    session.session(response, user_id)
    return {"status": "ok"}


@router.post("/auth/login")
def login(body: Credentials, response: Response):
    session.session(response, session.login(body.email, body.password))
    return {"status": "ok"}


@router.get("/auth/me", response_model=User)
def me(account=Depends(session.user)):
    return account


@router.post("/auth/logout", status_code=204)
def logout(request: Request, response: Response):
    session.logout(request, response)


@router.put("/settings", response_model=Preferences)
def preferences(body: Preferences, account=Depends(session.user)):
    session.update(account["id"], body.model_dump())
    return body


@router.get("/settings/upwork")
def connection(account=Depends(session.user)):
    return {"connected": oauth_store.load(account["id"]) is not None, "mode": mode(),
            "configured": bool(os.getenv("UPWORK_CLIENT_ID"))}


@router.get("/jobs", response_model=list[Job])
async def jobs(query: str = "", category: str = "", account=Depends(session.user)):
    return await market(account, "search_jobs", query=query[:120], category=category[:10])


@router.get("/jobs/{job_id}", response_model=Job)
async def job(job_id: str, account=Depends(session.user)):
    return await market(account, "get_job", job_id=job_id)


@router.get("/balance", response_model=Balance)
async def balance(account=Depends(session.user)):
    return await market(account, "get_connects_balance")


@router.get("/runs", response_model=list[Run])
def runs(kind: str = "", account=Depends(session.user)):
    return queue.list_runs(account["id"], kind)


def get_run(tenant, run_id):
    run = queue.get(tenant, run_id)
    if not run:
        raise HTTPException(404, "Agent run does not exist")
    return run


@router.get("/runs/{run_id}", response_model=Run)
def get(run_id: str, account=Depends(session.user)):
    return get_run(account["id"], run_id)


@router.post("/runs", response_model=Run, status_code=202)
def start(body: RunStart, account=Depends(session.user)):
    return queue.enqueue(account["id"], "bid", body.job_id, account["settings"], body.strategy)


@router.post("/messages/runs", response_model=Run, status_code=202)
def draft_reply(body: RunStart, account=Depends(session.user)):
    return queue.enqueue(account["id"], "conversation", body.job_id, account["settings"])


@router.post("/runs/{run_id}/approval", response_model=Run, status_code=202)
def approve(run_id: str, body: Approval, account=Depends(session.user)):
    if body.action == "reject" and not body.reason.strip():
        raise HTTPException(422, "Enter a rejection reason")
    if body.action == "edit" and not body.text:
        raise HTTPException(422, "Enter the revised draft")
    get_run(account["id"], run_id)
    if not queue.approve(account["id"], run_id, body.model_dump()):
        raise HTTPException(409, "This run is no longer waiting for approval")
    return get_run(account["id"], run_id)


@router.post("/runs/{run_id}/retry", response_model=Run)
def retry(run_id: str, account=Depends(session.user)):
    get_run(account["id"], run_id)
    if not queue.retry(account["id"], run_id):
        raise HTTPException(409, "Only failed runs can be retried")
    return get_run(account["id"], run_id)


@router.get("/runs/{run_id}/events")
def sse(run_id: str, request: Request, account=Depends(session.user)):
    get_run(account["id"], run_id)
    return stream(request, account["id"], run_id)


@router.get("/runs/{run_id}/trace")
def trace(run_id: str, account=Depends(session.user)):
    get_run(account["id"], run_id)
    return {"run_id": run_id, "events": queue.events(account["id"], run_id)}


@router.get("/runs/{run_id}/checkpoints")
async def checkpoints(run_id: str, request: Request, account=Depends(session.user)):
    run = get_run(account["id"], run_id)
    graph = request.app.state.graphs[run["kind"]]
    return [{"checkpoint": entry.config["configurable"].get("checkpoint_id"), "next": entry.next,
             "time": entry.created_at} async for entry in graph.aget_state_history(config(run_id))]


@router.get("/messages", response_model=list[Message])
async def messages(job_id: str = "", account=Depends(session.user)):
    return await market(account, "list_messages", job_id=job_id)


@router.get("/pipeline", response_model=list[PipelineCard])
async def pipeline(account=Depends(session.user)):
    rows = await market(account, "list_pipeline")
    by_job = {row["job_id"]: row for row in rows}
    for run in queue.list_runs(account["id"], "bid"):
        result = run["result"] or {}
        if run["job_id"] in by_job:
            by_job[run["job_id"]]["run_id"] = run["id"]
        elif run["status"] in {"pending", "rejected", "blocked"} and result.get("price_quote"):
            by_job[run["job_id"]] = {"job_id": run["job_id"], "title": result["job"]["title"],
                "stage": "drafted" if run["status"] == "pending" else "lost", "amount": result["price_quote"]["amount"],
                "connects": 0, "run_id": run["id"], "updated": run["updated"]}
    return list(by_job.values())


@router.get("/analytics")
async def analytics(account=Depends(session.user)):
    rows = await market(account, "list_pipeline")
    runs = queue.list_runs(account["id"], "bid")
    stages = Counter(row["stage"] for row in rows if row["connects"] > 0)
    categories = {}
    timing = []
    rejections = Counter()
    for run in runs:
        result = run["result"] or {}
        stage = next((row["stage"] for row in rows if row["job_id"] == run["job_id"] and row["connects"]), None)
        if stage:
            category = result.get("job", {}).get("category", "other")
            metrics = categories.setdefault(category, {"sent": 0, "replied": 0, "hired": 0})
            metrics["sent"] += 1
            metrics["replied"] += stage in {"replied", "interview", "hired"}
            metrics["hired"] += stage == "hired"
            timing.append(sum(event["duration_ms"] for event in result.get("event_stats", [])))
        if run["status"] == "rejected":
            rejections[(result.get("approval") or {}).get("reason", "No reason recorded")] += 1
    return {"sent": sum(stages.values()), "replied": sum(stages.get(stage, 0) for stage in ("replied", "interview", "hired")),
            "hired": stages["hired"], "connects": sum(row["connects"] for row in rows), "categories": categories,
            "average_proposal_ms": round(sum(timing)/len(timing), 2) if timing else 0, "model_cost_usd": 0,
            "rejection_reasons": dict(rejections)}


@router.get("/portfolio")
def portfolio(account=Depends(session.user)):
    persona = account["settings"]["persona"]
    return loaders.load_evidence("ai" if persona == "agency" else persona, account["id"])


@router.post("/portfolio", status_code=201)
async def upload(file: UploadFile = File(...), skills: str = Form(""), kind: str = Form("case_study"),
                 industry: str = Form("General"), account=Depends(session.user)):
    contents = await file.read(5_000_001)
    if len(contents) > 5_000_000:
        raise HTTPException(413, "Use a file smaller than 5 MB")
    persona = account["settings"]["persona"]
    tags = [part.strip()[:50] for part in skills.split(",") if part.strip()][:12]
    try:
        return loaders.ingest(account["id"], "ai" if persona == "agency" else persona, file.filename or "upload.txt",
                              contents, tags, kind, industry[:50])
    except (ValueError, UnicodeError) as exc:
        raise HTTPException(422, str(exc)) from exc


@router.delete("/portfolio/{evidence_id}", status_code=204)
def remove_portfolio(evidence_id: str, account=Depends(session.user)):
    if not loaders.delete(account["id"], evidence_id):
        raise HTTPException(404, "Only uploaded evidence can be deleted")


@router.get("/memory")
async def memory(request: Request, account=Depends(session.user)):
    store = request.app.state.graphs["store"]
    result = []
    for kind in ("style", "outcome"):
        result.extend({"key": item.key, "kind": kind, "value": item.value}
                      for item in await store.asearch((account["id"], kind), limit=60))
    return result


@router.delete("/memory/{kind}/{key}", status_code=204)
async def forget(kind: str, key: str, request: Request, account=Depends(session.user)):
    if kind not in {"style", "outcome"}:
        raise HTTPException(404)
    await request.app.state.graphs["store"].adelete((account["id"], kind), key)
