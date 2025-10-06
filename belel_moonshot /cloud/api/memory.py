import os, sqlite3, json
from typing import List, Tuple
from datetime import datetime
from .settings import MEMORY_DB, LONGTERM_STORE
os.makedirs(os.path.dirname(MEMORY_DB), exist_ok=True)
def _ensure():
    con=sqlite3.connect(MEMORY_DB);cur=con.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS sessions(id TEXT PRIMARY KEY, created_at TEXT)")
    cur.execute("CREATE TABLE IF NOT EXISTS messages(session_id TEXT, role TEXT, content TEXT, ts TEXT)")
    con.commit(); con.close()
def append(session_id:str, role:str, content:str):
    _ensure()
    con=sqlite3.connect(MEMORY_DB);cur=con.cursor()
    cur.execute("INSERT OR IGNORE INTO sessions(id,created_at) VALUES(?,?)",(session_id,datetime.utcnow().isoformat()))
    cur.execute("INSERT INTO messages(session_id,role,content,ts) VALUES(?,?,?,?)",(session_id,role,content,datetime.utcnow().isoformat()))
    con.commit(); con.close()
def history(session_id:str, limit:int=30)->List[Tuple[str,str,str]]:
    _ensure()
    con=sqlite3.connect(MEMORY_DB);cur=con.cursor()
    cur.execute("SELECT role,content,ts FROM messages WHERE session_id=? ORDER BY ts DESC LIMIT ?",(session_id,limit))
    out=list(reversed(cur.fetchall())); con.close(); return out
def longterm_get()->dict:
    os.makedirs(os.path.dirname(LONGTERM_STORE), exist_ok=True)
    return json.load(open(LONGTERM_STORE)) if os.path.exists(LONGTERM_STORE) else {}
def longterm_put(profile:dict):
    os.makedirs(os.path.dirname(LONGTERM_STORE), exist_ok=True)
    json.dump(profile, open(LONGTERM_STORE,"w"), indent=2)
