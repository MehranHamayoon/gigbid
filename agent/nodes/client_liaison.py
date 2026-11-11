from agent.mcp_client import invoke
from agent.nodes.risk_assessor import scan


async def client_liaison(state):
    common = {"user_id": state["user_id"], "trace_id": state["trace_id"]}
    messages = await invoke("client_liaison", "marketplace", "list_messages", job_id=state["job_id"], **common)
    incoming = next((message for message in reversed(messages) if message["direction"] == "inbound"), None)
    if not incoming:
        return {"approval_status": "blocked", "liaison": {"intent": "none", "draft": "", "slots": []}}
    body = incoming["body"].casefold()
    flags = scan(body)
    if flags:
        return {"approval_status": "blocked", "liaison": {"intent": "scam signal", "draft": "", "slots": [], "flags": flags}}
    slots = []
    if any(term in body for term in ("interview", "schedule", "meet")):
        intent = "interview request"
        slots = await invoke("client_liaison", "workspace", "free_calendar_slots", user_id=state["user_id"])
        dates = ", ".join(slot[:10] for slot in slots)
        text = f"Thanks for the reply. I am available at 15:00 UTC on {dates}. Which date works for you?"
    elif any(term in body for term in ("price", "budget", "rate")):
        intent = "negotiation"
        text = "Thanks for sharing your budget. Which deliverable is most important for the first milestone?"
    else:
        intent = "question"
        text = "Thanks for the question. Could you share the acceptance criteria you want to use for the first milestone?"
    return {"liaison": {"intent": intent, "draft": text, "slots": slots}, "approval_status": "drafted"}
