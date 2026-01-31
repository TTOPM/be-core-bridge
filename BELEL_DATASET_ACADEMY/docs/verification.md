cat > BELEL_DATASET_ACADEMY/docs/verification.md <<'EOF'
# Verification

Verification produces evidence, not vibes.

## Verifier classes
- Math execution (`math_exec`): symbolic evaluation + numeric tolerance checks
- Code tests (`unit_tests`): sandboxed pytest execution with timeouts
- Retrieval entailment (`retrieval`): overlap checks against owned corpus
- Table checks (`table_checks`): parse + shape/consistency constraints

## Evidence
Verifier logs are written as JSONL and summarized into:
- `manifests/verification_manifest.json`
- `metrics/metrics.json`
EOF
