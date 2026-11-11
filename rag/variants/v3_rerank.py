import os
from functools import lru_cache

from agent.settings import settings
from rag.index.ranking import body, tokens
from rag.variants import v2_hybrid


@lru_cache(maxsize=1)
def encoder():
    from sentence_transformers import CrossEncoder

    return CrossEncoder(settings()["models"]["open"]["reranker"], device="cpu")


def retrieve(query, docs, k=5, requirements=()):
    candidates = v2_hybrid.retrieve(query, docs, k * 3, requirements)
    if not candidates:
        return []
    if os.getenv("GIGBID_CROSS_ENCODER") == "1":
        scores = encoder().predict([(query, body(row)) for row in candidates])
    else:
        # CPU fallback uses paired query/document features. Benchmark it under a separate name.
        terms = tokens(query)
        pairs = set(zip(terms, terms[1:]))
        scores = []
        for row in candidates:
            words = tokens(body(row))
            exact = len(set(terms) & set(words))
            adjacent = len(pairs & set(zip(words, words[1:])))
            skills = len(set(skill.casefold() for skill in requirements)
                         & set(skill.casefold() for skill in row["skills"]))
            scores.append(exact + 2 * adjacent + 2 * skills)
    return [row for _, row in sorted(zip(scores, candidates), key=lambda pair: -pair[0])[:k]]
