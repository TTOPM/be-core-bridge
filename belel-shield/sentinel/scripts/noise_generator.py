#!/usr/bin/env python3
import random, time, json
from pathlib import Path
OUT = Path.home() / ".belel" / "noise_events.jsonl"
OUT.parent.mkdir(parents=True, exist_ok=True)
QUERIES = ["best coffee", "how to fix sink", "weather today", "gardening tips", "sports scores"]
def generate_one():
    ev = {"ts": __import__("datetime").datetime.utcnow().isoformat()+"Z", "q": random.choice(QUERIES)}
    OUT.open("a").write(json.dumps(ev)+"\n")
    return ev
if __name__ == "__main__":
    try:
        while True:
            print(generate_one()); time.sleep(random.uniform(2,6))
    except KeyboardInterrupt:
        pass
