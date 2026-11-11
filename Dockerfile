FROM node:22-bookworm-slim AS web
WORKDIR /repo
COPY docs/openapi.json docs/openapi.json
COPY apps/web apps/web
WORKDIR /repo/apps/web
RUN npm ci && npm run build

FROM python:3.13-slim AS service
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 GIGBID_STATE_DIR=/var/lib/gigbid
WORKDIR /repo
COPY pyproject.toml ./
COPY agent agent
COPY apps/api apps/api
COPY data data
COPY gigsim gigsim
COPY mcp_servers mcp_servers
COPY rag rag
COPY worker worker
COPY docs docs
COPY evals/results evals/results
RUN pip install --no-cache-dir .
COPY --from=web /repo/apps/web/dist apps/web/dist
EXPOSE 8000
CMD ["sh", "-c", "uvicorn apps.api.main:app --host 0.0.0.0 --port ${PORT:-8000} --no-access-log"]

