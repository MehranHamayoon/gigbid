from rag.variants import v2_hybrid


def retrieve(query, docs, k=5, requirements=()):
    candidates = v2_hybrid.retrieve(query, docs, k * 3, requirements)
    rank = {row["id"]: index for index, row in enumerate(candidates)}
    return sorted(candidates, key=lambda row: rank[row["id"]] - {"hired": 2, "replied": 1}.get(row.get("outcome"), 0))[:k]
