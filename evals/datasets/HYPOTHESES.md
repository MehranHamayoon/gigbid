# Evaluation hypotheses

These hypotheses apply to the deterministic local development study.

- A. Descriptions with explicit examples of alternative user vocabulary should improve tool selection over matching fine-grained tool names alone. Grouping by domain should reduce the schema vocabulary but leave more ambiguity about the selected sub-operation.
- B. Adding BM25 fusion to the term/character vector baseline should improve ranking on exact tool names. Strong synthetic overlap may leave little measurable headroom. V8 should remove unrelated matches on out-of-persona requests, where recall is undefined when no relevant evidence exists.
- C. The explicit fit/risk join should reduce bids on partial-fit and unsafe jobs. The direct router should have lower latency.
- X1. The three-portfolio router should identify evidence for more eligible jobs than a single AI/ML portfolio, with greater retrieval cost and ties on generic skills.
