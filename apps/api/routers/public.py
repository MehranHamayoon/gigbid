from typing import Literal

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from agent.settings import ROOT

router = APIRouter(include_in_schema=False)


@router.get("/field-notes")
def field_notes():
    return FileResponse(ROOT / "docs/public/field-notes.html", media_type="text/html")


@router.get("/demo")
def demo_page():
    return FileResponse(ROOT / "docs/public/demo.html", media_type="text/html")


@router.get("/media/{asset}")
def media(asset: Literal["demo.mp4", "inbox.png"]):
    source = ROOT / ("docs/public/demo.mp4" if asset == "demo.mp4" else "docs/images/inbox.png")
    if not source.is_file():
        raise HTTPException(404)
    return FileResponse(source)


@router.get("/traces/{job}")
def trace(job: Literal["gb-001","gb-003","gb-004"]):
    source = ROOT / f"evals/results/trace-{job}.json"
    if not source.is_file():
        raise HTTPException(404)
    return FileResponse(source, media_type="application/json")
