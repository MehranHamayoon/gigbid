from langgraph.graph import END, START, StateGraph
from langgraph.store.base import BaseStore
from langgraph.types import Send

from agent.graphs.approval import human_approval, market, proposal_tool, request
from agent.graphs.common import budget_stop, measured, within_budget
from agent.mcp_client import invoke
from agent.memory.store import promote_outcome, promote_style
from agent.nodes.analyst import analyst
from agent.nodes.compliance import compliance, review
from agent.nodes.critic import critic, revise
from agent.nodes.fit_matcher import fit_matcher
from agent.nodes.pricing import decision, pricing
from agent.nodes.risk_assessor import risk_assessor
from agent.nodes.scout import scout
from agent.nodes.verifier import verifier
from agent.nodes.writer import writer
from agent.state import GigBidState
from rag.verify import verify_claims


async def preview(state):
    return {"preview": await market(state, proposal_tool(), request(state, state["proposal_draft"]["cover_letter"])),
            "approval_status": "pending"}


async def review_edit(state):
    approval = state["approval"]
    draft = dict(state["proposal_draft"])
    previous = draft["cover_letter"]
    text = approval["text"] if approval["action"] == "edit" else previous
    if text is None:
        return {"approval_status": "blocked", "compliance_verdict": {"allowed": False, "reasons": ["Missing edited text."]}}
    identifiers = {row["evidence_id"] for row in verify_claims(text, state["evidence"], state["job"]["title"])
                   if row["status"] == "supported"}
    fresh = []
    for evidence_id in sorted(identifiers):
        row = await invoke("writer", "portfolio", "get_case_study", id=evidence_id,
                           persona=state["selected_persona"], tenant=state["user_id"])
        if row:
            fresh.append(row)
    verdict = review(text, fresh, state["job"]["title"])
    draft["cover_letter"] = text
    return {"proposal_draft": draft, "claim_verification": verify_claims(text, fresh, state["job"]["title"]),
            "compliance_verdict": verdict, "approval_status": "approved" if verdict["allowed"] else "blocked",
            "approval": {**approval, "previous": previous}}


async def dispatch(state, *, store: BaseStore):
    text = state["proposal_draft"]["cover_letter"]
    payload = request(state, text)
    created = await market(state, "create_proposal_draft", payload, dry_run=False)
    outcome = created if proposal_tool() == "create_proposal_draft" else await market(
        state, "submit_proposal", payload, dry_run=False)
    if state["approval"]["action"] == "edit":
        await promote_style(store, state["user_id"], state["trace_id"], state["approval"]["previous"], text)
    await promote_outcome(store, state["user_id"], state["trace_id"], state["job"]["category"], outcome["stage"])
    return {"outcome": outcome, "approval_status": "complete"}


def build_bid_graph(checkpointer=None, store=None):
    graph = StateGraph(GigBidState)
    for node in (scout, analyst, risk_assessor, fit_matcher, decision, pricing, writer, verifier, critic,
                 revise, compliance, preview, human_approval, review_edit, dispatch, budget_stop):
        graph.add_node(node.__name__, measured(node, store))
    graph.add_edge(START, "scout")
    branches = ["analyst", "risk_assessor", "fit_matcher"]
    graph.add_conditional_edges("scout", lambda state: [Send(node, state) for node in branches], branches)
    graph.add_edge(branches, "decision")
    graph.add_conditional_edges("decision", lambda state: "pricing" if state["decision"]["action"] == "bid" else END,
                                ["pricing", END])
    graph.add_conditional_edges("pricing", lambda state: "writer" if state["decision"]["action"] == "bid" else END,
                                ["writer", END])
    graph.add_conditional_edges("writer", lambda state: "verifier" if within_budget(state) else "budget_stop",
                                ["verifier", "budget_stop"])
    graph.add_edge("verifier", "critic")
    graph.add_conditional_edges("critic", lambda state: "revise" if not state["critique"]["accepted"] and
                                state.get("revision", 0) < 2 else "compliance", ["revise", "compliance"])
    graph.add_edge("revise", "writer")
    graph.add_conditional_edges("compliance", lambda state: "preview" if state["compliance_verdict"]["allowed"] else END,
                                ["preview", END])
    graph.add_edge("preview", "human_approval")
    graph.add_conditional_edges("human_approval", lambda state: END if state["approval_status"] == "rejected" else "review_edit",
                                ["review_edit", END])
    graph.add_conditional_edges("review_edit", lambda state: "dispatch" if state["approval_status"] == "approved" else END,
                                ["dispatch", END])
    graph.add_edge("dispatch", END)
    graph.add_edge("budget_stop", END)
    return graph.compile(checkpointer=checkpointer, store=store)


