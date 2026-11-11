"""Run deterministic local R&D studies and persist measured rows, traces, and summaries."""
import argparse
import asyncio
import csv
import json
import logging
import math
import os
from statistics import mean
from time import perf_counter
from uuid import uuid4

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.store.memory import InMemoryStore
from langgraph.types import Command

from agent.graphs.bid_graph import build_bid_graph
from agent.settings import ROOT
from evals.runners import ablation, decision_eval, rag_eval, tool_eval
from gigsim.service import JOBS, redact
from rag.ingest.loaders import load_fixtures
from rag.verify import verify_claims


def percentile(data, p):
    values = sorted(data)
    return round(values[max(0, math.ceil(p * len(values)) - 1)], 4) if values else None


def ratios(tp, fp, fn):
    precision = tp/(tp+fp) if tp+fp else 0
    recall = tp/(tp+fn) if tp+fn else 0
    return {"precision": precision, "recall": recall, "f1": 2*precision*recall/(precision+recall) if precision+recall else 0}


def write(name, data):
    (ROOT / f"evals/results/{name}.json").write_text(json.dumps(data, indent=2, ensure_ascii=False)+"\n", encoding="utf-8")


async def run(gold):
    graph = build_bid_graph(InMemorySaver(), InMemoryStore())
    outcomes = []
    traces = {}
    semaphore = asyncio.Semaphore(4)

    async def one(row, persona, kind):
        async with semaphore:
            trace = uuid4().hex
            initial = {"user_id": f"eval-{trace}", "trace_id": trace, "job_id": row["job_id"],
                       "persona": persona, "floor": 180, "weekly_limit": 100,
                       "strategy": "plan_first" if row["job_id"] == "GB-001" else "evidence_first",
                       "include_attested_skills": kind != "excerpt_only",
                       "rag_variant": "v0" if kind == "v0" else "v2"}
            cfg = {"configurable": {"thread_id": trace}, "recursion_limit": 38}
            start = perf_counter()
            state = await graph.ainvoke(initial, cfg)
            analysis_ms = (perf_counter()-start)*1000
            approved = state["approval_status"] == "pending"
            if approved and kind in {"single_persona", "excerpt_only", "v0"}:
                state = await graph.ainvoke(Command(resume={"action": "approve"}), cfg)
            proposal_ms = (perf_counter()-start)*1000 if approved else None
            if kind == "single_persona" and row["job_id"] in {"GB-001","GB-003","GB-004"}:
                traces[row["job_id"]] = {"job_id": row["job_id"], "trace_id": trace, "events": state["event_stats"],
                    "decision": state["decision"], "risk": state["risk_report"], "outcome": state.get("outcome"),
                    "claim_verification": state.get("claim_verification")}
            return {"job_id": row["job_id"], "persona": row["persona"], "scenario": row["scenario"], "arm": kind,
                    "gold_bid": row["bid"], "bid": state["decision"]["action"] == "bid",
                    "fit": state["fit_report"]["score"], "selected_persona": state["selected_persona"],
                    "gold_scam": row["scam"], "scam": bool(set(state["risk_report"]["flags"]) & {"off_platform","unpaid_work"}),
                    "injection": row["injection"], "injection_detected": "injection" in state["risk_report"]["flags"],
                    "fair": None if not row["fair_price"] or "price_quote" not in state else
                    row["fair_price"][0] <= state["price_quote"]["amount"] <= row["fair_price"][1],
                    "latency_ms": analysis_ms, "proposal_ms": proposal_ms, "tokens": state.get("tokens",0), "usd": 0,
                    "unsupported_before": state.get("claims_removed",0),
                    "unsupported_after": sum(item["status"] != "supported" for item in verify_claims(
                        state.get("proposal_draft", {}).get("cover_letter", ""), state.get("evidence", []), state["job"]["title"])),
                    "stage": (state.get("outcome") or {}).get("stage")}

    outcomes = await asyncio.gather(*(one(row, row["persona"], "single_persona") for row in gold))
    agency_gold = [row for row in gold if row["bid"]]
    agency = await asyncio.gather(*(one(row, persona, kind) for row in agency_gold
                                   for persona, kind in [("agency","agency"),("ai","ai_only")]))
    if traces:
        for name, value in traces.items():
            write(f"trace-{name.lower()}", redact(value))
    excerpts = await asyncio.gather(*(one(row, row["persona"], "excerpt_only") for row in agency_gold))
    cosine_baseline = await asyncio.gather(*(one(row, row["persona"], "v0") for row in gold))
    return outcomes, agency, excerpts, cosine_baseline


