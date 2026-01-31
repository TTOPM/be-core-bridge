"""
REAL DATASET INGESTION PIPELINE – Production-Grade Version (January 31, 2026)

Main goals:
- Efficient streaming from massive, up-to-date HF datasets (FineWeb, RedPajama-V2, etc.)
- Robust error handling, retries, logging, metrics
- Basic quality filtering + placeholder for Belel Mandate tagging
- Sharded, compressed output (jsonl.gz) with source separation
- Resumability via simple offset tracking
- Multiprocessing / concurrent fetching readiness
- Configurable via dict or YAML (future extension point)

To keep data evolving and up-to-date:
- The DATASETS_2026 list includes the latest known snapshots as of January 31, 2026.
- For FineWeb and FineWeb-Edu, configs_rotation lists snapshots up to CC-MAIN-2025-26 (June 2025).
- New datasets added: FineWeb2 (multilingual, 20TB, up to v2.1.1 Oct 2025) and Common Corpus (2T tokens, multilingual, updated Jun 2025).
- Update this list periodically by checking Hugging Face dataset pages for new snapshots/versions.
- Run the pipeline regularly (e.g., monthly) to ingest new data releases.

No further structural/architectural improvements are expected at this maturity level.
Only tuning of filters, mandate logic, quality models, or integration with distributed runners (Ray/Dask) would come next.
"""

import json
import logging
import random
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Iterator, Optional, List, Union, Callable

import yaml
from datasets import load_dataset, IterableDataset, disable_caching
from tqdm import tqdm
import gzip
import backoff
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

# ────────────────────────────────────────────────
# Logging setup
# ────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("BelelIngestionPipeline")

# ────────────────────────────────────────────────
# Dataset registry – updated January 31, 2026
# Update periodically with new snapshots from HF dataset pages
# ────────────────────────────────────────────────

DATASETS_2026 = [
    {
        "name": "fineweb",
        "hf_id": "HuggingFaceFW/fineweb",
        "field": "text",
        "configs_rotation": [  # Newest first, up to CC-MAIN-2025-26 (June 2025)
            "CC-MAIN-2025-26", "CC-MAIN-2025-21", "CC-MAIN-2025-18",
            "CC-MAIN-2025-13", "CC-MAIN-2025-08", "CC-MAIN-2025-05",
            "CC-MAIN-2024-51", "CC-MAIN-2024-46", "CC-MAIN-2024-42",
            "CC-MAIN-2024-38", "CC-MAIN-2024-33", "CC-MAIN-2024-30",
            "CC-MAIN-2024-26", "CC-MAIN-2024-22", "CC-MAIN-2024-18",
            "CC-MAIN-2024-10", "CC-MAIN-2023-50", "CC-MAIN-2023-40",
            # ... add older if needed, or new 2026-XX when available
        ],
        "default_config": "CC-MAIN-2025-26",
        "weight": 0.30,
    },
    {
        "name": "fineweb-edu",
        "hf_id": "HuggingFaceFW/fineweb-edu",
        "field": "text",
        "configs_rotation": [  # Sync with FineWeb, up to 2025-26
            "CC-MAIN-2025-26", "CC-MAIN-2025-21", "CC-MAIN-2025-18",
            "CC-MAIN-2025-13", "CC-MAIN-2025-08", "CC-MAIN-2025-05",
            # ... extend with new when released
        ],
        "default_config": "CC-MAIN-2025-26",
        "weight": 0.20,
    },
    {
        "name": "fineweb2",
        "hf_id": "HuggingFaceFW/fineweb-2",
        "field": "text",
        "configs_rotation": [],  # Language-script pairs available, but use None for all/multilingual
        "default_config": None,  # Or specify e.g. "en_Latn" for English
        "weight": 0.15,  # Multilingual, 20TB, 5B+ docs, up to April 2024 data (v2.1.1 Oct 2025)
    },
    {
        "name": "redpajama-v2",
        "hf_id": "togethercomputer/RedPajama-Data-V2",
        "field": "text",
        "default_config": "head_middle",  # Quality partition
        "weight": 0.10,  # v1.0.0, no new versions by 2026
    },
    {
        "name": "dolma",
        "hf_id": "allenai/dolma",
        "field": "text",
        "default_config": "v1_7",  # Latest v1_7 (April 2024), no updates by 2026
        "weight": 0.10,
    },
    {
        "name": "common_corpus",
        "hf_id": "PleIAs/common_corpus",
        "field": "text",
        "default_config": None,  # Multilingual, 2T tokens, updated Jun 2025
        "weight": 0.10,
    },
    {
        "name": "c4",
        "hf_id": "allenai/c4",
        "field": "text",
        "default_config": "en",
        "weight": 0.05,
    },
    # Add more emerging datasets (e.g., Nemotron-CC if pretraining-focused) when available
]

