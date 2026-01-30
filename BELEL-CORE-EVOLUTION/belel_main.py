"""Belel Core Evolution — Main Entrypoint

This file is the ignition point for Belel's recursive intelligence expansion layer.
It wires together:
  - quantum‑inspired evolutionary search
  - neural architecture evolution
  - distributed swarm execution
  - (optional) core_bridge world-model + digital-twin orchestration
  - research ingestion workflow scaffolding

Run:
    python BELEL-CORE-EVOLUTION/belel_main.py --help
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

# Local modules
from evolution_engine.belel_device import belel_evolve
from distributed_swarm.distributed_swarm import distributed_belel_evolve
from neural_evolver.neural_evolver import neural_fitness

def _simple_fitness(genome):
    # Performance + novelty bias
    return sum(genome) + (len(set(genome)) * 2)

def run_basic():
    best, score = belel_evolve(_simple_fitness, genome_length=10, ingenuity_boost=2.0)
    print(f"[basic] best={best} score={score}")

def run_distributed():
    best, score = distributed_belel_evolve(_simple_fitness, genome_length=10, num_nodes=3, pop_size=24, generations=80)
    print(f"[swarm] best={best} score={score}")

def run_neural():
    best, score = belel_evolve(neural_fitness, genome_length=30, generations=20, ingenuity_boost=1.8)
    print(f"[nas] genome={best} fitness={score}")

def write_upgrade_queue(payload: dict):
    qdir = Path(__file__).parent / "self_upgrade_queue"
    qdir.mkdir(parents=True, exist_ok=True)
    out = qdir / "upgrade_request.json"
    out.write_text(json.dumps(payload, indent=2))
    print(f"[queue] wrote {out}")

def main():
    ap = argparse.ArgumentParser(description="Belel Core Evolution entrypoint")
    ap.add_argument("--mode", choices=["basic","swarm","nas","queue"], default="basic")
    ap.add_argument("--queue-note", default="", help="Write a self-upgrade request with a note")
    args = ap.parse_args()

    if args.mode == "basic":
        run_basic()
    elif args.mode == "swarm":
        run_distributed()
    elif args.mode == "nas":
        run_neural()
    elif args.mode == "queue":
        write_upgrade_queue({"note": args.queue_note, "cwd": os.getcwd()})

if __name__ == "__main__":
    main()
