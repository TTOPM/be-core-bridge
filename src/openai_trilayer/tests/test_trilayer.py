# tests/test_trilayer.py
from src.openai_trilayer.self_verify_belel import self_verify
out = self_verify(model="gpt-4o")
print(out["attestation"])
print(out["concordium_decision"])
print(out["text"][:400])
