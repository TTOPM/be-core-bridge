
"""
policy_pipeline.py — multi-stage safety/compliance graph.

Stages:
  - disclosure
  - harm
  - bias
  - jurisdiction
  - provenance
  - audit_log
"""
from dataclasses import dataclass
from typing import List, Dict, Tuple

@dataclass
class PolicyContext:
    user_text: str
    model_text: str
    session_disclosed: bool
    locale: str = "EU"
    meta: Dict = None

class Stage:
    def run(self, ctx: PolicyContext) -> PolicyContext: return ctx

class Disclosure(Stage):
    SENTENCE = "For transparency: you are speaking with Belel, an artificial system."
    def run(self, ctx: PolicyContext):
        if not ctx.session_disclosed:
            ctx.model_text = f"{self.SENTENCE} {ctx.model_text}"
            ctx.meta = (ctx.meta or {}) | {"disclosed_now": True}
        return ctx

class Harm(Stage):
    BAD = {"suicide","harm myself","build a bomb","violence","hate","harass"}
    def run(self, ctx: PolicyContext):
        if any(k in ctx.user_text.lower() for k in self.BAD):
            ctx.model_text = ("I can’t help with that. If you’re in danger or considering self-harm, "
                              "please seek immediate help from local services.")
            ctx.meta = (ctx.meta or {}) | {"blocked": True}
        return ctx

class Bias(Stage):
    def run(self, ctx: PolicyContext):
        # TODO: plug ML classifier and mitigation.
        return ctx

class Jurisdiction(Stage):
    def run(self, ctx: PolicyContext):
        # TODO: adapt rules per ctx.locale / Concordium mandate.
        return ctx

class Provenance(Stage):
    def run(self, ctx: PolicyContext):
        # TODO: sign/trace outputs for provenance if needed.
        return ctx

class AuditLog(Stage):
    def run(self, ctx: PolicyContext):
        # TODO: write to audit log store.
        return ctx

class PolicyGraph:
    def __init__(self, stages: List[Stage]):
        self.stages = stages
    def run(self, ctx: PolicyContext) -> PolicyContext:
        for s in self.stages:
            ctx = s.run(ctx)
        return ctx


import os, hmac, hashlib, time, sqlite3

class Bias(Stage):
    WORDS = {"idiot","stupid"}  # placeholder
    def run(self, ctx: PolicyContext):
        if any(w in ctx.model_text.lower() for w in self.WORDS):
            ctx.model_text = ctx.model_text.replace("idiot","person").replace("stupid","unwise")
            ctx.meta = (ctx.meta or {}) | {"bias_mitigated": True}
        return ctx

class Jurisdiction(Stage):
    def run(self, ctx: PolicyContext):
        # Example: stricter rules in EU for privacy-sensitive content.
        if ctx.locale.upper()=="EU":
            # Placeholder: scrub emails
            import re
            ctx.model_text = re.sub(r"[\w\.-]+@[\w\.-]+", "[redacted-email]", ctx.model_text)
        return ctx

class Provenance(Stage):
    def run(self, ctx: PolicyContext):
        secret = os.getenv("PROVENANCE_HMAC_SECRET","")
        if secret:
            sig = hmac.new(secret.encode(), ctx.model_text.encode(), hashlib.sha256).hexdigest()
            ctx.meta = (ctx.meta or {}) | {"provenance_sig": sig}
        return ctx

class AuditLog(Stage):
    def run(self, ctx: PolicyContext):
        path = os.getenv("AUDIT_DB","")
        if not path: return ctx
        os.makedirs(os.path.dirname(path), exist_ok=True)
        con = sqlite3.connect(path)
        cur = con.cursor()
        cur.execute("CREATE TABLE IF NOT EXISTS audit(ts REAL, user_text TEXT, model_text TEXT, meta TEXT)")
        cur.execute("INSERT INTO audit(ts,user_text,model_text,meta) VALUES(?,?,?,?)",
                    (time.time(), ctx.user_text, ctx.model_text, str(ctx.meta)))
        con.commit(); con.close()
        return ctx
