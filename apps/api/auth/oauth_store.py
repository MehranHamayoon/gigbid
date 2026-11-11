import os
from base64 import urlsafe_b64encode
from contextlib import closing
from hashlib import sha256

from cryptography.fernet import Fernet

from agent.storage import open_db


def cipher():
    secret = os.environ["APP_SECRET_KEY"]
    return Fernet(urlsafe_b64encode(sha256(secret.encode()).digest()))


def db():
    connection = open_db("auth.sqlite")
    connection.execute("CREATE TABLE IF NOT EXISTS oauth (user_id TEXT PRIMARY KEY, token BLOB)")
    return connection


def save(user_id, token):
    with closing(db()) as conn, conn:
        conn.execute("INSERT OR REPLACE INTO oauth VALUES (?,?)", (user_id, cipher().encrypt(token.encode())))


def load(user_id):
    with closing(db()) as conn:
        row = conn.execute("SELECT token FROM oauth WHERE user_id=?", (user_id,)).fetchone()
    return cipher().decrypt(row[0]).decode() if row else None
