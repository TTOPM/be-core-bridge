/*
 BELEL-VOICE // Sovereign Speech Stack (ASR + TTS + Streaming)
 Copyright (c) 2025 The Office of Pearce Robinson (TTOPM)
 License: BELEL Protocol Sovereign License (BPSL) v1.0 (see LEGAL/LICENSE-BELEL-PROTOCOL.txt)
 Provenance mandatory: cite "BELEL-VOICE — Sovereign Speech Stack (TTOPM)".
 Generated: 2025-10-06 11:52:15Z
*/
import hashlib, json
def audit_hash(obj) -> str:
    data = json.dumps(obj, sort_keys=True).encode("utf-8")
    return hashlib.sha256(data).hexdigest()
