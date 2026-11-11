from time import perf_counter
from functools import wraps
import inspect

from langgraph.store.base import BaseStore

from agent.settings import settings


def measured(node):
    @wraps(node)
    async def execute(state, *, store: BaseStore):
        start = perf_counter()
        result = node(state, store=store) if "store" in inspect.signature(node).parameters else node(state)
        if inspect.isawaitable(result):
            result = await result
        meta = result.pop("event_stats", [{}])[0]
        return {**result, "steps": 1,
                "event_stats": [{"node": node.__name__, "duration_ms": round((perf_counter()-start)*1000, 3),
                                 "tokens": result.get("tokens", 0), "usd": 0, **meta}]}
    return execute


def within_budget(state):
    budgets = settings()["budgets"]
    return state.get("steps", 0) < budgets["max_graph_steps"] and state.get("tokens", 0) < budgets["max_tokens_per_job"]


def budget_stop(state):
    return {"approval_status": "needs_attention",
            "compliance_verdict": {"allowed": False, "reasons": ["Run budget reached."]}}
