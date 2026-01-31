cat > BELEL_DATASET_ACADEMY/docs/curriculum.md <<'EOF'
# Curriculum

Curriculum governs difficulty, domain balance, and verifier density.

## Signals
- Hardness proxy: length + numeric density + code token density
- Domain balance: enforce quotas per owned domain
- Verifier density: ensure verified anchors persist across shards

## Outputs
Curriculum decisions are recorded in:
- `manifests/dataset_manifest.json`
- `manifests/lineage_index.json`
EOF
