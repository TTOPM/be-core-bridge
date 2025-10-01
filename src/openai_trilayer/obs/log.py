import json, time, uuid, sys
def log(event, **kw):
    print(json.dumps({"ts": time.time(), "id": str(uuid.uuid4()), "event": event, **kw}), file=sys.stdout)
