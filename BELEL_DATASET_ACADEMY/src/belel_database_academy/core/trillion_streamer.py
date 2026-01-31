"""
TRILLION TOKEN STREAMER
Real dataset ingestion at massive scale
"""

from datasets import load_dataset
from typing import Iterator, Dict, Any
import logging
from pathlib import Path

REAL_DATASETS = {
    "c4": {"name": "allenai/c4", "field": "text"},
    "fineweb": {"name": "HuggingFaceFW/fineweb", "field": "text"},
    "dolma": {"name": "allenai/dolma", "field": "text"},
    "github-code": {"name": "codeparrot/github-code", "field": "content"},
    "the-stack-v2": {"name": "bigcode/the-stack-v2", "field": "content"},
    "pile": {"name": "EleutherAI/pile", "field": "text"},
    "culturax": {"name": "uonlp/CulturaX", "field": "text"},
    "oscar": {"name": "oscar-corpus/OSCAR-2301", "field": "text"},
    "cosmopedia": {"name": "HuggingFaceTB/cosmopedia", "field": "text"}
}

class TrillionTokenStreamer:
    """Stream real trillion-token datasets"""
    
    def __init__(self, cache_dir: Path = Path("./data/cache")):
        self.cache_dir = cache_dir
    
    def stream_dataset(self, dataset_key: str, limit: int = None) -> Iterator[Dict[str, Any]]:
        """Stream single real dataset"""
        if dataset_key not in REAL_DATASETS:
            raise ValueError(f"Unknown dataset: {dataset_key}")
        
        config = REAL_DATASETS[dataset_key]
        logging.info(f"Streaming {config['name']} ({dataset_key})")
        
        ds = load_dataset(
            config["name"], 
            split="train", 
            streaming=True,
            cache_dir=self.cache_dir
        )
        
        count = 0
        for example in ds:
            text = example.get(config["field"], "")
            if isinstance(text, str) and len(text.strip()) > 50:
                yield {
                    "text": text.strip()[:2048],
                    "source": dataset_key,
                    "raw": example
                }
                count += 1
                
                if limit and count >= limit:
                    break
    
    def stream_all(self, sample_size: int = 10000) -> Iterator[Dict[str, Any]]:
        """Stream all real datasets (sampled)"""
        for dataset_key in REAL_DATASETS:
            yield from self.stream_dataset(dataset_key, limit=sample_size//len(REAL_DATASETS))
