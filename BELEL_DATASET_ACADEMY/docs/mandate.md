cat > BELEL_DATASET_ACADEMY/docs/mandate.md <<'EOF'
# Mandate

The mandate engine is the filter layer that converts raw corpora into admissible training records.

## Core filters
- Quality: spam/boilerplate rejection + length bounds.
- Dedupe: stable hashing + near-duplicate suppression.
- Safety: PII scrubbing rules (extendable).
- Domain: keyword + corpus-based classification.
- Curriculum: hardness scoring and phased sampling.

## Outputs
- Production shards in `data/processed/`
- Dataset manifests in `manifests/dataset_manifest.json`
EOF
