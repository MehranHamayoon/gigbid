from agent.handoffs import Critique


def critic(state):
    notes = []
    if not state["proposal_draft"]["evidence_ids"]:
        notes.append("No verified case study is cited.")
    if state["claims_removed"]:
        notes.append("A claim failed the extractive verification check.")
    if state.get("strategy") == "plan_first" and not state.get("revision"):
        notes.append("Move concrete experience before the delivery plan.")
    if len(state["proposal_draft"]["cover_letter"]) > 1600:
        notes.append("Keep the proposal under 1,600 characters.")
    return {"critique": Critique(accepted=not notes, feedback=notes, revision=state.get("revision", 0)).model_dump()}


def revise(state):
    return {"revision": state.get("revision", 0) + 1}
