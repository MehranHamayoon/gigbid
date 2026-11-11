# ADR 002 · Hybrid retrieval

V2 uses BM25 and a normalized term/character cosine index with reciprocal rank fusion. The corrective variant marginally improved fixture recall and was slower. The shipped hybrid path is reproducible on CPU without downloads. The cross-encoder is configurable separately from the pair-feature proxy used in the local benchmark.
