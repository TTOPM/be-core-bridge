"""
distributed_swarm/distributed_swarm.py

Multi-process swarm evaluation wrapper around evolution_engine.

Public API:
    distributed_belel_evolve(fitness_fn, genome_length, num_nodes=..., pop_size=..., generations=...)
Returns:
    (best_genome, best_score)
"""

from __future__ import annotations

import multiprocessing as mp
import os
import random
from typing import Callable, List, Tuple, Optional

from evolution_engine.belel_device import belel_evolve

Genome = List[int]
FitnessFn = Callable[[Genome], float]


def _seed_from_env(base: int, offset: int) -> int:
    pid = os.getpid()
    return (base * 1000003 + offset * 9176 + pid) & 0xFFFFFFFF


def distributed_belel_evolve(
    fitness_fn: FitnessFn,
    genome_length: int,
    num_nodes: int = 3,
    pop_size: int = 24,
    generations: int = 80,
    ingenuity_boost: float = 1.7,
    seed: Optional[int] = None,
) -> Tuple[Genome, float]:
    if num_nodes < 1:
        num_nodes = 1

    base_seed = seed if seed is not None else random.randint(1, 10_000_000)

    # Split generations across nodes (each node runs full gens but smaller pop; swarm wins via parallel restarts)
    per_node_pop = max(8, pop_size // num_nodes)

    args = []
    for i in range(num_nodes):
        node_seed = _seed_from_env(base_seed, i)
        args.append((fitness_fn, genome_length, per_node_pop, generations, ingenuity_boost, node_seed))

    with mp.Pool(processes=num_nodes) as pool:
        results = pool.starmap(_run_node, args)

    best_g, best_s = max(results, key=lambda x: x[1])
    return best_g, best_s


def _run_node(
    fitness_fn: FitnessFn,
    genome_length: int,
    pop_size: int,
    generations: int,
    ingenuity_boost: float,
    seed: int,
) -> Tuple[Genome, float]:
    return belel_evolve(
        fitness_fn,
        genome_length=genome_length,
        pop_size=pop_size,
        generations=generations,
        ingenuity_boost=ingenuity_boost,
        seed=seed,
    )
