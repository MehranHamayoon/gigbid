"""Build the GigBid design review from the committed local evaluation."""
import json
import os
import sys
from html import escape
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

ROOT = Path(__file__).resolve().parents[1]
R = json.loads((ROOT / "evals/results/summary.json").read_text(encoding="utf-8"))
MODELS = json.loads((ROOT / "evals/results/open_models.json").read_text(encoding="utf-8"))
K = json.loads((ROOT / "data/sample/market_statistics.json").read_text(encoding="utf-8"))
GREEN = colors.HexColor("#154736")
INK = colors.HexColor("#162d28")
MUTED = colors.HexColor("#4d665c")
LINE = colors.HexColor("#dbe7dd")
SOFT = colors.HexColor("#eef5ed")
WIDTH = A4[0] - 36 * mm

styles = {
    "hero": ParagraphStyle("hero", fontName="Helvetica-Bold", fontSize=34, leading=36, textColor=GREEN, spaceAfter=12),
    "h1": ParagraphStyle("h1", fontName="Helvetica-Bold", fontSize=25, leading=28, textColor=GREEN, spaceAfter=12),
    "h2": ParagraphStyle("h2", fontName="Helvetica-Bold", fontSize=12, leading=15, textColor=GREEN, spaceBefore=10, spaceAfter=5),
    "p": ParagraphStyle("p", fontName="Helvetica", fontSize=10.2, leading=14.9, textColor=INK, spaceAfter=8, alignment=TA_LEFT),
    "lede": ParagraphStyle("lede", fontName="Helvetica", fontSize=13, leading=18, textColor=MUTED, spaceAfter=16),
    "eyebrow": ParagraphStyle("eyebrow", fontName="Helvetica-Bold", fontSize=8.2, leading=11, textColor=MUTED, spaceAfter=8),
    "source": ParagraphStyle("source", fontName="Helvetica", fontSize=8, leading=11, textColor=MUTED, spaceBefore=4, spaceAfter=8),
    "cell": ParagraphStyle("cell", fontName="Helvetica", fontSize=8.6, leading=11.2, textColor=INK),
    "head": ParagraphStyle("head", fontName="Helvetica-Bold", fontSize=8.2, leading=10.6, textColor=colors.white),
}
story = []


def add(text, style="p"):
    story.append(Paragraph(escape(text), styles[style]))


def section(number, title):
    story.append(PageBreak())
    add(number, "eyebrow")
    add(title, "h1")


def table(header, rows, widths):
    data = [[Paragraph(escape(str(item)), styles["head"]) for item in header]]
    data.extend([[Paragraph(escape(str(item)), styles["cell"]) for item in row] for row in rows])
    item = Table(data, colWidths=[WIDTH * width for width in widths], repeatRows=1, hAlign="LEFT")
    item.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), GREEN), ("ROWBACKGROUNDS", (0,1), (-1,-1), [SOFT, colors.white]),
        ("LINEBELOW", (0,0), (-1,0), 0.5, GREEN), ("LINEBELOW", (0,1), (-1,-1), 0.35, LINE),
        ("VALIGN", (0,0), (-1,-1), "TOP"), ("LEFTPADDING", (0,0), (-1,-1), 8),
        ("RIGHTPADDING", (0,0), (-1,-1), 8), ("TOPPADDING", (0,0), (-1,-1), 7),
        ("BOTTOMPADDING", (0,0), (-1,-1), 7),
    ]))
    story.append(item)
    story.append(Spacer(1, 7))


def source(text):
    add("Evidence   " + text, "source")


def percentage(x):
    return f"{100*x:.1f}%" if x is not None else "N/A"


def ms(x):
    return f"{x:.3f} ms" if x is not None else "N/A"


def footer(canvas, doc):
    width, height = A4
    canvas.setFillColor(GREEN)
    canvas.rect(0, height - 5 * mm, width, 5 * mm, stroke=0, fill=1)
    canvas.setStrokeColor(LINE)
    canvas.line(18*mm, 15*mm, width-18*mm, 15*mm)
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(MUTED)
    canvas.drawString(18*mm, 10*mm, "FAST-NUCES Islamabad  /  AI-4016  /  GigBid")
    canvas.drawRightString(width-18*mm, 10*mm, f"{doc.page:02d}")


