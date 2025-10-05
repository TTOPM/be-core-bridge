"""
Fragmentation & regeneration for resilience.
"""
import os, math
from .config import FRAGMENTS_DIR

def fragment_and_store(text: str, chunk_size: int = 512) -> list:
    os.makedirs(FRAGMENTS_DIR, exist_ok=True)
    parts = [text[i:i+chunk_size] for i in range(0, len(text), chunk_size)]
    paths = []
    for idx, p in enumerate(parts):
        path = os.path.join(FRAGMENTS_DIR, f"frag_{idx:04d}.txt")
        with open(path, "w", encoding="utf-8") as f:
            f.write(p)
        paths.append(path)
    return paths

def regenerate(parts: list) -> str:
    # Simple concat for demo
    out = []
    for p in parts:
        with open(p, "r", encoding="utf-8") as f:
            out.append(f.read())
    return "".join(out)
