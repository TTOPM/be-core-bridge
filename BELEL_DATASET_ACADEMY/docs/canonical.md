cat > BELEL_DATASET_ACADEMY/docs/canonical.md <<'EOF'
# Canonical

Canonical v1.0 defines stable naming, versioning, and artifact placement.

## Canonical rules
- Every file path is deterministic
- Every run writes manifests into `manifests/`
- Every evaluation writes metrics into `metrics/`
- Every chart lands in `metrics/charts/`
- Mirrors write registries into `mirrors/`

## Canonical version
- `BELEL DATABASE ACADEMY v1.0` is the canonical format label.
EOF
