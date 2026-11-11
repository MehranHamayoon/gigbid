
from agent.mcp_client import invoke


async def scout(state):
    job = await invoke("scout", "marketplace", "get_job", job_id=state["job_id"],
                       user_id=state["user_id"], trace_id=state["trace_id"])
    return {"job": job}


async def search(user_id, trace_id, query="", category=""):
    rows = await invoke("scout", "marketplace", "search_jobs", user_id=user_id, trace_id=trace_id,
                        query=query, category=category)
    return list({row["id"]: row for row in rows}.values())