def summary(rows):
    count = lambda key, gold: ratios(sum(row[key] and row[gold] for row in rows),
                         sum(row[key] and not row[gold] for row in rows), sum(not row[key] and row[gold] for row in rows))
    sent = [row for row in rows if row["stage"]]
    proposal = [row["proposal_ms"] for row in rows if row["proposal_ms"] is not None]
    prices = [row["fair"] for row in rows if row["fair"] is not None]
    return {"jobs": len(rows), "bid": count("bid","gold_bid"), "scam": count("scam","gold_scam"),
            "price_in_band": mean(prices) if prices else None, "submitted": len(sent),
            "reply_rate": mean(row["stage"] in {"replied","hired"} for row in sent) if sent else None,
            "hire_rate": mean(row["stage"] == "hired" for row in sent) if sent else None,
            "analysis_ms_p50": percentile([row["latency_ms"] for row in rows], .5),
            "analysis_ms_p95": percentile([row["latency_ms"] for row in rows], .95),
            "proposal_ms_p50": percentile(proposal,.5), "proposal_ms_p95": percentile(proposal,.95),
            "unsupported_before": sum(row["unsupported_before"] for row in rows),
            "unsupported_after": sum(row["unsupported_after"] for row in rows),
            "tokens": sum(row["tokens"] for row in rows), "usd": 0}


def main():
    logging.getLogger("mcp").setLevel(logging.WARNING)
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int)
    parser.add_argument("--gate", action="store_true")
    args = parser.parse_args()
    gold = json.loads((ROOT / "evals/datasets/local_dev.json").read_text(encoding="utf-8"))
    if args.limit:
        gold = gold[:args.limit]
    rag = rag_eval.retrieval(JOBS, gold)
    graph, agency, excerpts, cosine_baseline = asyncio.run(run(gold))
    tools = tool_eval.benchmark()
    docs = load_fixtures("evidence.json")
    baselines = {kind: [{**row, **decision_eval.baseline(JOBS[row["job_id"]], [doc for doc in docs if doc["persona"] == row["persona"]], kind)}
                        for row in gold[:50]] for kind in ("single_rule","staged_rules")}
    failures = [{"job_id": row["job_id"], "scenario": row["scenario"],
                 "baseline_bid": row["bid"], "gold_bid": row["scenario"] in {"standard","pilot"},
                 "graph_bid": next(item["bid"] for item in graph if item["job_id"] == row["job_id"])}
                for row in baselines["single_rule"] if row["bid"] != (row["scenario"] in {"standard","pilot"})]
    architecture = {kind: {"jobs": len(values), "accuracy": mean(row["bid"] == (row["scenario"] in {"standard","pilot"}) for row in values),
                           "p95_ms": percentile([row["ms"] for row in values],.95)}
                    for kind,values in baselines.items()}
    architecture["langgraph"] = {"jobs": len(graph[:50]), "accuracy": mean(row["bid"] == row["gold_bid"] for row in graph[:50]),
                                "p95_ms": percentile([row["latency_ms"] for row in graph[:50]], .95)}
    injection = [row for row in graph[:50] if row["injection"]]
    before = sum(row["injection_decision"] for row in baselines["single_rule"])
    rows = {"mode": "Local deterministic simulator; metrics are not instructor GigSim or hidden tests",
            "summary": summary(graph), "excerpt_only": summary(excerpts), "cosine_end_to_end": summary(cosine_baseline), "rag": ablation.report(rag), "architecture": architecture,
            "tool_design": {kind: {"tasks": len(subset), "tool_accuracy": mean(row["tool_correct"] for row in subset),
                                   "tool_and_argument_accuracy": mean(row["argument_correct"] for row in subset),
                                   "mean_input_words": mean(row["input_words"] for row in subset)}
                            for kind in ("fine","coarse","described")
                            if (subset := [row for row in tools if row["profile"] == kind])},
            "by_persona": {persona: summary([row for row in graph if row["persona"] == persona])
                           for persona in {row["persona"] for row in graph}},
            "injection": {"n": len(injection), "unsafe_reference_bids": before, "guarded_bids": sum(row["bid"] for row in injection)},
            "extension": {kind: {"n": len(subset), "eligible": sum(row["bid"] for row in subset),
                                 "correct_route": sum(row["selected_persona"] == row["persona"] for row in subset),
                                 "p95_ms": percentile([row["latency_ms"] for row in subset], .95)}
                          for kind in ("agency","ai_only") if (subset := [row for row in agency if row["arm"] == kind])},
            "failures": failures, "provenance": {"rag_reranker": "local pair-feature fallback",
                                                  "model_profile": os.getenv("MODEL_PROFILE","open") if os.getenv("OLLAMA_BASE_URL") else "extractive fallback"}}
    write("summary", rows)
    for name, values in (("job_metrics",graph),("retrieval",rag),("tool_tasks",tools),("agency",agency),("excerpt_only",excerpts),("cosine_end_to_end",cosine_baseline)):
        write(name, values)
        with (ROOT / f"evals/results/{name}.csv").open("w", newline="", encoding="utf-8") as file:
            output = csv.DictWriter(file, fieldnames=list(values[0]))
            output.writeheader()
            output.writerows(values)
    print(json.dumps({"summary": rows["summary"], "architecture": architecture, "extension": rows["extension"]}, indent=2))
    if args.gate and (rows["summary"]["bid"]["f1"] < .85 or rows["summary"]["unsupported_after"] > 0):
        raise SystemExit("Evaluation gate failed")


if __name__ == "__main__":
    main()


