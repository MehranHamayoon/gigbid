from agent.handoffs import BidDecision, PriceQuote
from agent.mcp_client import invoke
from agent.settings import policy, settings


def decision(state):
    job, fit, risk = state["job"], state["fit_report"], state["risk_report"]
    rules = settings()["thresholds"]
    if risk["score"] >= rules["maximum_risk_score"]:
        value = BidDecision(action="skip", reason=risk["explanation"])
    elif job["connects"] > policy()["max_connects_per_proposal"] or job["budget_max"] < policy()["minimum_budget_usd"]:
        value = BidDecision(action="skip", reason=f"Does not meet the {policy()['version']} policy limits.")
    elif job["budget_max"] < state["floor"]:
        value = BidDecision(action="skip", reason="The posted budget is below your minimum.")
    elif fit["score"] < rules["minimum_fit_score"]:
        value = BidDecision(action="watch" if fit["score"] else "skip",
                            reason="Missing portfolio evidence for " + ", ".join(fit["missing_skills"]) + ".")
    else:
        value = BidDecision(action="bid", reason=f"{len(fit['matched_skills'])} requirements have portfolio evidence. Risk is within policy.")
    return {"decision": value.model_dump(), "approval_status": value.action}


async def pricing(state):
    job = state["job"]
    context = {"user_id": state["user_id"], "trace_id": state["trace_id"]}
    client = await invoke("pricing", "marketplace", "get_client_history", client_id=job["client_id"], **context)
    balance = await invoke("pricing", "marketplace", "get_connects_balance", **context)
    low = max(job["budget_min"], state["floor"])
    high = job["budget_max"]
    target = int(round((0.65 * client["typical_spend"] + 0.35 * (low + high) / 2) / 5) * 5)
    quote = PriceQuote(amount=max(low, min(high, target)), low=low, high=high, connects=job["connects"],
                       rationale=f'Uses the posted ${low}–${high} band and client history (${client["typical_spend"]} typical).')
    response = {"price_quote": quote.model_dump()}
    if job["connects"] > min(balance["remaining"], state["weekly_limit"] - balance["week_spent"]):
        response.update(decision=BidDecision(action="watch", reason="The weekly or available Connects budget is too low.").model_dump(),
                        approval_status="watch")
    return response
