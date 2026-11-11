from langgraph.types import interrupt

from agent.handoffs import Approval
from agent.mcp_client import invoke
from mcp_servers.marketplace.server import DraftPayload, mode, signature


def request(state, text, message=False):
    amount = 0 if message else state["price_quote"]["amount"]
    return DraftPayload(job_id=state["job_id"], text=text, amount=amount).model_dump()


async def market(state, tool, payload, dry_run=True):
    key = f'{state["trace_id"]}-{tool}'
    proof = "" if dry_run else signature(tool, state["user_id"], key, payload)
    return await invoke("approvals", "marketplace", tool, payload=payload, user_id=state["user_id"],
                        trace_id=state["trace_id"], idempotency_key=key, dry_run=dry_run, approval=proof,
                        weekly_limit=state["weekly_limit"])


def proposal_tool():
    return "create_proposal_draft" if mode() == "upwork" else "submit_proposal"


def human_approval(state):
    payload = {"draft": state.get("proposal_draft") or state.get("liaison"),
               "evidence": state.get("claim_verification", []),
               "risk": state.get("risk_report"), "price": state.get("price_quote"), "preview": state["preview"]}
    result = Approval.model_validate(interrupt(payload))
    return {"approval": result.model_dump(), "approval_status": "rejected" if result.action == "reject" else "approved"}
