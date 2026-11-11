# Portfolio MCP server

GigBid Portfolio exposes grounded, read-only evidence for a freelancer's case studies, proposals, and documented skills. The package includes synthetic examples. The server runs over stdio by default.

```sh
python -m pip install .
gigbid-portfolio
```

For a desktop MCP host, use the executable path of `gigbid-portfolio` in the activated Python environment. After the GitHub repository is public, the equivalent one-shot install is:

```sh
uvx --from git+https://github.com/MehranHamayoon/gigbid.git gigbid-portfolio
```

For Inspector, run `npx @modelcontextprotocol/inspector python -m mcp_servers.portfolio.server` from the repository root. List tools, run `search_evidence` with a requirement such as "classification with scikit-learn", and inspect a result's exact text, source, date and skills. Resource URIs include `portfolio://case/ai-1-case` and `portfolio://proposal/ai-1-proposal`. The `answer_screening_question` prompt gives an evidence-first starting point. Avoid exposing a tenant's private upload store to a public MCP host.
