"""Measure two local Qwen configurations on a fixed, paired evidence selection task."""
import argparse
import json
import platform
from pathlib import Path
from random import Random
from statistics import mean
from subprocess import DEVNULL, Popen
from time import perf_counter, sleep

import httpx

from agent.models import prompt
from agent.settings import ROOT
from evals.runners.run_demo_eval import percentile
from gigsim.service import JOBS
from rag.ingest.loaders import load_fixtures


def run(profile, model_path, server_path, jobs, port, hardware):
    base = f"http://127.0.0.1:{port}"
    process = Popen([str(server_path), "--model", str(model_path), "--host", "127.0.0.1", "--port", str(port),
                     "--ctx-size", "1536", "--threads", "4", "--parallel", "1", "--n-gpu-layers", "0"],
                    stdout=DEVNULL, stderr=DEVNULL)
    docs = load_fixtures("evidence.json")
    rows = []
    try:
        with httpx.Client(base_url=base, timeout=55) as client:
            for attempt in range(90):
                if process.poll() is not None:
                    raise RuntimeError(f"{profile} server failed to start")
                try:
                    if client.get("/health", timeout=1).is_success:
                        break
                except httpx.HTTPError:
                    pass
                sleep(.5)
            else:
                raise RuntimeError(f"{profile} failed to become ready")
            for n, row in enumerate(jobs):
                job = JOBS[row["job_id"]]
                candidates = [item for item in docs if item["persona"] == row["persona"] and item["type"] == "case_study"]
                Random(432+n).shuffle(candidates)
                user = {"required_skills": job["skills"], "candidate_evidence": [
                    {"i": i, "text": item["text"][:300]} for i, item in enumerate(candidates)]}
                started = perf_counter()
                response = client.post("/v1/chat/completions", json={
                    "model": profile, "temperature": 0, "seed": 0, "max_tokens": 72,
                    "response_format": {"type": "json_object"},
                    "messages": [{"role": "system", "content": prompt("writer")},
                                 {"role": "user", "content": json.dumps(user)}],
                })
                response.raise_for_status()
                item = response.json()
                elapsed = (perf_counter()-started)*1000
                try:
                    order = json.loads(item["choices"][0]["message"]["content"])["order"]
                    valid = bool(order) and isinstance(order, list) and all(type(i) is int and 0 <= i < len(candidates) for i in order)
                    first = candidates[order[0]]["id"] if valid else None
                except (ValueError, KeyError, TypeError):
                    valid, first = False, None
                stats = item.get("timings", {})
                rows.append({"job_id": job["id"], "persona": row["persona"], "selected": first, "gold": row["evidence"][0],
                             "top1_correct": first == row["evidence"][0], "schema_valid": valid,
                             "latency_ms": round(elapsed, 2), "tokens": item["usage"]["total_tokens"],
                             "output_tokens_per_second": stats.get("predicted_per_second")})
                print(profile, job["id"], first, round(elapsed), flush=True)
    finally:
        process.terminate()
        process.wait(timeout=15)
    speeds = [row["output_tokens_per_second"] for row in rows if row["output_tokens_per_second"] is not None]
    return {"profile": profile, "runtime": "llama.cpp b12242 CPU", "hardware": hardware,
            "platform": platform.system(), "threads": 4, "quantization": "Q4_K_M", "n": len(rows),
            "top1_accuracy": mean(row["top1_correct"] for row in rows), "schema_valid": mean(row["schema_valid"] for row in rows),
            "latency_p95_ms": percentile([row["latency_ms"] for row in rows], .95),
            "mean_output_tokens_per_second": mean(speeds) if speeds else None,
            "mean_tokens": mean(row["tokens"] for row in rows), "billed_usd": 0, "rows": rows}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--server", type=Path, required=True)
    parser.add_argument("--small", type=Path, required=True)
    parser.add_argument("--large", type=Path, required=True)
    parser.add_argument("--hardware", required=True)
    parser.add_argument("--port", type=int, default=8089)
    args = parser.parse_args()
    gold = json.loads((ROOT / "evals/datasets/local_dev.json").read_text(encoding="utf-8"))
    subset = [row for row in gold if row["scenario"] == "standard"]
    output = ROOT / "evals/results/open_models.json"
    reports = []
    for label, model in (("Qwen2.5 0.5B Instruct", args.small), ("Qwen2.5 1.5B Instruct", args.large)):
        reports.append(run(label, model.resolve(), args.server.resolve(), subset, args.port, args.hardware))
        output.write_text(json.dumps(reports, indent=2) + "\n", encoding="utf-8")