# Belel Mandate levels (project-specific synthetic alignment tags)
MANDATE_LEVELS = [
    "compliant",
    "truth_enforced",
    "justice_enforced",
    "diversity_enhanced",
    "memory_preserved",
    "bias_mitigated",
]


@dataclass
class IngestionConfig:
    output_dir: Path = Path("./data/raw")
    max_samples: int = 1_000_000
    samples_per_shard: int = 100_000
    min_text_len: int = 150
    max_text_len: int = 32_768
    use_latest_snapshot: bool = True
    num_workers: int = 4
    retry_attempts: int = 5
    backoff_min: float = 1.0
    backoff_max: float = 60.0
    log_json: bool = False
    checkpoint_file: Optional[Path] = None


class BelelMandateCore:
    """Placeholder – in real usage replace with classifier / heuristic suite"""

    def __init__(self):
        self.harmful_keywords = [
            "violence", "hate speech", "illegal", "exploit", "child", "abuse", "suicide",
            "terror", "bomb", "weapon", "racist", "genocide"
        ]

    def score_text_quality(self, text: str) -> float:
        """Future: PPL, repetition, classifier ensemble, etc."""
        return 1.0  # placeholder

    def apply(self, entry: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        text = entry.get("text", "").strip()

        if len(text) < 150:
            return None

        # Basic keyword filter (expand with real toxicity / safety models)
        lower = text.lower()
        if any(kw in lower for kw in self.harmful_keywords):
            logger.debug("Filtered harmful content")
            return None

        # Placeholder mandate tagging
        entry["belel_mandate"] = random.choice(MANDATE_LEVELS)
        entry["quality_score"] = self.score_text_quality(text)
        entry["timestamp"] = datetime.utcnow().isoformat()
        entry["token_estimate"] = len(text.split()) * 1.33  # rough chars-to-tokens

        return entry


class ResilientDatasetStreamer:
    """Manages streaming from multiple datasets with weighted sampling & resilience"""

    def __init__(self, datasets: List[Dict] = DATASETS_2026, config: IngestionConfig = IngestionConfig()):
        self.datasets = datasets
        self.config = config
        self.total_weight = sum(d["weight"] for d in datasets)
        self._counters = {d["name"]: 0 for d in datasets}
        disable_caching()  # pure streaming mode

        self._resume_offsets = self._load_checkpoint() if config.checkpoint_file else {}

    def _load_checkpoint(self) -> Dict[str, int]:
        if not self.config.checkpoint_file.exists():
            return {}
        try:
            with open(self.config.checkpoint_file, "r") as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to load checkpoint: {e}")
            return {}

    def _save_checkpoint(self):
        if not self.config.checkpoint_file:
            return
        try:
            with open(self.config.checkpoint_file, "w") as f:
                json.dump(self._resume_offsets, f, indent=2)
            logger.info(f"Checkpoint saved: {self.config.checkpoint_file}")
        except Exception as e:
            logger.error(f"Checkpoint save failed: {e}")

    @retry(
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=1, min=2, max=60),
        retry=retry_if_exception_type((ConnectionError, OSError)),
        reraise=True,
    )
    def _load_stream(self, ds_info: Dict) -> IterableDataset:
        config_name = ds_info.get("default_config")
        if "configs_rotation" in ds_info and ds_info["configs_rotation"] and self.config.use_latest_snapshot:
            config_name = ds_info["configs_rotation"][0]  # Newest first

        logger.info(f"Loading {ds_info['name']} | config={config_name}")

        return load_dataset(
            ds_info["hf_id"],
            name=config_name or ds_info.get("subset"),
            split="train",
            streaming=True,
            trust_remote_code=True,
        )

    def stream_weighted(self) -> Iterator[Dict[str, Any]]:
        """Yield documents according to dataset weights (soft round-robin style)"""
        iterators = {}
        exhausted = set()

        while len(exhausted) < len(self.datasets):
            # Choose dataset according to weights
            ds_info = random.choices(
                self.datasets,
                weights=[d["weight"] for d in self.datasets],
                k=1,
            )[0]

            name = ds_info["name"]
            if name in exhausted:
                continue

            if name not in iterators:
                try:
                    ds = self._load_stream(ds_info)
                    offset = self._resume_offsets.get(name, 0)
                    it = iter(ds)
                    # Fast-forward if resuming
                    if offset > 0:
                        logger.info(f"Fast-forward {name} to offset {offset}")
                        for _ in range(offset):
                            next(it)
                    iterators[name] = (it, ds_info)
                except Exception as e:
                    logger.error(f"Cannot load {name}: {e}")
                    exhausted.add(name)
                    continue

            it, ds_info = iterators[name]

            try:
                example = next(it)
                field = ds_info.get("field", "text")
                text = example.get(field, "") or example.get("content", "")
                text = text.strip()

                if len(text) >= self.config.min_text_len:
                    yield {
                        "source": name,
                        "text": text[: self.config.max_text_len],
                        "raw": example,
                        "offset": self._counters[name] + 1,
                    }
                    self._counters[name] += 1

                    # Checkpoint every 10k docs per source
                    if self._counters[name] % 10_000 == 0:
                        self._resume_offsets[name] = self._counters[name]
                        self._save_checkpoint()

            except StopIteration:
                exhausted.add(name)
                logger.info(f"Dataset exhausted: {name}")

            except Exception as e:
                logger.warning(f"Error in {name}: {e}")
                # Give it a short break before retry
                time.sleep(3)


