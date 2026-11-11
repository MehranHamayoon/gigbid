from rag.index.ranking import bm25, fuse
from rag.variants import v0_naive


def retrieve(query, docs, k=5, requirements=()):
    expanded = " ".join([query, *requirements])
    return fuse([v0_naive.retrieve(expanded, docs, k * 3), bm25(expanded, docs)[:k * 3]], k)
