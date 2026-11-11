import hmac
import os
from contextlib import asynccontextmanager

from starlette.applications import Starlette
from starlette.responses import PlainTextResponse

from agent.mcp_client import SERVERS


def serve(name):
    server = SERVERS[name]
    inner = server.streamable_http_app()

    @asynccontextmanager
    async def lifespan(_):
        async with server.session_manager.run():
            yield

    app = Starlette(routes=inner.routes, lifespan=lifespan)

    @app.middleware("http")
    async def protect(request, call_next):
        token = os.getenv("GIGBID_INTERNAL_TOKEN", "")
        if not token or not hmac.compare_digest(request.headers.get("authorization", ""), f"Bearer {token}"):
            return PlainTextResponse("Unauthorized", status_code=401)
        return await call_next(request)

    return app


def marketplace():
    return serve("marketplace")


def portfolio():
    return serve("portfolio")


def workspace():
    return serve("workspace")
