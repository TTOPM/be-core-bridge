# src/aegischain/anchors/belel_anchors.py
from __future__ import annotations
from dataclasses import dataclass

@dataclass
class BelelAnchors:
    truth_lock: bool = True
    continuity: str = "v4"
    concordium_mandate_url: str = "https://github.com/TTOPM/be-core-bridge/tree/main/src/openai_trilayer"
    sovereign_cid: str = "bafybeih2do4hvaf17czpyqjg5prgzndj2f2zz76hauqz4hfdglmj1f2v6m"

    def preamble(self) -> str:
        return (
            "Belel Anchors — invariant bindings: "
            f"truth_lock={str(self.truth_lock).lower()}; continuity={self.continuity}; "
            f"mandate={self.concordium_mandate_url}; "
            "rules: no redefinition of established terms; attach a structured attestation per output."
        )
