from rag.index.ranking import fuse
from rag.variants import v0_naive


def retrieve(query, docs, k=5, requirements=()):
    ranked = [v0_naive.retrieve(item, docs, k) for item in requirements]
    return fuse([v0_naive.retrieve(query, docs, k), *ranked], k)
