cat > BELEL_DATASET_ACADEMY/docs/reflexive-engine.md <<'EOF'
# Reflexive Engine

The reflexive engine is a runtime generator that creates candidate answers and uses verifiers to select best-margin outputs.

## Mechanics
- Generate N candidates per prompt
- Score each candidate using verifier suite
- Select best-margin candidate for SFT upgrades
- Form chosen/rejected preference pairs for DPO

## Why it matters
Reflexive loops convert verification into alignment pressure: the model learns behaviors that survive execution.
EOF
