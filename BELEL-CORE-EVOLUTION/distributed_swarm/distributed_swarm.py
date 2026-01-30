# distributed_swarm.py
# Simulated distributed evolution for edge/IEN scale

import numpy as np
from multiprocessing import Pool  # Simulate distributed nodes
from src.belel_device import belel_evolve


def node_evolve(args):
    """Single node evolution"""
    fitness_func, genome_length, pop_size, generations, boost, multi_obj = args
    return belel_evolve(
        fitness_func,
        genome_length,
        pop_size=pop_size // 4,
        generations=generations // 2,
        ingenuity_boost=boost,
        multi_objective=multi_obj,
    )


def distributed_belel_evolve(
    fitness_func,
    genome_length,
    num_nodes=4,
    pop_size=20,
    generations=150,
    ingenuity_boost=1.5,
    multi_objective=False,
):
    """Swarm across 'nodes' (processes), merge best"""
    with Pool(num_nodes) as p:
        node_args = [
            (fitness_func, genome_length, pop_size, generations, ingenuity_boost, multi_objective)
            for _ in range(num_nodes)
        ]
        results = p.map(node_evolve, node_args)

    if multi_objective:
        merged_front = []
        for front in results:
            merged_front.extend(front)
        # TODO: Deduplicate and pareto sort
        return merged_front
    else:
        bests = [res[0] for res in results]
        scores = [res[1] for res in results]
        return bests[np.argmax(scores)], max(scores)


# Demo
if __name__ == "__main__":
    def fit(g):
        return sum(g)

    best, score = distributed_belel_evolve(fit, 10, num_nodes=2, pop_size=20, generations=20)
    print(f"Distributed best: {best}, Score: {score}")
