import asyncio
import os
from contextlib import asynccontextmanager, suppress
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse

from agent.settings import ROOT
from apps.api.auth.session import reviewer_seed
from apps.api.routers.main import router
from apps.api.routers.oauth import router as oauth_router
from apps.api.routers.public import router as public_router
from worker.main import local_worker, runtime


@asynccontextmanager
async def lifespan(app):
    if os.getenv("APP_ENV") == "production" and len(os.getenv("APP_SECRET_KEY", "")) < 32:
        raise RuntimeError("Set a private APP_SECRET_KEY with at least 32 characters")
    reviewer_seed()
    async with runtime() as graphs:
        app.state.graphs = graphs
        worker = asyncio.create_task(local_worker(graphs)) if os.getenv("GIGBID_EMBEDDED_WORKER", "1") == "1" else None
        try:
            yield
        finally:
            if worker:
                worker.cancel()
                with suppress(asyncio.CancelledError):
                    await worker


app = FastAPI(title="GigBid API", version="1.0.0", lifespan=lifespan)
app.include_router(router, prefix="/api")
app.include_router(oauth_router, prefix="/api")
app.include_router(public_router)


@app.get("/health")
async def health():
    return {"status": "ok", "service": "gigbid-api"}


@app.get("/{path:path}", include_in_schema=False)
def web(path: str, request: Request):
    if path == "api" or path.startswith("api/"):
        raise HTTPException(404)
    web_root = Path(os.getenv("GIGBID_WEB_DIST", ROOT / "apps/web/dist")).resolve()
    candidate = (web_root / path).resolve()
    if candidate.is_relative_to(web_root) and candidate.is_file():
        return FileResponse(candidate)
    index = web_root / "index.html"
    if not index.is_file():
        raise HTTPException(404, "Build the React client or start Vite")
    return FileResponse(index)

