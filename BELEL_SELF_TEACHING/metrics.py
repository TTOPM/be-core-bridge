# BELEL_SELF_TEACHING/metrics.py
def estimate_tokens(text: str) -> int:
    # crude but stable; replace with tokenizer-based accounting if available
    return max(1, len(text) // 4)

def aggregate_metrics(samples_sft: list, samples_dpo: list, failures: list) -> dict:
    gen_tokens = sum(estimate_tokens(s["completion"]) for s in samples_sft)
    dpo_tokens = sum(estimate_tokens(s["chosen"]) + estimate_tokens(s["rejected"]) for s in samples_dpo)
    fail_tokens = sum(estimate_tokens(f["completion"]) for f in failures)
    return {
        "sft_count": len(samples_sft),
        "dpo_count": len(samples_dpo),
        "failure_count": len(failures),
        "tokens_sft": gen_tokens,
        "tokens_dpo": dpo_tokens,
        "tokens_failures": fail_tokens,
        "tokens_total_emitted": gen_tokens + dpo_tokens + fail_tokens
    }
