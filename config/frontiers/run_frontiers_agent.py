"""
Frontiers Agent Runner
======================

This script launches an interactive command-line session using the
FrontiersAgent. Users can type queries to invoke the meta-orchestrator
directly. A heartbeat task runs in the background if configured, issuing
automatic queries at intervals.
"""

from __future__ import annotations

import asyncio

from src.frontiers.agent.frontiers_agent import FrontiersAgent


def main() -> int:
    agent = FrontiersAgent()
    asyncio.run(agent.interactive_loop())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())