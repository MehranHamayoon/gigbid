# ADR 001 · Approval and idempotent writes

The graph persists approval as an interrupt and signs the approved marketplace payload in the dispatch node. Simulator writes are isolated by tenant. A retry reuses the original key and payload, with the write result stored in the same transaction as its effect. An API-level boolean would let an approval go stale across process restarts and would provide weaker evidence that the correct text and cost were authorized.
