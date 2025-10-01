#!/usr/bin/env bash
set -euo pipefail
ARTIFACT="${1:-attest/ledger.jsonl}"
cosign sign-blob --yes --key cosign.key "$ARTIFACT" > "${ARTIFACT}.sig"
echo "Signed: ${ARTIFACT}.sig"
