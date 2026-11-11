from json import dumps

from agent.settings import ROOT
from apps.api.main import app

if __name__ == "__main__":
    (ROOT / "docs/openapi.json").write_text(dumps(app.openapi(), indent=2) + "\n", encoding="utf-8")
