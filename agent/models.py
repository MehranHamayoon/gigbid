import json
import os
from functools import lru_cache

import httpx

from agent.settings import ROOT, settings


@lru_cache(maxsize=32)
def prompt(node):
    return (ROOT / f"agent/prompts/{node}.v1.md").read_text(encoding="utf-8")


async def rank_with_open_model(rows, skills):
    base_url = os.getenv("OLLAMA_BASE_URL")
    if not base_url or not rows:
        return rows, 0, "extractive"
    profiles = settings()["models"]
    profile = os.getenv("MODEL_PROFILE", "open")
    if profile not in {"open", "open_small"}:
        return rows, 0, "extractive"
    model = profiles[profile].get("writer", profiles["open"]["writer"])
    data = {"required_skills": skills, "candidate_evidence": [{"i": i, "text": row["text"][:300]}
              for i, row in enumerate(rows)]}
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(f"{base_url.rstrip('/')}/api/chat", json={
                "model": model, "stream": False, "format": "json", "options": {"temperature": 0, "num_predict": 80},
                "messages": [{"role": "system", "content": prompt("writer")},
                             {"role": "user", "content": json.dumps(data)}]})
            response.raise_for_status()
        payload = response.json()
        indices = json.loads(payload["message"]["content"])["order"]
        if not isinstance(indices, list) or any(type(index) is not int or not 0 <= index < len(rows) for index in indices):
            raise ValueError("Invalid ranked evidence list")
        order = list(dict.fromkeys([*indices, *range(len(rows))]))
        return [rows[i] for i in order], payload.get("prompt_eval_count", 0) + payload.get("eval_count", 0), model
    except (httpx.HTTPError, ValueError, KeyError, TypeError):
        return rows, 0, "extractive"
