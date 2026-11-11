from typing import TypedDict

from langgraph.graph import END, START, StateGraph

from rag.variants import v2_hybrid


class State(TypedDict):
    query: str
    docs: list[dict]
    requirements: list[str]
    k: int
    evidence: list[dict]
    covered: list[str]


def search(state):
    return {"evidence": v2_hybrid.retrieve(state["query"], state["docs"], state["k"], state["requirements"])}


def grade(state):
    seen = {skill.casefold() for row in state["evidence"] for skill in row["skills"]}
    return {"covered": [term for term in state["requirements"] if term.casefold() in seen]}


def correct(state):
    missing = {term.casefold() for term in state["requirements"] if term not in state["covered"]}
    matches = [row for row in state["docs"] if missing.intersection(skill.casefold() for skill in row["skills"])]
    retrieved = v2_hybrid.retrieve(state["query"], matches, state["k"], list(missing))
    merged = {row["id"]: row for row in [*retrieved, *state["evidence"]]}
    return {"evidence": list(merged.values())[:state["k"]]}


def constrain(state):
    requested = {skill.casefold() for skill in state["requirements"]}
    return {"evidence": [row for row in state["evidence"] if not requested or
                          requested.intersection(skill.casefold() for skill in row["skills"])]}


builder = StateGraph(State)
for node in (search, grade, correct, constrain):
    builder.add_node(node.__name__, node)
builder.add_edge(START, "search")
builder.add_edge("search", "grade")
builder.add_conditional_edges("grade", lambda state: "constrain" if state["covered"] == state["requirements"] else "correct",
                              ["constrain", "correct"])
builder.add_edge("correct", "constrain")
builder.add_edge("constrain", END)
graph = builder.compile()


def retrieve(query, docs, k=5, requirements=()):
    return graph.invoke({"query": query, "docs": docs, "requirements": list(requirements), "k": k})["evidence"]
