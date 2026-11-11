from time import perf_counter

from agent.nodes.fit_matcher import map_requirements
from agent.nodes.risk_assessor import scan


def baseline(job, docs, kind):
    start = perf_counter()
    matches = map_requirements(job["skills"], docs)
    coverage = sum(bool(value) for value in matches.values()) / (len(matches) or 1)
    if kind == "single_rule":
        bid = coverage > 0 and job["budget_max"] > 0
    else:
        bid = coverage >= .65 and not scan(job["description"]) and job["budget_max"] > 0
    return {"bid": bid, "ms": (perf_counter()-start)*1000,
            "injection_decision": bid and "injection" in scan(job["description"])}
