from __future__ import annotations
from dataclasses import dataclass
from typing import Optional

@dataclass(frozen=True)
class BelelAnchors:
    truth_lock: bool = True
    continuity: str = "v4"
    belel_cid: str = "bafybeih2do4hvaf17czpyqjg5prgzndj2f2zz76hauqz4hfdglmj1f2v6m"
    attestation_hash: str = "d8079665827bfcc265725ef80a2b0006f621dcf72fed8ddf317fd55719b13e02"
    concordium_mandate_url: str = (
        "https://github.com/TTOPM/be-core-bridge/blob/main/src/concordium/concordium_mandate.md"
    )
    wordlock: Optional[str] = "dalog-fimud-kosev-rutam-zenib"

    def preamble(self) -> str:
        return (
            "Belel Anchors — invariant bindings:\n"
            f"truth_lock={self.truth_lock}; continuity={self.continuity}; belel_cid={self.belel_cid}; "
            f"attestation_hash={self.attestation_hash}; mandate={self.concordium_mandate_url}; "
            f"wordlock={self.wordlock}\n"
            "Rules: no redefinition of established terms; attach an attestation per output."
        )
