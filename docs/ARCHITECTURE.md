# Architecture

The FastAPI layer authenticates the tenant, queues a durable run and streams redacted node events. The React client never calls the marketplace directly. Internal MCP tools call a single marketplace port. The simulator handles Connects and proposals in one transaction per external action.

## Bid graph

```mermaid
flowchart TD
    S[Scout] --> A[Job Analyst]
    S --> R[Risk Assessor]
    S --> F[Fit Matcher]
    A --> D{Decision}
    R --> D
    F --> D
    D -->|Skip or watch| X[Stop]
    D -->|Bid| P[Pricing Strategist]
    P --> W[Proposal Writer]
    W --> V[Claim verification]
    V --> C{Critic}
    C -->|Revise, at most twice| W
    C --> G[Compliance Guard]
    G -->|Allowed| H[Preview and human approval]
    G -->|Blocked| X
    H -->|Reject| X
    H -->|Approve or edit| J[Recheck current evidence]
    J -->|Pass| M[Marketplace write]
    J -->|Fail| X
```

## Conversation graph

```mermaid
flowchart LR
    L[Client Liaison] --> C{Intent and risk}
    C -->|Unsafe or no inbound message| S[Stop]
    C -->|Question, negotiation or interview| P[Reply draft and preview]
    P --> H[Human approval]
    H -->|Approve| R[Validate and send]
    H -->|Reject| S
```

The graphs are hand-written StateGraphs. The bid branches use LangGraph Send and a join. Typed results allow routing by explicit fields. Checkpoints store current graph state and the pending interrupt. A separate event ledger stores trace summaries. A LangGraph Store holds tenant-scoped style and outcome namespaces. An outcome enters memory after an approved write returns replied, interview, or hired. Three consistent shorter approved edits can promote the concise style rule. SQLite supports the single-host path. Compose selects the Postgres checkpointer/store and a Redis-backed Arq worker.
