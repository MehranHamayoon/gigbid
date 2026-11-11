"""Transactional marketplace simulator. All records represent fictional activity."""
import json
from contextlib import closing

from agent.settings import ROOT, policy
from agent.storage import encode, open_db, utc


def load(name):
    return json.loads((ROOT / f"data/sample/{name}.json").read_text(encoding="utf-8"))


JOBS = {row["id"]: row for row in load("simulator_jobs")}
CLIENTS = {row["id"]: row for row in load("simulator_clients")}
MARKET_MEDIAN = load("market_statistics")["median"]


def search(query: str = "", category: str = "") -> list[dict]:
    query = query.strip().casefold()
    return [job for job in JOBS.values() if (not category or job["category"] == category)
            and (not query or query in f'{job["title"]} {job["description"]} {" ".join(job["skills"])}'.casefold())]


def db():
    connection = open_db("marketplace.sqlite")
    connection.executescript("""
        CREATE TABLE IF NOT EXISTS actions (
          user_id TEXT, key TEXT, tool TEXT, payload TEXT, result TEXT,
          PRIMARY KEY(user_id, key));
        CREATE TABLE IF NOT EXISTS proposals (
          user_id TEXT, job_id TEXT, body TEXT, amount INTEGER, stage TEXT,
          connects INTEGER, updated TEXT, PRIMARY KEY(user_id, job_id));
        CREATE TABLE IF NOT EXISTS messages (
          id TEXT, user_id TEXT, job_id TEXT, direction TEXT, body TEXT, created TEXT,
          PRIMARY KEY(user_id, id));
        CREATE TABLE IF NOT EXISTS audit (
          id INTEGER PRIMARY KEY, created TEXT, user_id TEXT, trace_id TEXT,
          tool TEXT, payload TEXT, result TEXT);
    """)
    return connection


def redact(value):
    import re

    if isinstance(value, dict):
        return {key: redact(item) for key, item in value.items()}
    if isinstance(value, list):
        return [redact(item) for item in value]
    if isinstance(value, str):
        value = re.sub(r"[\w.+-]+@[\w.-]+\.[a-zA-Z]{2,}", "[email]", value)
        return re.sub(r"(?<!\w)\+?\d[\d ().-]{7,}\d(?!\w)", "[number]", value)
    return value


def audit(user_id, trace_id, tool, payload, result):
    with closing(db()) as conn, conn:
        conn.execute("INSERT INTO audit(created,user_id,trace_id,tool,payload,result) VALUES (?,?,?,?,?,?)",
                     (utc(), user_id, trace_id, tool, encode(redact(payload)), encode(redact(result))))


def balance(user_id, conn=None):
    if conn is None:
        with closing(db()) as connection:
            return balance(user_id, connection)
    total = conn.execute("SELECT COALESCE(SUM(connects),0) FROM proposals WHERE user_id=?", (user_id,)).fetchone()[0]
    week = conn.execute("""SELECT COALESCE(SUM(connects),0) FROM proposals
                         WHERE user_id=? AND julianday(updated)>=julianday('now','-7 days')""",
                        (user_id,)).fetchone()[0]
    return {"remaining": 100 - total, "spent": total, "week_spent": week}


def proposals(user_id):
    with closing(db()) as conn:
        rows = conn.execute("""SELECT job_id,amount,stage,connects,updated FROM proposals
                            WHERE user_id=? ORDER BY updated DESC""", (user_id,))
        return [{**dict(row), "title": JOBS[row["job_id"]]["title"]} for row in rows]


def messages(user_id, job_id=""):
    with closing(db()) as conn:
        return [dict(row) for row in conn.execute("""SELECT id,job_id,direction,body,created FROM messages
                WHERE user_id=? AND (?='' OR job_id=?) ORDER BY created,id""", (user_id, job_id, job_id))]


def predicted_outcome(job, client, body, amount):
    match = client["preferred_skill"].casefold() in body.casefold()
    eligible = client["payment_verified"] and match and amount <= client["ceiling"]
    tailored = job["title"].casefold() in body.casefold()
    return "hired" if eligible and tailored and amount < client["typical_spend"] else "replied" if eligible else "submitted"


def write(tool, user, trace_id, key, payload, dry_run, weekly_limit):
    job = JOBS[payload["job_id"]]
    connects = job["connects"] if tool == "submit_proposal" else 0
    if connects > policy()["max_connects_per_proposal"]:
        raise ValueError("Connects cost exceeds the active marketplace policy")
    if dry_run:
        return {"status": "preview", "connects": connects, "payload": payload, "stage": None}
    with closing(db()) as conn, conn:
        conn.execute("BEGIN IMMEDIATE")
        previous = conn.execute("SELECT tool,payload,result FROM actions WHERE user_id=? AND key=?",
                                (user, key)).fetchone()
        if previous:
            if previous["tool"] != tool or previous["payload"] != encode(payload):
                raise ValueError("Idempotency key already used with a different action")
            return json.loads(previous["result"])
        stage = None
        if tool == "send_message":
            if not conn.execute("SELECT 1 FROM proposals WHERE user_id=? AND job_id=? AND connects>0",
                                (user, job["id"])).fetchone():
                raise ValueError("A submitted proposal is required before sending a reply")
            conn.execute("INSERT INTO messages VALUES (?,?,?,?,?,?)",
                         (key, user, job["id"], "outbound", payload["text"], utc()))
            conn.execute("UPDATE proposals SET stage='interview' WHERE user_id=? AND job_id=? AND stage='replied'",
                         (user, job["id"]))
        elif tool == "create_proposal_draft":
            conn.execute("""INSERT INTO proposals VALUES (?,?,?,?,?,?,?)
                          ON CONFLICT(user_id,job_id) DO UPDATE SET body=excluded.body, amount=excluded.amount
                          WHERE proposals.connects=0""",
                         (user, job["id"], payload["text"], payload["amount"], "drafted", 0, utc()))
            stage = "drafted"
        elif tool == "submit_proposal":
            row = conn.execute("SELECT * FROM proposals WHERE user_id=? AND job_id=?", (user, job["id"])).fetchone()
            if not row or row["body"] != payload["text"] or row["amount"] != payload["amount"]:
                raise ValueError("The approved proposal must match the marketplace draft")
            if row["connects"] > 0:
                raise ValueError("This job already has a submitted proposal")
            funds = balance(user, conn)
            if connects > funds["remaining"] or connects + funds["week_spent"] > weekly_limit:
                raise ValueError("Insufficient Connects or weekly budget")
            stage = predicted_outcome(job, CLIENTS[job["client_id"]], payload["text"], payload["amount"])
            conn.execute("UPDATE proposals SET stage=?,connects=?,updated=? WHERE user_id=? AND job_id=?",
                         (stage, connects, utc(), user, job["id"]))
            if stage in {"replied", "hired"}:
                conn.execute("INSERT INTO messages VALUES (?,?,?,?,?,?)", (f"in-{job['id']}", user, job["id"],
                             "inbound", "Thanks for the relevant example. Could we schedule a short interview to discuss the handoff?", utc()))
        result = {"status": "applied", "connects": connects, "payload": payload, "stage": stage}
        conn.execute("INSERT INTO actions VALUES (?,?,?,?,?)", (user, key, tool, encode(payload), encode(result)))
        conn.execute("INSERT INTO audit(created,user_id,trace_id,tool,payload,result) VALUES (?,?,?,?,?,?)",
                     (utc(), user, trace_id, tool, encode(redact(payload)), encode(redact(result))))
        return result


