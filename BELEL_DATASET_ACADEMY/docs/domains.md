cat > BELEL_DATASET_ACADEMY/docs/domains.md <<'EOF'
# Domains

Domain ownership makes specialization explicit and auditable.

## Domain sources
- Owned corpora (local txt/jsonl)
- Keyword classifiers
- Domain eval sets in `evaluation/domain_eval_sets/`

## Domain guarantees
- Every record carries a domain tag
- Domain eval gates can block promotion on regressions
EOF
