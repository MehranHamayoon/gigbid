from operator import add
from typing import Annotated, Any, TypedDict


class GigBidState(TypedDict, total=False):
    user_id: str
    trace_id: str
    job_id: str
    persona: str
    floor: int
    weekly_limit: int
    filters: str
    strategy: str
    job: dict[str, Any]
    job_spec: dict[str, Any]
    risk_report: dict[str, Any]
    fit_report: dict[str, Any]
    evidence: list[dict[str, Any]]
    selected_persona: str
    decision: dict[str, Any]
    price_quote: dict[str, Any]
    proposal_draft: dict[str, Any]
    claim_verification: list[dict[str, Any]]
    claims_removed: int
    critique: dict[str, Any]
    compliance_verdict: dict[str, Any]
    approval: dict[str, Any]
    approval_status: str
    preview: dict[str, Any]
    outcome: dict[str, Any]
    liaison: dict[str, Any]
    revision: int
    steps: Annotated[int, add]
    tokens: Annotated[int, add]
    event_stats: Annotated[list[dict], add]
