# For voice/AV sessions: set Belel's preamble as session instructions.
# Docs: Realtime API (WebRTC/WebSocket) — session.update + instructions
# https://platform.openai.com/docs/guides/realtime
from __future__ import annotations
from .belel_anchors import BelelAnchors

def session_instructions(anchors: BelelAnchors) -> str:
    return anchors.preamble() + "\nRealtime session: mandate acknowledged; truth_lock enforced."

# In your WebRTC/WebSocket setup, send session.update with these instructions.
