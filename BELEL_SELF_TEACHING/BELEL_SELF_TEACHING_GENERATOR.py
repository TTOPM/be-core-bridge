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

# Enhancements (6.1–6.5)
from .uncertainty import disagreement_uncertainty
from .rare_signal import extract_signals, update_counts, compute_rare_index, load_rare_index, rarity_score
from .code_coverage import coverage_verify
from .diversity import DiversityGate
from .quarantine import quarantine_record

BASE = Path("BELEL_SELF_TEACHING")
CFG_DIR = BASE / "config"
GUIDE_LEVELS = BASE / "guide" / "levels"
GUIDE_COMPILED = BASE / "guide" / "compiled"
CYCLES = BASE / "cycles"
OUT_SFT = BASE / "generated_shards" / "sft"
OUT_DPO = BASE / "generated_shards" / "dpo"
OUT_NEG = BASE / "generated_shards" / "negatives"
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
    IDX_DIR.mkdir(parents=True, exist_ok=True)
    seen_path = IDX_DIR / "seen_hashes.jsonl"
    with seen_path.open("a", encoding="utf-8") as f:
        for h in new_hashes:
            f.write(h + "\n")


def run_self_teaching_cycle(belel_core):
    """
    belel_core must supply:
      - ingest_data(sources=[...]) -> List[dict] with {prompt, tags?, domain?, metadata?}
      - apply_mandate(text) -> {"allowed": bool, "reasons": [...]}
      - verify_execution(text) -> {"passed": bool, "signals":..., "errors":...}
      - generate_reflexive_variant(prompt, mode=...) -> str

    Optional but recommended:
      - sandbox_run_python(code: str) -> {"passed": bool, "stdout":..., "stderr":...}
    """

    config = load_json(CFG_DIR / "self_teaching_config.json", {
        "budget_per_cycle": 300,
        "variants_per_prompt": 3,

        # selection mixer
        "mix": {"uncertainty": 0.55, "rarity": 0.20, "failure_replay": 0.20, "random": 0.05},

        # rarity + uncertainty
        "uncertainty_k": 4,
        "rare_percentile": 0.15,
        "rare_recompute_every_cycles": 1,  # simplest: recompute every cycle
        "rarity_min_tag": 0.2,

        # acceptance gates
        "rubric_min_total": 0.78,
        "keep_failures_rate": 0.15,

        # diversity anti-collapse
        "diversity_max_similarity": 0.92,

        # code coverage gates
        "require_mutation_kill_if_code": True,

        # quarantine
        "quarantine_enabled": True,

        # guide
        "compile_guide_every_cycle": True,
    })

    strategies = load_json(CFG_DIR / "strategies.json", {
        "sources": ["internal_pool", "previous_shards"],
        "domains_default": "general",
    })

    cycle_id = utc_cycle_id()
    cycle_dir = CYCLES / cycle_id.replace(":", "-")
    cycle_dir.mkdir(parents=True, exist_ok=True)

    ensure_level_files(GUIDE_LEVELS)

    # (6.2) Rare-signal index maintenance
    if config.get("rare_recompute_every_cycles", 1) == 1:
        compute_rare_index(percentile=config["rare_percentile"])
    rare_idx = load_rare_index()

    # (6.4) Diversity gate for anti-collapse
    div_gate = DiversityGate(max_similarity=config["diversity_max_similarity"], window=400)

    # Dedup index
    seen = load_seen_hashes()
    deduper = Deduper(seen, fuzzy_threshold=0.92)

    pool = belel_core.ingest_data(sources=strategies["sources"]) or []

    # Pre-tag pool items with rare-signal score so selector can use it (6.2)
    for it in pool:
        it.setdefault("tags", [])
        it["metadata"] = it.get("metadata", {}) or {}
        rs = rarity_score(it.get("prompt", ""), rare_idx)
        it["metadata"]["rare_score"] = rs
        if rs >= config.get("rarity_min_tag", 0.2) and "rare_signal" not in it["tags"]:
            it["tags"].append("rare_signal")

    # (6.1) Disagreement uncertainty computed per candidate (fast short generations)
    def short_gen(p: str) -> str:
        out = belel_core.generate_reflexive_variant(p, mode="generate")
        return out[:700]

    def verifier_short(text: str) -> dict:
        return belel_core.verify_execution(text)

    def rubric_fn(prompt: str, completion: str, ver: dict) -> dict:
        return rubric_score(prompt, completion, ver)

    for it in pool:
        p = it.get("prompt", "") or ""
        it["metadata"] = it.get("metadata", {}) or {}
        it["metadata"]["uncertainty_disagreement"] = disagreement_uncertainty(
            p,
            generator_short=short_gen,
            verifier_fn=verifier_short,
            rubric_fn=rubric_fn,
            k=config["uncertainty_k"],
        )

    def get_u(item):
        return float(item.get("metadata", {}).get("uncertainty_disagreement", 0.0))

    candidates = pick_candidates(
        pool=pool,
        budget=config["budget_per_cycle"],
        get_uncertainty_score=get_u,
        mix=config["mix"],
    )

    # Log selection for auditability
    (cycle_dir / "selection.jsonl").write_text(
        "\n".join(json.dumps(c, ensure_ascii=False) for c in candidates),
        encoding="utf-8"
    )

    sft_records = []
    dpo_records = []
    failures = []
    new_hashes_to_persist = []

    for cand in candidates:
        prompt = cand.get("prompt", "") or ""
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

            # mandate gate
            mandate = belel_core.apply_mandate(completion)
            if not mandate.get("allowed", True):
                # (6.5) quarantine if rubric would have passed but mandate fails is handled as mandate failure
                record = {
                    "prompt": prompt,
                    "completion": completion,
                    "domain": domain,
                    "tags": tags,
                    "metadata": cand.get("metadata", {}),
                    "mandate": mandate,
                }
                if config.get("quarantine_enabled", True):
                    quarantine_record(record, reason="failed_mandate", cycle_id=cycle_id, reverify=False)
                rejected_texts.append(completion)
                continue

            # dedup
            if deduper.is_exact_dup(completion) or deduper.is_fuzzy_dup(completion):
                continue

            # (6.4) diversity gate
            if not div_gate.allow(completion):
                continue

            # verify execution
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
                "mandate": mandate,
            }

            # (6.3) code test generation + mutation testing gate (if sandbox present)
            coverage = {}
            if hasattr(belel_core, "sandbox_run_python"):
                coverage = coverage_verify(
                    completion,
                    sandbox_run_python=belel_core.sandbox_run_python,
                    generate_reflexive_variant=belel_core.generate_reflexive_variant,
                )
                record["coverage"] = coverage

                if coverage.get("has_code"):
                    if not coverage.get("tests_passed"):
                        if config.get("quarantine_enabled", True):
                            quarantine_record(record, reason="code_tests_failed", cycle_id=cycle_id, reverify=True)
                        rejected_texts.append(completion)
                        continue

                    if config.get("require_mutation_kill_if_code", True) and not coverage.get("mutation_killed"):
                        if config.get("quarantine_enabled", True):
                            quarantine_record(record, reason="mutation_not_killed", cycle_id=cycle_id, reverify=True)
                        rejected_texts.append(completion)
                        continue

            # (6.5) quarantine: passes execution but fails rubric
            if ver.get("passed") and rub["total"] < config["rubric_min_total"]:
                if config.get("quarantine_enabled", True):
                    quarantine_record(record, reason="passed_execution_failed_rubric", cycle_id=cycle_id, reverify=False)
                rejected_texts.append(completion)
                continue

            # acceptance: verified AND rubric threshold
            if ver.get("passed") and rub["total"] >= config["rubric_min_total"]:
                sft_records.append(record)
                verified_texts.append(completion)

                # update dedup + diversity memory
                deduper.add_exact(completion)
                deduper.remember(completion)
                div_gate.remember(completion)
                new_hashes_to_persist.append(sha256_text(completion))

                # (6.2) update rare counts only on accepted samples
                sig = extract_signals(prompt + "\n" + completion)
                update_counts(sig)
            else:
                rejected_texts.append(completion)

                # optionally keep failures for negatives
                if config["keep_failures_rate"] > 0:
                    failures.append(record)

        # DPO building: verified vs rejected
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
                "tags": tags,
                "metadata": cand.get("metadata", {}),
            })

    # persist seen hashes
    persist_seen_hashes(new_hashes_to_persist)

    # Write shards
    OUT_SFT.mkdir(parents=True, exist_ok=True)
    OUT_DPO.mkdir(parents=True, exist_ok=True)
    OUT_NEG.mkdir(parents=True, exist_ok=True)

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
        "config": config,
    }, indent=2), encoding="utf-8")

    return {
        "cycle_id": cycle_id,
        "metrics": m,
        "paths": {
            "sft": str(sft_path),
            "dpo": str(dpo_path),
            "neg": str(neg_path),
            "cycle_dir": str(cycle_dir),
        }
    }

