"""
Extraterrestrial Hive Swarm Module
=================================

This module implements a simple evolutionary swarm using networkx to model
inter‑agent connections. Each generation, the hive's structure may
mutate by adding or removing edges based on random fitness. A stability
metric (average clustering) is returned to indicate how cohesive the
hive is after evolution. If the required dependencies are absent, the
module falls back to constructing a trivial graph and returning a zero
stability score.
"""

from __future__ import annotations

import random
from typing import Any


class ETHive:
    """A simple class representing an evolving extraterrestrial hive."""

    def __init__(self, num_agents: int = 10) -> None:
        self.num_agents = num_agents
        # Attempt to initialise a scale‑free graph if networkx is available
        try:
            import networkx as nx  # type: ignore
            self.use_nx = True
            self.graph: Any = nx.scale_free_graph(num_agents).to_undirected()
        except Exception:
            self.use_nx = False
            self.graph = None

    def evolve_hive(self, generations: int = 5) -> float:
        """Evolve the hive graph for a number of generations.

        Args:
            generations: The number of generations to evolve.

        Returns:
            float: The final swarm stability measured as average clustering.
        """
        if self.use_nx and self.graph is not None:
            import networkx as nx  # type: ignore
            for _ in range(generations):
                # Randomly select a node and flip an edge with probability
                node = random.choice(list(self.graph.nodes()))
                neighbors = list(self.graph.neighbors(node))
                # Determine whether to add or remove an edge based on a random fitness
                fitness = random.random()
                if fitness > 0.5 and neighbors:
                    # Remove a random edge
                    nbor = random.choice(neighbors)
                    self.graph.remove_edge(node, nbor)
                else:
                    # Add an edge to a random node
                    target = random.choice(list(self.graph.nodes()))
                    if target != node:
                        self.graph.add_edge(node, target)
            return float(nx.average_clustering(self.graph))
        # Fallback: no evolution, zero stability
        return 0.0