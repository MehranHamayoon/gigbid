# Runbook

## Local review

Install Python 3.13 and Node.js 22. Run the commands from the repository root.

```sh
python -m venv .venv
# Activate the virtual environment for your shell.
python -m pip install -e ".[dev]"
npm --prefix apps/web ci
npm --prefix apps/web run build
python -m uvicorn apps.api.main:app --host 127.0.0.1 --port 8000
```

Visit http://127.0.0.1:8000 and choose **Explore simulator demo**. Analyze GB-001, inspect its evidence, then approve. Open Messages and approve the suggested reply. GB-003 and GB-004 exercise the unpaid-work and planted-instruction routes.

## Compose

```sh
python infra/prepare_env.py
docker compose up --build
```

This starts the app, Redis/Arq worker, three private MCP endpoints, simulator, and PostgreSQL. Add `--profile models` for Ollama. Pull the configured models and set `OLLAMA_BASE_URL=http://ollama:11434` in the Compose environment to enable open-model evidence ordering. Set `MARKETPLACE_MODE=upwork` only with a registered OAuth client and confirmed tool schemas. Live scouting is opt-in via a saved search with a default four-hour interval. The CLI and approved MCP are the supported boundaries for external data.

## Render

Connect the public repository as a Docker Web Service, branch `main`, root Dockerfile, health path `/health`. Set `APP_ENV=production`, a random `APP_SECRET_KEY` of at least 32 characters, and private `REVIEWER_EMAIL` and `REVIEWER_PASSWORD` values. Leave `GIGBID_EMBEDDED_WORKER=1` for a single-service deployment. For persistence across Render restarts and deploys, use a plan with a disk mounted at `/var/lib/gigbid`. The free service has cold starts and ephemeral disk. Share reviewer credentials in the private Classroom comment. Use HTTPS.

## Failures and recovery

When the Marketplace MCP endpoint becomes unreachable, bounded retries finish with an unavailable banner. Queued runs keep their IDs and can retry after recovery. A lease covers a worker crash. Approvals are durable and application retries use the same marketplace write key. The simulator records the result and deducts Connects atomically. Prefer inspecting a checkpoint or running a replay in a fresh isolated tenant. Never replay an old live approval to execute a real marketplace write.

## Observability

Inspect the Run timeline and its Raw trace link. Private traces use the same run ID as the Marketplace audit log. Set `LANGSMITH_TRACING=true` and a project key only for synthetic workloads if you want provider traces. Local node events mask common email and number patterns. Health status is at `/health`.
