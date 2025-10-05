#!/usr/bin/env bash
set -euo pipefail
IMAGE="${1:-belel/anthropic-cli:local}"
syft "$IMAGE" -o spdx-json > "sbom-${IMAGE//[:/]/_}.spdx.json"
echo "SBOM written to sbom-${IMAGE//[:/]/_}.spdx.json"