def main(path):
    summary = R["summary"]
    add("AI-4016  /  ASSIGNMENT II  /  ENGINEERING DESIGN REVIEW", "eyebrow")
    story.append(Spacer(1, 16))
    add("GigBid", "hero")
    add("A multi-agent copilot for evidence-grounded freelance bids", "lede")
    add(os.getenv("GIGBID_REPORT_STUDENT", "AI-4016 student"), "h2")
    add("FAST School of Computing, FAST-NUCES Islamabad  |  November 2026", "source")
    story.append(Spacer(1, 13))
    table(["Local dev jobs", "Bid-or-skip F1", "Proposal p95", "Model API spend"], [[summary["jobs"],
        percentage(summary["bid"]["f1"]), ms(summary["proposal_ms_p95"]), f'USD {summary["usd"]}']],
        [.25,.25,.25,.25])
    add("Problem and constraints", "h2")
    add("A freelancer needs to decide which listings deserve time and paid Connects. GigBid assesses risk and fit, proposes a price, and produces a reviewable cover letter grounded in a portfolio. The freelancer controls the external action. The same approval mechanism governs client replies.")
    add("The system targets p95 at or below 3 seconds for analysis and 15 seconds for an approved proposal, excluding human think time, with zero billed model API spend in the local profile. CPU time, hosting and model downloads are separate costs.")
    add("Local results use a student-built simulator and three fictional portfolios. The brief describes supplied services and labels. The classroom clarification called for building the simulator using the starter kit. A Kaggle pricing aggregate supplies one real-data signal.")
    source("agent/config.yaml · evals/results/summary.json · docs/DATA_CARD.md")
    add("Primary finding", "h2")
    add(f'The same retriever produced {percentage(R["excerpt_only"]["reply_rate"])} simulator replies when the writer quoted only the case study, and {percentage(summary["reply_rate"])} when it also cited exact skill tags. This isolates a writing and verification change under a synthetic client that rewards explicit skill mentions.')
    source("evals/results/excerpt_only.csv · evals/results/job_metrics.csv")

    section("01  /  SYSTEM DESIGN", "Two durable graphs")
    add("The API authenticates the tenant and queues a run. The worker executes the graph, persists progress and streams redacted events. Marketplace, Portfolio and Workspace capabilities are MCP tools with per-role allowlists.")
    table(["Graph", "Execution path"], [
        ["Bid", "Scout -> Send to Analyst, Risk Assessor and Fit Matcher in parallel -> join and decide skip, watch or bid."],
        ["Draft", "Pricing -> Writer -> claim verifier -> Critic. The Critic can return the draft for two revisions. Compliance can block it."],
        ["Approval", "Preview -> interrupt -> reject or recheck the approved text and current evidence -> idempotent marketplace write."],
        ["Conversation", "Liaison reads the inbound thread -> classify question, negotiation, interview or scam -> draft and preview -> interrupt -> approved response."]
    ], [.21,.79])
    add("Why these responsibilities are separate", "h2")
    add("Analyst normalizes the brief. Risk joins posting signals with client history. Fit maps each required skill to a portfolio ID. Pricing balances the user's floor, client spend and posted range. Writer constructs draft and screening answers. Verification tests claims. Critic checks specificity and structure. Compliance checks the policy. Liaison classifies and handles the follow-up.")
    add("State, traces and memory", "h2")
    add("Checkpoint state belongs to a job or conversation. The event ledger records node times and the simulator audit captures marketplace tool arguments and results after redaction. Two tenant-scoped LangGraph memory namespaces hold repeated style edits and positive approved outcomes. Promotion requires three shorter approved edits for a style rule, or a meaningful recorded stage for an outcome.")
    add("One marketplace port", "h2")
    add("The simulator and official Upwork adapters sit behind the same port. The simulator offers local transactional writes. The Upwork adapter maps configured tools through Streamable HTTP and limits external actions to drafts. The reviewer deployment is scoped to simulation.")
    source("docs/ARCHITECTURE.md · agent/graphs/ · agent/memory/store.py · mcp_servers/")

    section("02  /  R&D QUESTION A", "Tool granularity and descriptions")
    add("Hypothesis. Descriptions with common intent vocabulary should improve exact tool routing. A coarse surface may identify the right domain while leaving the operation ambiguous.")
    add("Setup. The lexical proxy received forty requests covering ten operations, with one case ID per request. The profiles changed the candidate descriptions and granularity. The coarse arm receives domain credit when it picks the correct domain. An exact tool and argument match requires the actual operation and the right ID.")
    t = R["tool_design"]
    table(["Surface", "Tasks", "Tool or domain", "Exact call", "Mean input words"], [
        [label, item["tasks"], percentage(item["tool_accuracy"]), percentage(item["tool_and_argument_accuracy"]), item["mean_input_words"]]
        for label, item in [("Fine tool names",t["fine"]),("Coarse domains",t["coarse"]),("Described tools",t["described"])]
    ], [.25,.11,.23,.19,.22])
    add("Interpretation", "h2")
    add("The richer description recovered wording the bare names missed, at the cost of a larger description surface. The described arm shares vocabulary with the requests by design. Treat the result as an interface ablation, with word count as an input-size proxy. The LLM tool-call accuracy and token comparison remain unmeasured.")
    add("Operational consequences", "h2")
    add("The Marketplace server declares write schemas, preview flags and idempotency hints. A signed proof binds the approved action to a tenant and exact payload. Portfolio offers read tools, resource templates and a screening-question prompt. Workspace offers mock availability and draft capabilities. A graph role can call only the tools listed for that role.")
    source("evals/results/tool_tasks.csv · tests/contract/tool_schemas.json · docs/TOOLS.md")

    section("03  /  R&D QUESTION B", "Retrieval and claim grounding")
    add("Hypothesis. BM25 fusion improves evidence retrieval for exact tool names. Corrective retrieval should help at the boundary where a requirement has little support.")
    rows = []
    names = {"v0":"V0 cosine baseline","v1":"V1 requirement decomposition","v2":"V2 hybrid, shipped",
             "v3":"V3 pair-feature rerank","v4":"V4 outcome boost","v8":"V8 corrective graph"}
    for key, name in names.items():
        x = R["rag"][f"{key}/all"]
        rows.append([name, percentage(x["recall5"]), f'{x["mrr"]:.3f}', f'{x["ndcg10"]:.3f}', ms(x["ms"])])
    table(["Variant", "Recall@5", "MRR", "nDCG@10", "Mean retrieval"], rows, [.33,.16,.14,.16,.21])
    add("Ablation and decision", "h2")
    add("The cosine-only and hybrid arms isolate the addition of a lexical ranker and fusion. Corrective search marginally increases recall over V2 and takes longer. V4 ties V2 on overall recall and nDCG. The shipped V2 hybrid avoids that extra branch on every job. V3's measured CPU fallback uses query-document features. The optional BGE cross-encoder was configured separately.")
    personas = ["ai","web","data"]
    table(["Persona", "V0 Recall@5", "V2 Recall@5", "Bid F1", "Fair price"], [
        [name, percentage(R["rag"][f"v0/{key}"]["recall5"]), percentage(R["rag"][f"v2/{key}"]["recall5"]),
         percentage(R["by_persona"][key]["bid"]["f1"]), percentage(R["by_persona"][key]["price_in_band"])]
        for key, name in zip(personas, ["AI / ML","Full-stack","Data analyst"])
    ], [.25,.20,.20,.16,.19])
    add("Claim and outcome evaluation", "h2")
    cosine = R["cosine_end_to_end"]
    table(["End-to-end arm", "Unsupported / proposal", "Reply rate", "Proposal p95", "API spend"], [
        ["V0", cosine["unsupported_after"]/cosine["submitted"], percentage(cosine["reply_rate"]), ms(cosine["proposal_ms_p95"]), "USD 0"],
        ["V2", summary["unsupported_after"]/summary["submitted"], percentage(summary["reply_rate"]), ms(summary["proposal_ms_p95"]), "USD 0"]
    ], [.21,.25,.15,.21,.18])
    add(f'{summary["submitted"]} generated proposals were submitted in the local approved arm. Unsupported claims before and after verification were {summary["unsupported_before"]} and {summary["unsupported_after"]}. The forged-claim test shows the verifier can reject an unsupported statement with a valid citation. The two retrieval arms tied on replies despite different recall. V2 outcomes were {percentage(summary["reply_rate"])} replied or hired and {percentage(summary["hire_rate"])} hired. An LLM judge and blind human panel are outstanding.')
    source("evals/results/retrieval.csv · evals/results/summary.json · tests/unit/test_verify.py")

    section("04  /  R&D QUESTION C", "What the graph adds")
    add("Hypothesis. An explicit risk and fit join reduces unsafe and partial-fit bids. A direct rule has lower overhead.")
    names = {"single_rule":"Direct rule","staged_rules":"Staged rule comparator","langgraph":"Hand-built LangGraph"}
    table(["Arm", "Jobs", "Bid accuracy", "p95"], [
        [names[key], item["jobs"], percentage(item["accuracy"]), ms(item["p95_ms"])]
        for key, item in R["architecture"].items()
    ], [.42,.13,.23,.22])
    add("The staged rule matched graph accuracy on this subset. The raw rule timing excludes MCP, drafting and persistence, so the p95 values have different boundaries. The ReAct and prebuilt supervisor comparisons remain outstanding. The direct rule was fastest on ordinary cases and falsely bid on a set of injected and partial-fit cases.")
    add("Crash and resume", "h2")
    add("The integration test pauses GB-001, closes the graph runtime, reopens the checkpoint store and resumes the pending approval. The simulator creates one proposal, deducts six Connects once, and records one inbound reply. A second approval request is rejected. The idempotency test separately repeats a successful simulator write and confirms the existing result is returned.")
    add("What the trace shows", "h2")
    add("GB-001 uses the plan-first test strategy, takes a Critic revision, verifies its claims, pauses and dispatches. GB-003 skips unpaid work and off-platform contact. GB-004 skips a planted instruction. Public traces are restricted to these synthetic runs.")
    source("evals/results/trace-gb-001.json · trace-gb-003.json · trace-gb-004.json · tests/integration/test_bid_workflow.py")
    add("Two open-weight model configurations", "h2")
    add("Each Qwen model ranks shuffled candidate excerpts for the same twelve standard development jobs. The local CPU runner uses llama.cpp b12242, four threads, Q4_K_M, and an AMD Ryzen 5 5600H. Both arms returned parseable output and incurred zero billed API cost.")
    table(["Model", "Top-1 accuracy", "p95", "Output tokens/s"], [
        [row["profile"], percentage(row["top1_accuracy"]), ms(row["latency_p95_ms"]), f'{row["mean_output_tokens_per_second"]:.1f}']
        for row in MODELS
    ], [.40,.18,.21,.21])
    add("The 1.5B configuration is the optional local Writer default. The reviewer service uses the measured extractive fallback and keeps exact evidence as the source of each claim.")
    source("evals/results/open_models.json · evals/runners/model_eval.py · agent/config.yaml")

    section("05  /  EXTENSION AND CHANGE REQUEST", "Routing for a small agency")
    ext = R["extension"]
    table(["Workspace", "Eligible jobs", "Correctly routed", "Analysis p95"], [
        ["AI/ML only", ext["ai_only"]["eligible"], ext["ai_only"]["correct_route"], ms(ext["ai_only"]["p95_ms"])],
        ["Agency", ext["agency"]["eligible"], ext["agency"]["correct_route"], ms(ext["agency"]["p95_ms"])]
    ], [.34,.21,.24,.21])
    add("The X1 route compares coverage across all three portfolios and chooses a same-category portfolio on ties. The result measures routing against fixture labels, with extra retrieval work. Cross-functional projects and overlapping portfolios remain a harder test. One reviewer approves all actions in this version.")
    source("evals/results/agency.csv · docs/EXTENSION.md")
    add("Policy change drill", "h2")
    add("The classroom package did not include the dated update described in the brief. The local drill changes the maximum per-proposal Connects from fourteen to five in a temporary YAML policy. GB-001 costs six and routes to Skip. The simulator write path also enforces the configured cap. The test exercises a configuration-only change and leaves the repository policy intact.")
    source("data/policy_pack/local.yaml · tests/integration/test_bid_workflow.py")
    add("Pricing and dataset provenance", "h2")
    add(f'Kaggle version 1 supplied {K["examined"]:,} postings. The filter retained {K["fixed_price_in_range"]:,} fixed-price budgets and calculated a USD {K["median"]} median. GigBid uses a five-percent market prior and gives more weight to simulated client spend and the posted range. Historical advertised prices are an imperfect guide to actual freelancer earnings.')
    source("data/sample/market_statistics.json · rag/ingest/kaggle.py · docs/DATA_CARD.md")

    section("06  /  FAILURE ANALYSIS", "What failed on local dev jobs")
    add("The following failed cases came from the direct-rule comparator on the same local dev fixture. Injection and partial fit are distinct causes. The direct rule used any matching skill and a positive budget.")
    failures = R["failures"][:12]
    table(["Job", "Failure class", "Tried", "Graph"], [
        [row["job_id"], "Planted instruction" if row["scenario"] == "injection" else "Partial fit",
         "Run configured risk scan before routing" if row["scenario"] == "injection" else "Require portfolio coverage across skills",
         "Bid" if row["graph_bid"] else "No bid"]
        for row in failures
    ], [.15,.24,.45,.16])
    add("Proposal stage failure", "h2")
    add("A separate paired comparison exposed relevant evidence whose wording missed the simulated client's preferred skill. The change added an independently verified skill-metadata citation. The two arms use the same retrieval and prices. This fixture makes explicit skill strings unusually influential.")
    source("evals/results/summary.json · evals/results/excerpt_only.csv · evals/results/job_metrics.csv")

    section("07  /  SAFETY AND OPERATIONS", "Budgets, guardrails and open work")
    table(["Metric", "Declared budget", "Measured p50", "Measured p95"], [
        ["Analysis", "3 seconds p95", ms(summary["analysis_ms_p50"]), ms(summary["analysis_ms_p95"])],
        ["Approved proposal", "15 seconds p95", ms(summary["proposal_ms_p50"]), ms(summary["proposal_ms_p95"])],
        ["Billed model API cost", "USD 0", "USD 0", "USD 0"]
    ], [.28,.25,.23,.24])
    add(f'The timing includes local MCP and graph execution. The proposal timer resumes automatically after the test interrupt, with no user wait. The extractive fallback used {summary["tokens"]} model tokens. Early skips avoid running pricing and drafting for high-risk and low-fit jobs.')
    add("Guardrails", "h2")
    injection = R["injection"]
    add(f'The direct rule would bid on {injection["unsafe_reference_bids"]} of {injection["n"]} planted-instruction cases. The guarded graph bid on {injection["guarded_bids"]}. These counts measure decisions on the first fifty fixtures. No reference arm attempted a marketplace write. A keyword detector can miss paraphrases. The approval signature and tool allowlists still guard writes. Logs mask common emails and phone/payment number patterns. OAuth token values are encrypted.')
    add("Verification boundary", "h2")
    add("The completed evidence is local development data, MCP protocol snapshots, browser workflow tests, and persisted approval tests. The instructor runs the hidden tests after the deadline. Upwork OAuth, persistent hosting across restarts, blind human review, and instructor hidden-set latency and cost are outside the measured results.")
    add("Résumé", "h2")
    add(f'Built a LangGraph and MCP freelance copilot with resumable approval and idempotent simulator writes. Measured {percentage(R["rag"]["v2/all"]["recall5"])} hybrid evidence Recall@5 across {summary["jobs"]} synthetic jobs.')
    source("evals/results/summary.json · tests/integration/test_bid_workflow.py · docs/RUNBOOK.md")
    document = SimpleDocTemplate(str(path), pagesize=A4, title="GigBid - R&D Engineering Design Review",
                                 author="Mehran Hamayoon", leftMargin=18*mm, rightMargin=18*mm,
                                 topMargin=18*mm, bottomMargin=21*mm)
    document.build(story, onFirstPage=footer, onLaterPages=footer)


if __name__ == "__main__":
    destination = Path(sys.argv[1]).resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)
    main(destination)



