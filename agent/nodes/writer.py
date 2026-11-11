from agent.handoffs import ProposalDraft
from agent.models import rank_with_open_model


async def writer(state, *, store=None):
    matched = set(state["fit_report"]["evidence_ids"])
    cases = [row for row in state["evidence"] if row["id"] in matched and row["type"] == "case_study"]
    cases, tokens, model = await rank_with_open_model(cases, state["job"]["skills"])
    revision = state.get("revision", 0)
    example = cases[0] if cases else None
    job = state["job"]
    strategy = state.get("strategy", "evidence_first")
    lead = f'Project: {job["title"]}'
    claim = f'Portfolio evidence: {example["text"].strip()} [{example["id"]}]' if example else ""
    plan = "I propose to deliver a reproducible baseline and a documented handoff."
    if store and await store.aget((state["user_id"], "style"), "concise"):
        plan = "I propose to review the requirements with you and agree on acceptance criteria."
    paragraphs = [lead, claim, plan] if strategy == "evidence_first" or revision else [lead, plan, claim]
    draft = ProposalDraft(job_id=job["id"], cover_letter="\n\n".join(filter(None, paragraphs)),
                          evidence_ids=[example["id"]] if example else [],
                          screening_answers=["I propose to validate the deliverable against agreed acceptance criteria and document the results."
                                             for _ in job["screening_questions"]])
    return {"proposal_draft": draft.model_dump(), "tokens": tokens, "event_stats": [{"model": model}],
            "revision": revision}
