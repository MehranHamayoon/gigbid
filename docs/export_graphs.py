from agent.graphs.bid_graph import build_bid_graph
from agent.graphs.conversation_graph import build_conversation_graph
from agent.settings import ROOT

if __name__ == "__main__":
    for name, build in (("bid", build_bid_graph), ("conversation", build_conversation_graph)):
        (ROOT / f"docs/images/{name}.mmd").write_text(build().get_graph().draw_mermaid() + "\n", encoding="utf-8")
