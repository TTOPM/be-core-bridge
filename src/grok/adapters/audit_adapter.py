from __future__ import annotations
import os, json, hashlib

class AuditAdapter:
    def __init__(self):
        self._path = os.getenv("GROK_AUDIT_PATH", os.path.expanduser("~/.grok/audit.log"))
        os.makedirs(os.path.dirname(self._path), exist_ok=True)

    def last_hash(self) -> str|None:
        try:
            with open(self._path,"r",encoding="utf-8") as f:
                lines = [l.strip() for l in f if l.strip()]
                if not lines: return None
                rec = json.loads(lines[-1])
                return rec.get("hash")
        except FileNotFoundError:
            return None

    def chain_is_monotone(self) -> bool:
        try:
            with open(self._path,"r",encoding="utf-8") as f:
                prev = None
                for line in f:
                    line=line.strip()
                    if not line: continue
                    rec=json.loads(line)
                    # simple check that prev hash matches
                    if rec.get("prev") != prev:
                        if prev is None:  # first record may have prev None
                            pass
                        else:
                            return False
                    prev = rec.get("hash")
            return True
        except FileNotFoundError:
            return True

    def replay_from_checkpoint(self) -> None:
        # In a real system, rebuild file from known-good snapshot; here we noop.
        pass

    def rebuild(self, cid: str, tail: str|None) -> None:
        # Optionally re-seal last record with “regeneration” note
        rec = {"event":"rebuild", "cid":cid, "prev":tail}
        rec["hash"]=hashlib.sha256(json.dumps(rec,sort_keys=True).encode()).hexdigest()
        with open(self._path,"a",encoding="utf-8") as f:
            f.write(json.dumps(rec,sort_keys=True)+ "\n")
