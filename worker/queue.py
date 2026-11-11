import json
import time
from contextlib import closing
from uuid import NAMESPACE_URL, uuid5

from agent.storage import encode, open_db, utc
from gigsim.service import redact

ACTIVE = {"queued", "running", "marketplace_unavailable"}


def db():
    conn = open_db("runs.sqlite")
    conn.executescript("""
      CREATE TABLE IF NOT EXISTS runs (
        id TEXT PRIMARY KEY, tenant TEXT, kind TEXT, job_id TEXT, status TEXT, initial TEXT,
        resume TEXT, result TEXT, error TEXT, attempts INTEGER, due REAL, created TEXT, updated TEXT);
      CREATE TABLE IF NOT EXISTS events (
        seq INTEGER PRIMARY KEY, run_id TEXT, tenant TEXT, created TEXT, data TEXT);
      CREATE INDEX IF NOT EXISTS runs_tenant ON runs (tenant,kind,job_id);
      CREATE INDEX IF NOT EXISTS events_run ON events (tenant,run_id,seq);
    """)
    return conn


def hydrate(row):
    if not row:
        return None
    obj = dict(row)
    for key in ("initial", "resume", "result"):
        obj[key] = json.loads(obj[key]) if obj[key] else None
    return obj


def enqueue(tenant, kind, job_id, settings, strategy="evidence_first"):
    run_id = uuid5(NAMESPACE_URL, f"gigbid/{tenant}/{kind}/{job_id}").hex
    state = {"user_id": tenant, "trace_id": run_id, "job_id": job_id, "persona": settings["persona"],
             "floor": settings["floor"], "weekly_limit": settings["weekly_limit"], "strategy": strategy, "autonomy": settings.get("autonomy", "review")}
    with closing(db()) as conn, conn:
        conn.execute("""INSERT OR IGNORE INTO runs VALUES (?,?,?,?,?,?,NULL,NULL,NULL,0,?,?,?)""",
                     (run_id, tenant, kind, job_id, "queued", encode(state), time.time(), utc(), utc()))
    return get(tenant, run_id)


def get(tenant, run_id):
    with closing(db()) as conn:
        return hydrate(conn.execute("SELECT * FROM runs WHERE tenant=? AND id=?", (tenant, run_id)).fetchone())


def list_runs(tenant, kind=""):
    with closing(db()) as conn:
        return [hydrate(row) for row in conn.execute(
            "SELECT * FROM runs WHERE tenant=? AND (?='' OR kind=?) ORDER BY rowid DESC", (tenant, kind, kind))]


def approve(tenant, run_id, value):
    with closing(db()) as conn, conn:
        updated = conn.execute("""UPDATE runs SET resume=?,status='queued',due=?,updated=?,attempts=0
                                  WHERE tenant=? AND id=? AND status='pending'""",
                               (encode(value), time.time(), utc(), tenant, run_id))
        return bool(updated.rowcount)


def retry(tenant, run_id):
    with closing(db()) as conn, conn:
        updated = conn.execute("""UPDATE runs SET status='queued',error=NULL,due=?,updated=?,attempts=0
                                  WHERE tenant=? AND id=? AND status IN ('needs_attention','marketplace_unavailable')""",
                               (time.time(), utc(), tenant, run_id))
        return bool(updated.rowcount)


def claim():
    now = time.time()
    with closing(db()) as conn, conn:
        conn.execute("BEGIN IMMEDIATE")
        row = conn.execute("""SELECT * FROM runs WHERE due<=? AND status IN ('queued','marketplace_unavailable','running')
                             ORDER BY due LIMIT 1""", (now,)).fetchone()
        if row:
            conn.execute("UPDATE runs SET status='running',due=?,attempts=attempts+1,updated=? WHERE id=?",
                         (now+300, utc(), row["id"]))
            return hydrate(row)


def save(run, status, result, error=None, delay=0):
    with closing(db()) as conn, conn:
        conn.execute("""UPDATE runs SET status=?,result=?,error=?,updated=?,due=?,resume=CASE WHEN ? THEN resume ELSE NULL END
                        WHERE id=? AND tenant=?""",
                     (status, encode(result), error, utc(), time.time()+delay,
                      status in {"marketplace_unavailable", "needs_attention"}, run["id"], run["tenant"]))


def event(run, data):
    with closing(db()) as conn, conn:
        conn.execute("INSERT INTO events(run_id,tenant,created,data) VALUES (?,?,?,?)",
                     (run["id"], run["tenant"], utc(), encode(redact(data))))


def events(tenant, run_id, after=0):
    with closing(db()) as conn:
        return [{"seq": row["seq"], "date": row["created"], **json.loads(row["data"])}
                for row in conn.execute("""SELECT seq,created,data FROM events WHERE tenant=? AND run_id=? AND seq>?
                                          ORDER BY seq""", (tenant, run_id, after))]

