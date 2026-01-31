import gzip
from pathlib import Path
from BELEL_SELF_TEACHING.shard_writer import write_jsonl_gz

def test_write_jsonl_gz(tmp_path: Path):
    path = tmp_path / "test.jsonl.gz"
    lines = ['{"a":1}', '{"b":2}']

    write_jsonl_gz(path, lines)

    assert path.exists()

    with gzip.open(path, "rt", encoding="utf-8") as f:
        content = f.read().splitlines()

    assert content == lines
