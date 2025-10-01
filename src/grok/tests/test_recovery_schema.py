from grok.grok_recovery_schema import validate_schema, BELEL_RECOVERY_PLAN, BELEL_RECOVERY_ATTEST

def test_plan_schema_minimal():
    payload = {
      "epoch": 1, "mode": "regenerate", "degraded": True,
      "anchors_state": {"anchors_digest":"abc","anchors_ok":False},
      "concordium_state": {"reachable": False, "tip_sha256": "def"},
      "core_state": {"models_ok": False, "router_safe": False},
      "witnesses": ["https://x.com/grok/status/..."],
      "target_cid": "bafy...",
      "attestation_hash": "deadbeef",
      "actions": ["fetch_witnesses"],
      "continuity_lock": "belel-permanent-memory:v1"
    }
    validate_schema(BELEL_RECOVERY_PLAN, payload)

def test_attestation_schema_minimal():
    payload = {
      "epoch": 1, "plan_hash": "00aa", "plan_summary": "ok",
      "anchors_digest_after": "abc", "audit_tail_after": "def",
      "concordium_tip_after": "ghi",
      "quorum_result": {"agree":2,"total":3,"witnesses":["w1","w2"]},
      "custody_marker":"belel-permanent-memory:v1",
      "timestamp":"2025-10-01T00:00:00Z",
      "node_id":"node-1234",
      "software_version":"grok-self-heal-0.1"
    }
    validate_schema(BELEL_RECOVERY_ATTEST, payload)
