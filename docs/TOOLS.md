# Tool surface

The browser cannot access internal MCP routes. Compose uses an internal bearer token. Marketplace writes also require proof over the exact tenant, tool, idempotency key and payload after the graph resumes. The Marketplace server limits scouting calls per tenant and records redacted audit events.

| Tool | Server | Access | MCP annotations | Auth |
|---|---|---|---|---|
| search_evidence | Portfolio | Read | read-only, idempotent | Internal bearer or local stdio |
| get_case_study | Portfolio | Read | read-only, idempotent | Internal bearer or local stdio |
| list_skills | Portfolio | Read | read-only, idempotent | Internal bearer or local stdio |
| search_jobs | Marketplace | Read | read-only, idempotent | Internal bearer |
| get_job | Marketplace | Read | read-only, idempotent | Internal bearer |
| get_client_history | Marketplace | Read | read-only, idempotent | Internal bearer |
| get_connects_balance | Marketplace | Read | read-only, idempotent | Internal bearer |
| list_messages | Marketplace | Read | read-only, idempotent | Internal bearer |
| list_pipeline | Marketplace | Read | read-only, idempotent | Internal bearer |
| create_proposal_draft | Marketplace | Write | non-destructive, idempotent | Bearer and approval proof |
| submit_proposal | Marketplace | Write | destructive, idempotent | Bearer and approval proof |
| send_message | Marketplace | Write | destructive, idempotent | Bearer and approval proof |
| free_calendar_slots | Workspace | Read | read-only, idempotent | Internal bearer |
| create_tentative_hold | Workspace | Write | non-destructive, idempotent | Internal bearer |
| create_email_draft | Workspace | Write | non-destructive, idempotent | Internal bearer |

The Portfolio server also exposes two URI templates and the `answer_screening_question` prompt. Workspace uses a mock calendar and email store. Roles and their permitted calls are in `agent/mcp_client.py`. The in-memory contract snapshot lives in `tests/contract/tool_schemas.json`.

- **Upwork official MCP.** The vendor owns the marketplace interface and requires authorization. Use draft-only write mappings and platform confirmation. Live OAuth and mappings require an approved client.
- **GitHub official MCP.** The provider owns repo access control. Restrict its file reader to read-only public repository content for portfolio ingestion.
