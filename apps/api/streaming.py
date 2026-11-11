import asyncio
import json

from fastapi.responses import StreamingResponse

from worker import queue


def stream(request, tenant, run_id):
    async def generate():
        try:
            cursor = int(request.headers.get("last-event-id", "0"))
        except ValueError:
            cursor = 0
        while not await request.is_disconnected():
            for item in queue.events(tenant, run_id, cursor):
                cursor = item["seq"]
                yield f"id: {cursor}\nevent: node\ndata: {json.dumps(item)}\n\n"
            run = queue.get(tenant, run_id)
            if not run or run["status"] not in queue.ACTIVE:
                yield f'event: complete\ndata: {json.dumps({"status": run["status"] if run else "missing"})}\n\n'
                break
            yield ": keepalive\n\n"
            await asyncio.sleep(0.35)

    return StreamingResponse(generate(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})
