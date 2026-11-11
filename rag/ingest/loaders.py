from contextlib import closing
from hashlib import sha256
from io import BytesIO
from pathlib import Path
import json
import re

from pypdf import PdfReader

from agent.settings import ROOT
from agent.storage import encode, open_db, utc


def load_fixtures(filename):
    return json.loads((ROOT / "data/personas" / filename).read_text(encoding="utf-8"))


def db():
    conn = open_db("portfolio.sqlite")
    conn.execute("CREATE TABLE IF NOT EXISTS evidence (tenant TEXT, id TEXT, body TEXT, PRIMARY KEY(tenant,id))")
    return conn


def load_evidence(persona="ai", tenant=""):
    with closing(db()) as conn:
        additions = [json.loads(row[0]) for row in conn.execute("SELECT body FROM evidence WHERE tenant=?", (tenant,))]
    return [row for row in [*load_fixtures("evidence.json"), *additions] if row["persona"] == persona]


def ingest(tenant, persona, filename, content, skills, kind, industry, outcome=None):
    extension = Path(filename).suffix.casefold()
    if extension == ".pdf":
        reader = PdfReader(BytesIO(content))
        if len(reader.pages) > 40:
            raise ValueError("Use a portfolio PDF with at most 40 pages")
        text = "\n".join(page.extract_text() or "" for page in reader.pages)
    elif extension in {".txt", ".md", ".py", ".ts", ".tsx", ".js", ".sql", ".json"}:
        text = content.decode("utf-8-sig")
    else:
        raise ValueError("Upload a PDF or a supported text or source file")
    normalized = re.sub(r"\s+", " ", text).strip()
    if len(normalized) < 20:
        raise ValueError("The file contains too little extractable text")
    project = sha256(content).hexdigest()[:12]
    chunks = []
    for index in range(0, min(len(normalized), 15000), 750):
        item = {"id": f"upload-{project}-{index//750}", "persona": persona, "project": project,
                "type": kind, "title": Path(filename).name, "skills": skills,
                "date": utc()[:10], "industry": industry, "text": normalized[index:index + 850],
                "source": "User-uploaded evidence", "outcome": outcome}
        chunks.append(item)
    with closing(db()) as conn, conn:
        conn.executemany("INSERT OR REPLACE INTO evidence VALUES (?,?,?)",
                         [(tenant, item["id"], encode(item)) for item in chunks])
    return chunks


def delete(tenant, evidence_id):
    with closing(db()) as conn, conn:
        return bool(conn.execute("DELETE FROM evidence WHERE tenant=? AND id=?", (tenant, evidence_id)).rowcount)
