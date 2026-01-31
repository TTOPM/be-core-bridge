# BELEL_SELF_TEACHING/BELEL_SELF_TEACHING_GENERATOR.py
import json
from pathlib import Path

from .utils import utc_cycle_id, sha256_text
from .selectors import pick_candidates
from .generators import generate_variants, self_consistency_pick
from .verifiers import verify
from .quality import basic_sanity_checks, rubric_score
from .curriculum import assign_level
from .dpo_builder import build_dpo_pairs
from .dedup import Deduper
from .shard_writer import write_jsonl_gz
from .metrics import aggregate_metrics
from .guide_updater import ensure_level_files, append_examples
from .guide_compiler import compile_master
from .schemas import to_jsonl

BASE = Path("BELEL_SELF_TEACHING")
CFG_DIR = BASE / "config"
GUIDE_LEVELS = BASE / "guide" / "levels"
GUIDE_COMPILED = BASE / "guide" / "compiled"
CYCLES = BASE / "cycles"
OUT_SFT = BASE / "generated_shards" / "sft"
OUT_DPO = BASE / "generated_shards" / "dpo"
OUT_NEG = BASE / "generated_shards" / "negatives"
OUT_MAN = BASE / "generated_shards" / "manifests"
IDX_DIR = BASE / "indexes"

def load_json(path: Path, default):
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(default, indent=2), encoding="utf-8")
    return default

def load_seen_hashes() -> set:
    IDX_DIR.mkdir(parents=True, exist_ok=True)
    seen_path = IDX_DIR / "seen_hashes.jsonl"
    if not seen_path.exists():
        return set()
    s = set()
    for ln in seen_path.read_text(encoding="utf-8").splitlines():
        if ln.strip():
            s.add(ln.strip())
    return s

def persist_seen_hashes(new_hashes: list):
    seen_path = IDX_DIR / "seen_hashes.jsonl"
    with seen_path.open("a", encoding="utf-8") as f:
        for h in new_hashes:
            f.write(h + "\n")

