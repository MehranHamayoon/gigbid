import hmac
import json
import os
import time
from contextlib import closing
from hashlib import scrypt, sha256
from secrets import token_hex
from uuid import uuid4

from fastapi import HTTPException, Request, Response

from agent.storage import encode, open_db

COOKIE = "gigbid_session"
DEFAULTS = {"persona": "ai", "floor": 180, "weekly_limit": 30, "filters": "", "autonomy": "review",
            "scout_hours": 4, "onboarded": False}


def db():
    conn = open_db("auth.sqlite")
    conn.executescript("""
      CREATE TABLE IF NOT EXISTS accounts (
          id TEXT PRIMARY KEY, email TEXT UNIQUE, name TEXT, password TEXT, prefs TEXT, scout_after REAL DEFAULT 0);
      CREATE TABLE IF NOT EXISTS sessions (digest TEXT PRIMARY KEY, user_id TEXT, expiry REAL);
    """)
    return conn


def password_hash(password, salt):
    return scrypt(password.encode(), salt=bytes.fromhex(salt), n=16384, r=8, p=1).hex()


def register(name, email, password, ready=False, id=None):
    salt = token_hex(16)
    user_id = id or uuid4().hex
    prefs = {**DEFAULTS, "onboarded": ready}
    with closing(db()) as conn, conn:
        conn.execute("INSERT INTO accounts (id,email,name,password,prefs) VALUES (?,?,?,?,?)",
                     (user_id, email.casefold().strip(), name, f"{salt}:{password_hash(password, salt)}", encode(prefs)))
    return user_id


def reviewer_seed():
    email, password = os.getenv("REVIEWER_EMAIL"), os.getenv("REVIEWER_PASSWORD")
    if email and password:
        with closing(db()) as conn:
            exists = conn.execute("SELECT 1 FROM accounts WHERE email=?", (email.casefold(),)).fetchone()
        if not exists:
            register("Assignment Reviewer", email, password, ready=True)


def login(email, password):
    with closing(db()) as conn:
        row = conn.execute("SELECT id,password FROM accounts WHERE email=?", (email.casefold().strip(),)).fetchone()
    salt, target = row["password"].split(":") if row else ("00" * 16, "00" * 64)
    if not hmac.compare_digest(password_hash(password, salt), target) or row is None:
        raise HTTPException(401, "Email or password did not match")
    return row["id"]


def session(response: Response, user_id):
    token = token_hex(32)
    with closing(db()) as conn, conn:
        conn.execute("DELETE FROM sessions WHERE expiry<?", (time.time(),))
        conn.execute("INSERT INTO sessions VALUES (?,?,?)", (sha256(token.encode()).hexdigest(), user_id, time.time()+43200))
    response.set_cookie(COOKIE, token, max_age=43200, httponly=True, secure=os.getenv("APP_ENV") == "production",
                        samesite="lax", path="/")


def user(request: Request):
    token = request.cookies.get(COOKIE, "")
    with closing(db()) as conn:
        row = conn.execute("""SELECT a.id,a.email,a.name,a.prefs FROM sessions s JOIN accounts a ON a.id=s.user_id
                            WHERE s.digest=? AND s.expiry>?""", (sha256(token.encode()).hexdigest(), time.time())).fetchone()
    if not row:
        raise HTTPException(401, "Sign in to continue")
    return {"id": row["id"], "email": row["email"], "name": row["name"], "settings": json.loads(row["prefs"])}


def logout(request, response):
    token = request.cookies.get(COOKIE, "")
    with closing(db()) as conn, conn:
        conn.execute("DELETE FROM sessions WHERE digest=?", (sha256(token.encode()).hexdigest(),))
    response.delete_cookie(COOKIE)


def update(user_id, values):
    with closing(db()) as conn, conn:
        conn.execute("UPDATE accounts SET prefs=?,scout_after=? WHERE id=?", (encode(values), time.time(), user_id))


def due_searches():
    now = time.time()
    with closing(db()) as conn, conn:
        conn.execute("BEGIN IMMEDIATE")
        rows = list(conn.execute("SELECT id,prefs FROM accounts WHERE scout_after<=?", (now,)))
        due = []
        for row in rows:
            prefs = json.loads(row["prefs"])
            interval = prefs["scout_hours"] * 3600
            if prefs["onboarded"] and prefs["filters"]:
                due.append((row["id"], prefs))
            conn.execute("UPDATE accounts SET scout_after=? WHERE id=?", (now + interval, row["id"]))
    return due
