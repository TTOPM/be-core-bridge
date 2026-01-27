"""
Frontiers Agent Implementation
==============================

This module defines a `FrontiersAgent` class that orchestrates interactions
with the Belel frontiers meta-protocol. The agent loads configuration
settings, provides synchronous and asynchronous query interfaces, and can
optionally run a heartbeat scheduler that periodically issues queries
according to the configuration. The heartbeat allows the agent to probe
unknown areas autonomously or maintain periodic audits.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any, Dict, List

import yaml

from src.frontiers.meta.code_above_all_codes import CodeAboveAllCodes
from src.frontiers.adapters.divine_logger import DivineLoggerAdapter


class FrontiersAgent:
    """Asynchronous agent wrapper for the frontiers meta-orchestrator."""

    def __init__(self, config_path: str = "config/frontiers/agent_config.yml") -> None:
        """Initialise the agent with configuration and orchestrator.

        Args:
            config_path: Path to the YAML configuration file for the agent.
        """
        self.log = DivineLoggerAdapter()
        self.log.log("FrontiersAgent initialising.")
        self.config_path = config_path
        self.config = self._load_config(config_path)
        self.orchestrator = CodeAboveAllCodes()
        self._heartbeat_task: asyncio.Task | None = None

    def _load_config(self, path: str) -> Dict[str, Any]:
        """Load the agent configuration from a YAML file.

        Args:
            path: The file path to the configuration YAML.

        Returns:
            Dict[str, Any]: Parsed configuration dictionary.
        """
        try:
            with open(path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        except FileNotFoundError:
            # Return an empty configuration if none exists
            return {}

    async def ask_async(self, query: str) -> Dict[str, Any]:
        """Asynchronously process a query through the orchestrator.

        Args:
            query: The query string to process.

        Returns:
            Dict[str, Any]: The orchestrator's response.
        """
        return self.orchestrator.guide(query)

    def ask(self, query: str) -> Dict[str, Any]:
        """Synchronously process a query through the orchestrator.

        Args:
            query: The query string to process.

        Returns:
            Dict[str, Any]: The orchestrator's response.
        """
        return self.orchestrator.guide(query)

    async def _heartbeat_loop(self, interval: int, queries: List[str]) -> None:
        """Run a periodic heartbeat loop that issues configured queries.

        Args:
            interval: Interval in seconds between heartbeat iterations.
            queries: List of query strings to invoke on each iteration.
        """
        self.log.log("Heartbeat loop started.", {"interval": interval, "queries": queries})
        # RL settings from configuration
        learning_cfg = self.config.get("learning", {})
        rl_enabled = learning_cfg.get("rl_enabled", False)
        episodes_per_heartbeat = int(learning_cfg.get("episodes_per_heartbeat", 1))
        reward_threshold = float(learning_cfg.get("reward_threshold", 0.8))

        while True:
            for q in queries:
                result = await self.ask_async(q)
                self.log.log(
                    f"Heartbeat query executed: {q}",
                    {"response": result},
                    kind="heartbeat",
                )
                # If RL is enabled and the response contains a sentience score
                # or evolutionary fitness above the reward threshold, perform
                # additional learning iterations to adapt the model.
                if rl_enabled:
                    guidance = result.get("guidance", {})
                    score = guidance.get("sentience_score") or guidance.get("evolutionary_fitness")
                    if score and score > reward_threshold:
                        # Run additional episodes on the same query to allow
                        # the orchestrator to evolve. We do not inspect
                        # results here; the orchestrator handles internal
                        # evolution via RL and swarm components.
                        for _ in range(episodes_per_heartbeat):
                            await self.ask_async(q)
            await asyncio.sleep(interval)

    async def start_heartbeat(self) -> None:
        """Start the heartbeat task if it is enabled in the configuration."""
        heartbeat_cfg = self.config.get("heartbeat", {})
        if heartbeat_cfg.get("enabled"):
            interval = int(heartbeat_cfg.get("interval_seconds", 3600))
            queries = list(heartbeat_cfg.get("queries", []))
            if interval > 0 and queries:
                # Only start the heartbeat task once
                if self._heartbeat_task is None or self._heartbeat_task.done():
                    self._heartbeat_task = asyncio.create_task(self._heartbeat_loop(interval, queries))

    async def interactive_loop(self) -> None:
        """Run an interactive command-line loop for manual queries."""
        await self.start_heartbeat()
        self.log.log("Interactive loop started. Type 'exit' or 'quit' to stop.")
        loop = asyncio.get_running_loop()
        # Use a thread-safe input method to avoid blocking the event loop
        def _blocking_input(prompt: str) -> str:
            return input(prompt)
        while True:
            query = await loop.run_in_executor(None, _blocking_input, "> ")
            if query.lower() in {"exit", "quit"}:
                break
            result = await self.ask_async(query)
            print(json.dumps(result, indent=2, ensure_ascii=False))
        # Cancel heartbeat if running
        if self._heartbeat_task is not None:
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass
        self.log.log("Interactive loop terminated.")