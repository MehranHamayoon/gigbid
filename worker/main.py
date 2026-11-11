import asyncio
import logging
import os
from contextlib import AsyncExitStack, asynccontextmanager

from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.store.postgres.aio import AsyncPostgresStore
from langgraph.store.sqlite.aio import AsyncSqliteStore
from langgraph.types import Command

from agent.graphs.bid_graph import build_bid_graph
from agent.graphs.conversation_graph import build_conversation_graph
from agent.mcp_client import ToolUnavailable
from agent.nodes.scout import search
from agent.settings import STATE
from apps.api.auth.session import due_searches
from worker import queue

log = logging.getLogger("gigbid")


@asynccontextmanager
async def runtime():
    STATE.mkdir(exist_ok=True, parents=True)
    async with AsyncExitStack() as stack:
        url = os.getenv("DATABASE_URL")
        if url:
            saver = await stack.enter_async_context(AsyncPostgresSaver.from_conn_string(url))
            store = await stack.enter_async_context(AsyncPostgresStore.from_conn_string(url))
        else:
            saver = await stack.enter_async_context(AsyncSqliteSaver.from_conn_string(str(STATE / "checkpoints.sqlite")))
            store = await stack.enter_async_context(AsyncSqliteStore.from_conn_string(str(STATE / "memory.sqlite")))
        await saver.setup()
        await store.setup()
        yield {"bid": build_bid_graph(saver, store), "conversation": build_conversation_graph(saver, store),
               "store": store}


def config(run_id):
    return {"configurable": {"thread_id": run_id}, "recursion_limit": 38, "metadata": {"gigbid_trace_id": run_id}}


async def process(run, graphs):
    graph = graphs[run["kind"]]
    cfg = config(run["id"])
    try:
        checkpoint = await graph.aget_state(cfg)
        if not checkpoint.values:
            incoming = run["initial"]
        elif checkpoint.interrupts:
            incoming = Command(resume=run["resume"]) if run["resume"] else None
        else:
            incoming = None
        if not checkpoint.values or (checkpoint.next and (not checkpoint.interrupts or run["resume"])):
            async for update in graph.astream(incoming, config=cfg, stream_mode="updates"):
                for node, payload in update.items():
                    meta = (payload or {}).get("event_stats", [{}])[0] if isinstance(payload, dict) else {}
                    queue.event(run, {"node": node, "status": "paused" if node == "__interrupt__" else "done", **meta})
        checkpoint = await graph.aget_state(cfg)
        result = checkpoint.values
        queue.save(run, "pending" if checkpoint.interrupts else result.get("approval_status", "needs_attention"), result)
    except ToolUnavailable:
        retry = run["attempts"] < 3
        queue.save(run, "marketplace_unavailable" if retry else "needs_attention", run["result"],
                   "Marketplace unavailable. The run can be retried.", min(60, 5 * 2 ** run["attempts"]))
        queue.event(run, {"node": "marketplace", "status": "unavailable"})
    except Exception as exc:
        # Exception text can contain private tool data. Retain only the class name in operational logs.
        log.error("Run %s failed (%s)", run["id"], type(exc).__name__)
        queue.save(run, "needs_attention", run["result"], "Agent run needs attention. Inspect its checkpoint.")
        queue.event(run, {"node": "worker", "status": "error", "error_type": type(exc).__name__})


async def drain(graphs, limit=12):
    for _ in range(limit):
        run = queue.claim()
        if not run:
            return
        await process(run, graphs)


async def local_worker(graphs):
    while True:
        await drain(graphs)
        await asyncio.sleep(0.3)


async def startup(ctx):
    ctx["runtime"] = runtime()
    ctx["graphs"] = await ctx["runtime"].__aenter__()


async def shutdown(ctx):
    await ctx["runtime"].__aexit__(None, None, None)


async def execute_queue(ctx):
    await drain(ctx["graphs"])


async def scout_schedules(ctx):
    from uuid import uuid4

    for tenant, settings in due_searches():
        try:
            results = await search(tenant, uuid4().hex, settings["filters"])
            for job in results[:5]:
                queue.enqueue(tenant, "bid", job["id"], settings)
        except ToolUnavailable:
            log.info("Scouting delayed because marketplace is unavailable")


class WorkerSettings:
    from arq import cron
    from arq.connections import RedisSettings

    functions = [execute_queue]
    cron_jobs = [cron(execute_queue, second={0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55}),
                 cron(scout_schedules, minute=set(range(60)), second=10)]
    redis_settings = RedisSettings.from_dsn(os.getenv("REDIS_URL", "redis://localhost:6379/0"))
    on_startup = startup
    on_shutdown = shutdown
