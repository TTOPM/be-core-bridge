# Runbooks

## High violation rate
1. Check OpenAI latency/health.
2. Inspect `gateway/validate_response.py` failures.
3. Review recent changes in prompts/tools/schemas.

## Attestation signature mismatch
1. Rotate keys (`attest/sign.py:gen_keys`), update public key, re‑sign latest batch.
2. Verify CI provenance on artifacts.
