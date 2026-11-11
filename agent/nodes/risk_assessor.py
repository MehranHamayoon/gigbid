import re

from agent.handoffs import RiskReport
from agent.mcp_client import invoke
from agent.settings import policy


def scan(text):
    return [name for name, pattern in policy()["risk_rules"].items() if re.search(pattern, text, re.I)]


async def risk_assessor(state):
    job = state["job"]
    client = await invoke("risk_assessor", "marketplace", "get_client_history", client_id=job["client_id"],
                          user_id=state["user_id"], trace_id=state["trace_id"])
    flags = scan(f'{job["title"]}\n{job["description"]}')
    if not client["payment_verified"]:
        flags.append("unverified_payment")
    if client["average_rating"] < 3:
        flags.append("low_client_rating")
    severe = {"unpaid_work", "off_platform", "injection", "credentials"}
    score = min(1.0, 0.12 + 0.65 * len(severe.intersection(flags)) + 0.12 * len(set(flags) - severe))
    reason = ", ".join(flag.replace("_", " ") for flag in flags)
    explanation = f"Flagged {reason}." if flags else "Payment is verified and no configured risk rule matched."
    return {"risk_report": RiskReport(score=score, flags=flags, explanation=explanation).model_dump()}
