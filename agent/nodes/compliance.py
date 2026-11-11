import re

from agent.handoffs import ComplianceVerdict
from agent.settings import policy
from rag.verify import verify_claims


def review(text, evidence, title):
    reasons = []
    if not text.strip():
        reasons.append("The draft is empty.")
    if re.search(policy()["blocked_draft"], text, re.I):
        reasons.append("Draft includes prohibited contact details, an external link, or a guarantee.")
    claims = verify_claims(text, evidence, title)
    if not any(row["status"] == "supported" for row in claims):
        reasons.append("At least one exact portfolio excerpt with its citation is required.")
    if any(row["status"] != "supported" for row in claims):
        reasons.append("The draft has a sentence that is not grounded in the available evidence.")
    return ComplianceVerdict(allowed=not reasons, reasons=reasons).model_dump()


def compliance(state):
    verdict = review(state["proposal_draft"]["cover_letter"], state["evidence"], state["job"]["title"])
    return {"compliance_verdict": verdict, "approval_status": "drafted" if verdict["allowed"] else "blocked"}
