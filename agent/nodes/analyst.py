from agent.handoffs import JobSpec


def analyst(state):
    job = state["job"]
    return {"job_spec": JobSpec(job_id=job["id"], title=job["title"], deliverables=job["deliverables"],
                               required_skills=job["skills"], budget_min=job["budget_min"],
                               budget_max=job["budget_max"], duration_days=job["duration_days"],
                               screening_questions=job["screening_questions"],
                               hidden_needs=["Define an acceptance check and handoff scope."]).model_dump()}
