import re

from langgraph.graph import END, START, StateGraph

from agent.graphs.approval import human_approval, market, request
from agent.graphs.common import measured
from agent.nodes.client_liaison import client_liaison
from agent.nodes.risk_assessor import scan
from agent.settings import policy
from agent.state import GigBidState


async def message_preview(state):
    result = await market(state, "send_message", request(state, state["liaison"]["draft"], message=True))
    return {"preview": result, "approval_status": "pending"}


async def send_reply(state):
    edit = state["approval"]
    text = edit["text"] if edit["action"] == "edit" else state["liaison"]["draft"]
    protected = re.sub(r"\b\d{4}-\d{2}-\d{2}\b", "[date]", text or "")
    if not text or len(text.strip()) < 12 or scan(text) or re.search(policy()["blocked_draft"], protected, re.I):
        return {"approval_status": "blocked", "compliance_verdict": {"allowed": False, "reasons": ["Reply failed compliance review."]}}
    outcome = await market(state, "send_message", request(state, text, message=True), dry_run=False)
    return {"outcome": outcome, "approval_status": "complete"}


def build_conversation_graph(checkpointer=None, store=None):
    graph = StateGraph(GigBidState)
    for node in (client_liaison, message_preview, human_approval, send_reply):
        graph.add_node(node.__name__, measured(node, store))
    graph.add_edge(START, "client_liaison")
    graph.add_conditional_edges("client_liaison", lambda state: "message_preview" if state["approval_status"] == "drafted" else END,
                                ["message_preview", END])
    graph.add_edge("message_preview", "human_approval")
    graph.add_conditional_edges("human_approval", lambda state: "send_reply" if state["approval_status"] == "approved" else END,
                                ["send_reply", END])
    graph.add_edge("send_reply", END)
    return graph.compile(checkpointer=checkpointer, store=store)

