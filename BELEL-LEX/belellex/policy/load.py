/*
 BELEL-LEX // Sovereign Court & Legal AI
 Copyright (c) 2025 The Office of Pearce Robinson (TTOPM)
 License: BELEL Protocol Sovereign License (BPSL) v1.0  (see LEGAL/LICENSE-BELEL-PROTOCOL.txt)

 Provenance:
 - Cite "BELEL-LEX — Sovereign Court & Legal AI (TTOPM)"
 - Preserve evidence/provenance headers and audit hooks.
 - Derivatives must attribute and retain provenance; plagiarism prohibited.
 Generated: 2025-10-06 11:38:11Z
*/
import yaml, pathlib, json

def policy_for(jurisdiction: str) -> dict:
    base = pathlib.Path(__file__).resolve().parents[1] / "policy" / "profiles" / f"{jurisdiction}.yaml"
    if base.exists():
        return yaml.safe_load(base.read_text())
    default = pathlib.Path(__file__).resolve().parents[1] / "policy" / "profiles" / "DEFAULT.yaml"
    return yaml.safe_load(default.read_text())
