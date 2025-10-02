import json
def parse_json_bytes(b: bytes):
    try: return json.loads(b.decode("utf-8"))
    except Exception: return None
