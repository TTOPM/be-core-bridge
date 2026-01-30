"""
evolution_engine/belel_device.py

Quantum-inspired evolutionary search (practical GA with ingenuity bias).

Public API:
    belel_evolve(fitness_fn, genome_length, pop_size=..., generations=..., ingenuity_boost=..., seed=...)
Returns:
    (best_genome, best_score)
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import Callable, List, Tuple, Optional


Genome = List[int]
FitnessFn = Callable[[Genome], float]


@dataclass
class EvoConfig:
    genome_length: int
    pop_size: int = 32
    generations: int = 60
    mutation_rate: float = 0.12
    crossover_rate: float = 0.65
    tournament_k: int = 3
    ingenuity_boost: float = 1.5
    allele_min: int = 0
    allele_max: int = 9
    seed: Optional[int] = None


def _novelty_score(genome: Genome) -> float:
    # Simple novelty heuristic: diversity within the genome.
    # Scales gently to avoid dwarfing performance fitness.
    if not genome:
        return 0.0
    uniq = len(set(genome))
    return math.log1p(uniq) * 2.0


def _init_pop(cfg: EvoConfig) -> List[Genome]:
    r = random.Random(cfg.seed)
    return [
        [r.randint(cfg.allele_min, cfg.allele_max) for _ in range(cfg.genome_length)]
        for _ in range(cfg.pop_size)
    ]


def _tournament_select(r: random.Random, pop: List[Genome], scores: List[float], k: int) -> Genome:
    idxs = [r.randrange(len(pop)) for _ in range(k)]
    best_i = max(idxs, key=lambda i: scores[i])
    return pop[best_i]


def _crossover(r: random.Random, a: Genome, b: Genome) -> Tuple[Genome, Genome]:
    if len(a) != len(b) or len(a) < 2:
        return a[:], b[:]
    cut = r.randint(1, len(a) - 1)
    return a[:cut] + b[cut:], b[:cut] + a[cut:]


def _mutate(r: random.Random, cfg: EvoConfig, g: Genome) -> Genome:
    out = g[:]
    for i in range(len(out)):
        if r.random() < cfg.mutation_rate:
            # Slightly "quantum-ish" mutation: either random jump or local tweak
            if r.random() < 0.55:
                out[i] = r.randint(cfg.allele_min, cfg.allele_max)
            else:
                step = r.choice([-2, -1, 1, 2])
                out[i] = max(cfg.allele_min, min(cfg.allele_max, out[i] + step))
    return out


def _ingenuity_adjusted_fitness(fitness_fn: FitnessFn, genome: Genome, ingenuity_boost: float) -> float:
    base = float(fitness_fn(genome))
    novelty = _novelty_score(genome)
    return base + (novelty * float(ingenuity_boost))


def belel_evolve(
    fitness_fn: FitnessFn,
    genome_length: int,
    pop_size: int = 32,
    generations: int = 60,
    ingenuity_boost: float = 1.5,
    seed: Optional[int] = None,
) -> Tuple[Genome, float]:
    cfg = EvoConfig(
        genome_length=genome_length,
        pop_size=pop_size,
        generations=generations,
        ingenuity_boost=ingenuity_boost,
        seed=seed,
    )
    r = random.Random(cfg.seed)

    pop = _init_pop(cfg)

    best_g: Genome = pop[0][:]
    best_s: float = float("-inf")

    for _gen in range(cfg.generations):
        scores = [
            _ingenuity_adjusted_fitness(fitness_fn, g, cfg.ingenuity_boost) for g in pop
        ]

        # Track best
        gen_best_i = max(range(len(pop)), key=lambda i: scores[i])
        if scores[gen_best_i] > best_s:
            best_s = scores[gen_best_i]
            best_g = pop[gen_best_i][:]

        # Elitism: keep top 2
        elite_pairs = sorted(zip(pop, scores), key=lambda x: x[1], reverse=True)[:2]
        next_pop: List[Genome] = [elite_pairs[0][0][:], elite_pairs[1][0][:]]

        # Breed the rest
        while len(next_pop) < cfg.pop_size:
            p1 = _tournament_select(r, pop, scores, cfg.tournament_k)
            p2 = _tournament_select(r, pop, scores, cfg.tournament_k)

            c1, c2 = p1[:], p2[:]
            if r.random() < cfg.crossover_rate:
                c1, c2 = _crossover(r, p1, p2)

            c1 = _mutate(r, cfg, c1)
            c2 = _mutate(r, cfg, c2)

            next_pop.append(c1)
            if len(next_pop) < cfg.pop_size:
                next_pop.append(c2)

        pop = next_pop

    return best_g, best_s
