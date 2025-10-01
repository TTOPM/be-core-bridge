import re, hashlib
EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
PHONE = re.compile(r"\+?[0-9][0-9\-()\s]{6,}[0-9]")
def _hash(s:str)->str: return hashlib.sha256(s.encode()).hexdigest()[:16]
def redact(text:str)->str:
    text = EMAIL.sub(lambda m: f"<email:{_hash(m.group(0))}>", text)
    text = PHONE.sub(lambda m: f"<phone:{_hash(m.group(0))}>", text)
    return text