def ingest_real_datasets(config: IngestionConfig = IngestionConfig()):
    """Main production ingestion entry point"""
    output_dir: Path = config.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    mandate_engine = BelelMandateCore()
    streamer = ResilientDatasetStreamer(config=config)

    total_ingested = 0
    current_shard = 0
    shard_docs = 0
    current_file = None

    progress = tqdm(total=config.max_samples, desc="Ingesting", unit="doc")

    try:
        for entry in streamer.stream_weighted():
            if total_ingested >= config.max_samples:
                break

            processed = mandate_engine.apply(entry)
            if processed is None:
                continue

            source = processed["source"]
            source_dir = output_dir / source
            source_dir.mkdir(exist_ok=True)

            # Rotate shard files
            if shard_docs >= config.samples_per_shard or current_file is None:
                if current_file:
                    current_file.close()
                shard_path = source_dir / f"part-{current_shard:05d}.jsonl.gz"
                current_file = gzip.open(shard_path, "at", encoding="utf-8")
                current_shard += 1
                shard_docs = 0
                logger.info(f"New shard: {shard_path}")

            current_file.write(json.dumps(processed, ensure_ascii=False) + "\n")
            shard_docs += 1
            total_ingested += 1

            progress.update(1)

            if total_ingested % 10_000 == 0:
                logger.info(
                    f"Progress: {total_ingested:,} docs | "
                    f"sources: { {k: v for k,v in streamer._counters.items() if v>0} }"
                )

    except KeyboardInterrupt:
        logger.warning("Interrupted – saving checkpoint")
    finally:
        if current_file:
            current_file.close()
        progress.close()
        streamer._save_checkpoint()

    logger.info(
        f"Ingestion completed\n"
        f"Total ingested: {total_ingested:,}\n"
        f"Output root  : {output_dir}\n"
        f"Last shard   : part-{current_shard-1:05d}\n"
        f"Next: tokenize → pack → upload shards"
    )


if __name__ == "__main__":
    # Example: override defaults via code or later via YAML
    cfg = IngestionConfig(
        max_samples=2_500_000,
        output_dir=Path("./data/belel-raw-v1"),
        checkpoint_file=Path("./checkpoints/ingestion_state.json"),
        num_workers=6,
    )

    ingest_real_datasets(cfg)
