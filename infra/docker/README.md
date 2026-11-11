The root Dockerfile builds the TypeScript frontend and installs the pinned Python project. Compose reuses the resulting image for the API, worker, three MCP endpoints, and simulator. Private service traffic uses a shared bearer token. PostgreSQL and Redis bind only to the internal network.

For a small single-service review deployment, use the same Dockerfile, attach a persistent volume at /var/lib/gigbid, and allow the embedded worker. Configure environment variables in the host dashboard. See the runbook.
