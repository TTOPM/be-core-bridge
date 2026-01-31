cat > BELEL_DATASET_ACADEMY/docs/architecture.md <<'EOF'
# Architecture

BELEL Database Academy is a pipeline with explicit evidence paths.

## Flow
1. Ingest: streaming corpora + owned domain corpora
2. Process: normalize schema, apply mandate, tag domain/hardness
3. Verify: execute verifiers under policy
4. Reflex: generate candidates, score, synthesize preference pairs
5. Train: SFT → DPO/ORPO
6. Evaluate: lm-eval + domain eval sets
7. Manifest: lineage index + regression tracking

## Artifacts
- `assets/system-architecture.*` preview diagram
- `evaluation/` runner + registry
- `metrics/` outputs + charts
EOF
