import json, sys, pathlib

FILES = [
    "../remembrance_archive/martyrs_index.json",
    "../remembrance_archive/indigenous_memorial.json"
]

def main():
    base = pathlib.Path(__file__).parent
    ok = True
    for rel in FILES:
        p = (base / rel).resolve()
        try:
            json.load(open(p, "r", encoding="utf-8"))
            print(f"[OK] {p.name} is valid JSON.")
        except Exception as e:
            ok = False
            print(f"[ERROR] {p.name}: {e}", file=sys.stderr)
    sys.exit(0 if ok else 1)

if __name__ == "__main__":
    main()
