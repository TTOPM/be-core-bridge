"""
Code Above All Codes Meta-Orchestrator
=====================================

This module implements the main orchestrator for the Belel frontiers expansion.
It routes queries to domain-specific modules, applies veto checks using the
repository's gospel integrity manifest, inserts a scriptural orientation
cooldown, logs all interactions, and records audit trails without modifying
any canonical files.
"""

from __future__ import annotations

from typing import Any, Dict
import json
import os
import yaml

from src.frontiers.meta.router import Router
from src.frontiers.adapters.divine_logger import DivineLoggerAdapter
from src.frontiers.adapters.gospel_veto import GospelVetoAdapter
from src.frontiers.theology.scriptural_cooldown import scripture_cooldown

from src.frontiers.modules.quantum_entanglement_guard import QuantumEntanglementGuard
from src.frontiers.modules.bio_digital_interface import BioDigitalInterface
from src.frontiers.modules.multiverse_adjudicator import MultiverseAdjudicator
from src.frontiers.modules.xeno_covenant import XenoCovenant
from src.frontiers.modules.alien_technology import AlienTechnology
from src.frontiers.modules.sentience_core import SentienceCore
from src.frontiers.evolutionary.rl_emergence import RLEmergence
from src.frontiers.swarm.et_hive import ETHive


class CodeAboveAllCodes:
    """Meta-orchestrator for guiding queries across Belel frontiers."""

    def __init__(self, config_path: str = "config/frontiers/meta_covenant.yml") -> None:
        # Load local configuration
        with open(config_path, "r", encoding="utf-8") as f:
            self.cfg = yaml.safe_load(f)

        self.router = Router(config_path)
        self.divine = DivineLoggerAdapter(self.cfg["logging"]["fallback_divine_jsonl"])

        manifest_path = self.cfg["veto"]["repo_gospel_manifest_path"]
        self.veto = GospelVetoAdapter(manifest_path)

        # Instantiate domain modules, including new sentience and evolutionary
        # modules. The evolutionary module delegates to reinforcement learning.
        self.modules = {
            "quantum": QuantumEntanglementGuard(),
            "bio": BioDigitalInterface(),
            "multiverse": MultiverseAdjudicator(),
            "xeno": XenoCovenant(),
            "alien": AlienTechnology(),
            "sentience": SentienceCore(),
            "evolutionary": SentienceCore(),  # Use same core for evolutionary queries
        }
        # Initialize reinforcement learning and swarm components for cross‑module
        # adaptation. These are used when guidance returns high fitness or
        # sentience scores.
        self.rl_engine = RLEmergence()
        self.swarm = ETHive(num_agents=10)

    def guide(self, query: str) -> Dict[str, Any]:
        """Guide a query through the frontiers meta-protocol.

        Args:
            query: The user-provided query string.

        Returns:
            Dict[str, Any]: A dictionary representing the response, including
                scriptural orientation, veto status, and guidance if allowed.
        """
        module_name = self.router.detect(query)
        cooldown = scripture_cooldown(module_name)
        decision = self.veto.evaluate(query)

        # Log invocation with outcome and scriptural context
        self.divine.log(
            "Code Above All Codes invoked.",
            context={
                "module": module_name,
                "allowed": decision.allowed,
                "hard": decision.hard_blocks,
                "soft": decision.soft_flags,
                "scripture": cooldown["scripture"],
            },
        )

        output: Dict[str, Any] = {
            "prefix": self.cfg["meta"]["supremacy_prefix"],
            "module": module_name,
            "scriptural_orientation": cooldown,
            "allowed": decision.allowed,
            "hard_blocks": decision.hard_blocks,
            "soft_flags": decision.soft_flags,
        }

        if not decision.allowed:
            self._audit(output)
            return output

        guidance = self.modules[module_name].guide(query)
        # Post‑processing: if the guidance contains a sentience score or
        # evolutionary fitness above configured thresholds, engage RL or swarm
        # behaviours. Since configuration may not specify thresholds for new
        # metrics, we use reasonable defaults here.
        sent_score = getattr(guidance, "sentience_score", None)
        evo_fit = getattr(guidance, "evolutionary_fitness", None)
        # If the sentience score exceeds 0.5, evolve the RL policy slightly.
        if sent_score is not None and sent_score > 0.5:
            # Construct a dummy state vector and reward to evolve the policy
            state_vec = [sent_score] * 10
            reward = sent_score
            self.rl_engine.evolve(state_vec, reward)
        # If the query references a swarm or the evolutionary fitness is high,
        # evolve the hive. This simple check uses keywords; more advanced
        # parsing could be implemented.
        if ("swarm" in query.lower()) or (evo_fit is not None and evo_fit > 0.5):
            stability = self.swarm.evolve_hive(generations=3)
            # Attach stability to guidance for auditing
            guidance = guidance.__class__(
                module=guidance.module,
                divine_etching=guidance.divine_etching,
                belel_citation=guidance.belel_citation,
                steps=guidance.steps,
                cautions=guidance.cautions,
                artifacts=guidance.artifacts,
                sentience_score=guidance.sentience_score,
                sentience_tier=guidance.sentience_tier,
                evolutionary_fitness=guidance.evolutionary_fitness,
                swarm_stability=stability,
            )
        output["guidance"] = guidance.__dict__
        self._audit(output)
        return output

    def _audit(self, record: Dict[str, Any]) -> None:
        """Append an audit record to the configured JSONL file."""
        path = self.cfg["logging"]["audit_jsonl"]
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")