def run_self_teaching_cycle(belel_core):
    """
    belel_core must supply:
      - ingest_data(sources=[...]) -> List[dict] with {prompt, tags?, domain?, ...}
      - apply_mandate(text) -> {allowed: bool, reasons: [...]}
      - verify_execution(text) -> {passed: bool, signals:..., errors:...}
      - generate_reflexive_variant(prompt, mode=...) -> str
      - get_uncertainty_score(item) -> float
    """
    config = load_json(CFG_DIR / "self_teaching_config.json", {
        "budget_per_cycle": 300,
        "variants_per_prompt": 3,
        "mix": {"uncertainty": 0.55, "rarity": 0.20, "failure_replay": 0.20, "random": 0.05},
        "rarity_keywords": ["edge case", "counterexample", "adversarial", "race condition", "overflow", "off-by-one"],
        "rubric_min_total": 0.78,
        "keep_failures_rate": 0.15,
        "compile_guide_every_cycle": True
    })

    strategies = load_json(CFG_DIR / "strategies.json", {
        "sources": ["internal_pool", "previous_shards"],
        "domains_default": "general"
    })

    cycle_id = utc_cycle_id()
    cycle_dir = CYCLES / cycle_id.replace(":", "-")
    cycle_dir.mkdir(parents=True, exist_ok=True)

    ensure_level_files(GUIDE_LEVELS)

    seen = load_seen_hashes()
    deduper = Deduper(seen, fuzzy_threshold=0.92)

    pool = belel_core.ingest_data(sources=strategies["sources"])
    rarity_keywords = set(config["rarity_keywords"])

    candidates = pick_candidates(
        pool=pool,
        budget=config["budget_per_cycle"],
        get_uncertainty_score=belel_core.get_uncertainty_score,
        rarity_keywords=rarity_keywords,
        mix=config["mix"]
    )

    # Log selection (for auditability)
    (cycle_dir / "selection.jsonl").write_text(
        "\n".join(json.dumps(c, ensure_ascii=False) for c in candidates),
        encoding="utf-8"
    )

    sft_records = []
    dpo_records = []
    failures = []
    new_hashes_to_persist = []

    for cand in candidates:
        prompt = cand.get("prompt", "")
        tags = cand.get("tags", []) or []
        domain = cand.get("domain") or strategies.get("domains_default", "general")

        variants = generate_variants(prompt, belel_core.generate_reflexive_variant, n=config["variants_per_prompt"])
        variants = self_consistency_pick(variants)

        verified_texts = []
        rejected_texts = []

        for completion in variants:
            ok, reason = basic_sanity_checks(prompt, completion)
            if not ok:
                rejected_texts.append(completion)
                continue

            mandate = belel_core.apply_mandate(completion)
            if not mandate.get("allowed", True):
                rejected_texts.append(completion)
                continue

            if deduper.is_exact_dup(completion) or deduper.is_fuzzy_dup(completion):
                continue

            ver = verify(completion, belel_core.verify_execution)
            rub = rubric_score(prompt, completion, ver)

            level = assign_level(prompt, domain)
            h = sha256_text(prompt + "\n" + completion)

            record = {
                "prompt": prompt,
                "completion": completion,
                "level": level,
                "domain": domain,
                "source": "self_generated",
                "verified": bool(ver.get("passed")),
                "verifier": ver,
                "rubric": rub,
                "hash": h,
                "cycle_id": cycle_id,
                "tags": tags,
                "metadata": cand.get("metadata", {}),
            }

            if ver.get("passed") and rub["total"] >= config["rubric_min_total"]:
                sft_records.append(record)
                verified_texts.append(completion)
                deduper.add_exact(completion)
                deduper.remember(completion)
                new_hashes_to_persist.append(sha256_text(completion))
            else:
                rejected_texts.append(completion)
                if config["keep_failures_rate"] > 0:
                    failures.append(record)

        # Build DPO pairs from verified vs rejected
        pairs = build_dpo_pairs(prompt, verified_texts, rejected_texts, limit=2)
        for chosen, rejected in pairs:
            level = assign_level(prompt, domain)
            dpo_records.append({
                "prompt": prompt,
                "chosen": chosen,
                "rejected": rejected,
                "level": level,
                "domain": domain,
                "source": "self_generated_dpo",
                "chosen_hash": sha256_text(chosen),
                "rejected_hash": sha256_text(rejected),
                "cycle_id": cycle_id,
                "tags": tags
            })

    # Persist seen hashes
    persist_seen_hashes(new_hashes_to_persist)

    # Write shards
    sft_path = OUT_SFT / f"sft_{cycle_id.replace(':','-')}.jsonl.gz"
    dpo_path = OUT_DPO / f"dpo_{cycle_id.replace(':','-')}.jsonl.gz"
    neg_path = OUT_NEG / f"neg_{cycle_id.replace(':','-')}.jsonl.gz"

    write_jsonl_gz(sft_path, (json.dumps(r, ensure_ascii=False) for r in sft_records))
    write_jsonl_gz(dpo_path, (json.dumps(r, ensure_ascii=False) for r in dpo_records))
    write_jsonl_gz(neg_path, (json.dumps(r, ensure_ascii=False) for r in failures))

    # Metrics
    m = aggregate_metrics(sft_records, dpo_records, failures)
    (cycle_dir / "metrics.json").write_text(json.dumps(m, indent=2), encoding="utf-8")

    # Update guide + compile
    append_examples(GUIDE_LEVELS, sft_records, cycle_id, per_level_cap=10)
    if config.get("compile_guide_every_cycle", True):
        compile_master(GUIDE_LEVELS, GUIDE_COMPILED)

    # Cycle summary
    (cycle_dir / "cycle.json").write_text(json.dumps({
        "cycle_id": cycle_id,
        "pool_size": len(pool),
        "candidates_selected": len(candidates),
        "sft_emitted": len(sft_records),
        "dpo_emitted": len(dpo_records),
        "failures_kept": len(failures),
        "metrics": m,
        "config": config
    }, indent=2), encoding="utf-8")

    return {"cycle_id": cycle_id, "metrics": m, "paths": {"sft": str(sft_path), "dpo": str(dpo_path), "neg": str(neg_path), "cycle_dir": str(cycle_dir)}}
