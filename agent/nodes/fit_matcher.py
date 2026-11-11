import asyncio

from agent.handoffs import FitReport
from agent.mcp_client import invoke
from mcp_servers.marketplace.server import mode


def map_requirements(skills, evidence):
    return {skill: [row["id"] for row in evidence if skill.casefold() in
                    {tag.casefold() for tag in row["skills"]}] for skill in skills}


async def fit_matcher(state):
    job = state["job"]
    personas = ["ai", "web", "data"] if state["persona"] == "agency" else [state["persona"]]
    query = f'{job["title"]}\n' + "\n".join(job["deliverables"])
    lists = await asyncio.gather(*(invoke("fit_matcher", "portfolio", "search_evidence", requirement=query,
        k=8, filters={"persona": persona, "tenant": state["user_id"], "skills": job["skills"],
        "variant": state.get("rag_variant"), "exclude_synthetic": mode() == "upwork"}) for persona in personas))
    options = [(persona, evidence, map_requirements(job["skills"], evidence))
               for persona, evidence in zip(personas, lists)]
    persona, evidence, matrix = max(options, key=lambda item: (sum(bool(ids) for ids in item[2].values()), item[0] == job["category"]))
    matched = [skill for skill, ids in matrix.items() if ids]
    report = FitReport(score=len(matched) / (len(matrix) or 1), matched_skills=matched,
                       missing_skills=[skill for skill in matrix if not matrix[skill]], matrix=matrix,
                       evidence_ids=list(dict.fromkeys(item for ids in matrix.values() for item in ids)))
    return {"fit_report": report.model_dump(), "evidence": evidence, "selected_persona": persona}


