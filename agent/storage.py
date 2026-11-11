import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from agent.settings import STATE


def utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def open_db(name: str) -> sqlite3.Connection:
    STATE.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(STATE / Path(name), timeout=15)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA journal_mode=WAL")
    db.execute("PRAGMA foreign_keys=ON")
    return db


def encode(value) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))
