from agent.settings import settings
from rag.variants import v0_naive, v1_requirements, v2_hybrid, v3_rerank, v4_outcomes, v8_corrective

VARIANTS = {"v0": v0_naive, "v1": v1_requirements, "v2": v2_hybrid,
            "v3": v3_rerank, "v4": v4_outcomes, "v8": v8_corrective}


def search(query, docs, k=5, requirements=(), variant=None):
    variant = variant or settings()["rag"]["variant"]
    if variant == "v0":
        return VARIANTS[variant].retrieve(query, docs, k)
    return VARIANTS[variant].retrieve(query, docs, k, requirements)
