"""
REAL DATASET INGESTION PIPELINE
Downloads + processes trillion-token sources
"""

import json
from pathlib import Path
from tqdm import tqdm
import gzip
from ..core.trillion_streamer import TrillionTokenStreamer
from ..core.mandate_engine import BelelMandateCore

def ingest_real_datasets(
    output_dir: Path = Path("./data/raw"),
    sample_size: int = 10000,
    max_workers: int = 4
):
    """Main ingestion pipeline"""
    streamer = TrillionTokenStreamer()
    mandate = BelelMandateCore()
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    for dataset_name in tqdm(streamer.stream_all(sample_size), total=sample_size, desc="Ingesting"):
        # Save raw
        raw_path = output_dir / dataset_name["source"] / "raw.jsonl.gz"
        raw_path.parent.mkdir(parents=True, exist_ok=True)
        
        with gzip.open(raw_path, "at", encoding="utf-8") as f:
            f.write(json.dumps(dataset_name) + "\n")
    
    print(f"✅ Ingested {sample_size} real samples across {len(streamer.stream_all(0))} datasets")

if __name__ == "__main__":
    ingest_real_datasets()
