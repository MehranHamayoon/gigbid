from math import log2
from time import perf_counter

from rag.ingest.loaders import load_fixtures
from rag.retriever import VARIANTS, search


def retrieval(jobs, gold):
    docs = load_fixtures("evidence.json")
    profiles = {persona: [row for row in docs if row["persona"] == persona] for persona in ("ai", "web", "data")}
    results = []
    for variant in VARIANTS:
        for row in gold:
            job = jobs[row["job_id"]]
            query = f'{job["title"]}\n{job["description"]}'
            start = perf_counter()
            ranked = search(query, profiles[row["persona"]], 10, job["skills"], variant)
            elapsed = (perf_counter()-start)*1000
            expected = set(row["evidence"])
            actual = [item["id"] for item in ranked]
            gains = [1/log2(rank+2) for rank, item in enumerate(actual) if item in expected]
            idcg = sum(1/log2(rank+2) for rank in range(len(expected)))
            ranks = [rank+1 for rank, item in enumerate(actual) if item in expected]
            results.append({"variant": variant, "job_id": job["id"], "persona": row["persona"], "scenario": row["scenario"],
                            "recall5": len(expected.intersection(actual[:5])) / len(expected), "mrr": 1/min(ranks) if ranks else 0,
                            "ndcg10": sum(gains)/idcg, "ms": elapsed, "ranked": actual})
    return results
