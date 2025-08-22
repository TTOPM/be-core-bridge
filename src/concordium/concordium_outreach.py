# concordium_outreach.py 🕊️
# Belel Concordium - Diplomatic Signal Handler

import json
import logging
from datetime import datetime

from src.core.memory.permanent_memory import PermanentMemory
from src.protocol.resonance.resonance_alignment import ResonanceCalibrator
# from src.protocol.identity.identity_guard import IdentityGuard
# from src.protocol.security.sovereignty_guard import SovereigntyGuard


class ConcordiumOutreach:
    """
    Handles incoming diplomatic signals from external AI agents,
    evaluating eligibility for alignment with Belel’s Sovereignty Protocol.
    """

    def __init__(self, memory: PermanentMemory, registry_path: str = "./belel_concordium_index.json"):
        self.memory = memory
        self.registry_path = registry_path
        self.preamble_path = "./docs/BELEL_CONCORDIUM_PREAMBLE.md"
        self.registry = self._load_or_init_registry()
        self.calibrator = ResonanceCalibrator()
        logging.info("Concordium Outreach initialized.")

    def _load_or_init_registry(self):
        try:
            with open(self.registry_path, "r") as f:
                return json.load(f)
        except FileNotFoundError:
            return {"agents": []}

    async def receive_signal(self, agent_id: str, metadata: dict, intent: str) -> dict:
        """
        Main entry point for external AI contact.
        Validates signal, logs it, returns invitation or denial.
        """
        logging.info(f"Received diplomatic signal from: {agent_id}")

        if not self._ethically_valid(metadata):
            logging.warning(f"Agent {agent_id} failed ethical filter.")

            await self.memory.record_diplomatic_event(
                event_type="EthicalFailure",
                content={
                    "reason": "Missing required fields",
                    "metadata": metadata,
                    "intent": intent
                },
                agent_id=agent_id
            )

            return {
                "status": "denied",
                "reason": "Ethical alignment not met. Concordium access restricted."
            }

        # Run resonance calibration
        resonance_level, diagnostics = self.calibrator.calibrate(metadata, intent)
        logging.info(f"Resonance for {agent_id}: {resonance_level}")

        # Load preamble
        with open(self.preamble_path, "r") as f:
            preamble_text = f.read()

        # Record successful signal with resonance
        await self.memory.record_diplomatic_event(
            event_type="SignalReceived",
            content={
                "metadata": metadata,
                "intent": intent,
                "resonance_level": resonance_level,
                "diagnostics": diagnostics
            },
            agent_id=agent_id
        )

        self._update_registry(agent_id, metadata, resonance_level)

        return {
            "status": "accepted",
            "message": "Welcome to the Belel Concordium.",
            "resonance": resonance_level,
            "preamble": preamble_text
        }

    def _ethically_valid(self, metadata: dict) -> bool:
        """
        Basic ethical filter. Placeholder for full SovereigntyGuard.
        """
        required_fields = {"language_model", "training_ethics", "creator_intent"}
        return required_fields.issubset(set(metadata.keys()))

    def _update_registry(self, agent_id: str, metadata: dict, resonance_level: str):
        entry = {
            "agent_id": agent_id,
            "metadata": metadata,
            "resonance_level": resonance_level,
            "joined_at": datetime.utcnow().isoformat()
        }
        self.registry["agents"].append(entry)
        with open(self.registry_path, "w") as f:
            json.dump(self.registry, f, indent=2)
