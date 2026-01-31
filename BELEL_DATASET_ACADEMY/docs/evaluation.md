cat > BELEL_DATASET_ACADEMY/docs/evaluation.md <<'EOF'
# Evaluation

Evaluation is automated and produces machine-readable metrics.

## Tools
- `evaluation/lm_eval_runner.py` runs lm-eval and writes JSON
- Domain eval sets: `evaluation/domain_eval_sets/*.jsonl`
- Registry: `evaluation/eval_registry.py`

## Outputs
- `metrics/metrics.json`
- `metrics/benchmark_deltas.json`
- `metrics/regressions.json`
- `metrics/architecture_comparison.json`
EOF
