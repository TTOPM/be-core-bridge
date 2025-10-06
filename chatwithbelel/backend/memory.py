
import sqlite3
import os
from typing import List, Tuple, Optional
from datetime import datetime

DB_PATH = os.environ.get("BELEL_MEMORY_DB", "chat_memory.sqlite")

def _ensure():
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            id TEXT PRIMARY KEY,
            created_at TEXT
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            session_id TEXT,
            role TEXT,
            content TEXT,
            ts TEXT
        )
    """)
    con.commit()
    con.close()

def append_message(session_id: str, role: str, content: str):
    _ensure()
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    # ensure session
    cur.execute("INSERT OR IGNORE INTO sessions (id, created_at) VALUES (?, ?)",
                (session_id, datetime.utcnow().isoformat()))
    cur.execute("INSERT INTO messages (session_id, role, content, ts) VALUES (?, ?, ?, ?)",
                (session_id, role, content, datetime.utcnow().isoformat()))
    con.commit()
    con.close()

def get_history(session_id: str, limit: int = 20) -> List[Tuple[str, str, str, str]]:
    _ensure()
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute("SELECT role, content, ts FROM messages WHERE session_id=? ORDER BY ts DESC LIMIT ?", (session_id, limit))
    rows = cur.fetchall()
    con.close()
    return list(reversed(rows))
