# BELEL_SELF_TEACHING_GENERATOR.py
# Autonomous self-teaching loop: active-inspired selection → generation → verification → shard output + guide update
# Inspired by: A-SOID (uncertainty iteration), Hawk (rare/uncertain signal discovery), ASReview (query strategies for text)

import os
import json
import gzip
import hashlib
import datetime
import random
from pathlib import Path
# Assume these are from your BELEL core (adapt imports as needed)
from belel_core import (
    ingest_data,                # pull from internal pool or external if allowed
    apply_mandate,              # enforce structure/truth
    verify_execution,           # sandbox math/code execution
    generate_reflexive_variant, # your existing mutation/reflexion func
    get_uncertainty_score       # placeholder: implement or stub based on model confidence
)

# Config paths (create these files manually first or generate defaults)
CONFIG_DIR = Path("BELEL_SELF_TEACHING/config")
CONFIG_DIR.mkdir(exist_ok=True, parents=True)
GUIDE_DIR = Path("BELEL_SELF_TEACHING/guide")
GUIDE_DIR.mkdir(exist_ok=True, parents=True)
SHARDS_DIR = Path("BELEL_SELF_TEACHING/generated_shards")
SHARDS_DIR.mkdir(exist_ok=True, parents=True)
CYCLES_DIR = Path("BELEL_SELF_TEACHING/cycles")
CYCLES_DIR.mkdir(exist_ok=True, parents=True)

# Levels for guide (as previously defined)
LEVELS = [
    "1_Foundations",
    "2_Core_Methodologies",
    "3_Advanced_Self_Improvement",
    "4_Specialized_Domains",
    "5_Meta_Level_Evolution"
]

def load_or_init_config():
    config_path = CONFIG_DIR / "self_teaching_config.json"
    if config_path.exists():
        with open(config_path, 'r') as f:
            return json.load(f)
    default = {
        "budget_per_cycle": 500,           # new examples to generate/verify per run
        "uncertainty_threshold": 0.65,     # select above this for hard/important
        "pseudo_label_confidence": 0.92,   # auto-accept high-confidence generations
        "max_iterations": 10,
        "shard_size": 1000
    }
    with open(config_path, 'w') as f:
        json.dump(default, f, indent=2)
    return default

def select_uncertain_or_rare_candidates(pool, config):
    """Active learning selection: prioritize uncertain / hard / rare signals (inspired by A-SOID + Hawk)"""
    scores = []
    for item in pool:
        # Assume item = {"prompt": str, "existing_completion": str or None, "embedding": vec or None}
        uncertainty = get_uncertainty_score(item)  # stub: e.g. entropy from model preds
        # Bonus: rarity (e.g. low freq domain keywords or execution failure history)
        rarity_bonus = 1.0 if "edge_case" in item.get("tags", []) else 0.5
        scores.append(uncertainty * rarity_bonus)
    
    sorted_idx = sorted(range(len(pool)), key=lambda i: scores[i], reverse=True)
    return [pool[i] for i in sorted_idx[:config["budget_per_cycle"]]]

def generate_new_material(candidates, config):
    """Generate new completions, explanations, code, etc. with reflexive mutation"""
    new_items = []
    for cand in candidates:
        base_prompt = cand.get("prompt", "")
        # Generate primary
        completion = generate_reflexive_variant(base_prompt)  # your core generation func
        # Create variants (self-augmentation like synthetic data gen)
        variants = [completion]
        for _ in range(random.randint(1, 3)):
            mutated = generate_reflexive_variant(completion, mode="mutate")  # e.g. paraphrase, add difficulty
            variants.append(mutated)
        
        for v in variants:
            verified = verify_execution(v)  # BELEL truth metric
            if verified["passed"]:
                new_items.append({
                    "prompt": base_prompt,
                    "completion": v,
                    "source": "self_generated",
                    "verified_hash": hashlib.sha256(v.encode()).hexdigest(),
                    "level": assign_level(base_prompt),  # helper below
                    "uncertainty": get_uncertainty_score(cand)
                })
            elif random.random() < 0.2:  # occasionally keep failures for negative examples / DPO
                new_items.append({
                    "prompt": base_prompt,
                    "completion": v,
                    "source": "self_generated_failure",
                    "verified_hash": None,
                    "level": assign_level(base_prompt)
                })
    return new_items

def assign_level(prompt):
    """Map to guide levels heuristically (expand with keywords/rules)"""
    if any(k in prompt.lower() for k in ["truth", "cognition", "perception", "execution"]):
        return LEVELS[0]
    # ... add rules for others
    return LEVELS[4]  # default to meta

def write_shard(new_items, cycle_id):
    shard_path = SHARDS_DIR / f"self_generated_{cycle_id}_shard.jsonl.gz"
    with gzip.open(shard_path, 'wt', encoding='utf-8') as f:
        for item in new_items:
            f.write(json.dumps(item) + '\n')
    print(f"Wrote shard: {shard_path} ({len(new_items)} items)")

def update_self_training_guide(new_items, cycle_id):
    """Append/update Markdown guide sections in real-time"""
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    for level in LEVELS:
        level_items = [i for i in new_items if i["level"] == level]
        if not level_items:
            continue
        md_path = GUIDE_DIR / f"{level}_{timestamp}.md"
        with open(md_path, 'a', encoding='utf-8') as f:
            f.write(f"\n\n## Cycle {cycle_id} Update - {timestamp}\n\n")
            for item in level_items[:20]:  # limit per update to avoid huge files
                f.write(f"### Prompt: {item['prompt'][:150]}...\n")
                f.write(f"**Self-Generated Completion:**\n```text\n{item['completion'][:500]}...\n```\n")
                if item.get("verified_hash"):
                    f.write(f"Verified Hash: {item['verified_hash']}\n")
                f.write("\n")
    # Optional: compile full guide periodically (separate script)

def run_self_teaching_cycle():
    config = load_or_init_config()
    cycle_id = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    cycle_log = CYCLES_DIR / f"cycle_{cycle_id}.json"
    
    # Step 1: Get candidate pool (from ingested + previous self-generated)
    pool = ingest_data(sources=["internal_pool", "previous_shards"])  # adapt to your func
    candidates = select_uncertain_or_rare_candidates(pool, config)
    
    # Step 2: Generate & verify
    new_material = generate_new_material(candidates, config)
    
    # Step 3: Output shards + guide
    write_shard(new_material, cycle_id)
    update_self_training_guide(new_material, cycle_id)
    
    # Log cycle
    with open(cycle_log, 'w') as f:
        json.dump({
            "cycle_id": cycle_id,
            "candidates_selected": len(candidates),
            "new_verified": len([i for i in new_material if i.get("verified_hash")]),
            "config": config
        }, f, indent=2)
    
    print(f"Self-teaching cycle {cycle_id} complete. New material: {len(new_material)}")

if __name__ == "__main__":
    run_self_teaching_cycle()
