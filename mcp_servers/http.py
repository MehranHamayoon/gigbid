import hmac
import os
from contextlib import asynccontextmanager

from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import PlainTextResponse

from agent.mcp_client import SERVERS


def serve(name):
    server = SERVERS[name]
    security = server.settings.transport_security
    if security is not None:
        # Compose resolves each private endpoint by its service name.
        hosts = [*security.allowed_hosts, f"{name}:*"]
        server.settings.transport_security = security.model_copy(update={"allowed_hosts": hosts})
    inner = server.streamable_http_app()

    @asynccontextmanager
    async def lifespan(_):
        async with server.session_manager.run():
            yield

    async def protect(request, call_next):
        token = os.getenv("GIGBID_INTERNAL_TOKEN", "")
        if not token or not hmac.compare_digest(request.headers.get("authorization", ""), f"Bearer {token}"):
            return PlainTextResponse("Unauthorized", status_code=401)
        return await call_next(request)

    return Starlette(routes=inner.routes, lifespan=lifespan,
                     middleware=[Middleware(BaseHTTPMiddleware, dispatch=protect)])


def marketplace():
    return serve("marketplace")


def portfolio():
    return serve("portfolio")


def workspace():
    return serve("workspace")


