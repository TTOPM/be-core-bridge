import os, hashlib
def make_id(prompt:str, anchors:str, nonce:str|None=None)->str:
    nonce = nonce or os.urandom(8).hex()
    return hashlib.sha256(f"{prompt}|{anchors}|{nonce}".encode()).hexdigest()
