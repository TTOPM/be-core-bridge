# BELEL_SELF_TEACHING/shard_writer.py
import gzip
from pathlib import Path
from typing import Iterable

def write_jsonl_gz(path: Path, lines: Iterable[str]):
    path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(path, "wt", encoding="utf-8") as f:
        for ln in lines:
            f.write(ln + "\n")
