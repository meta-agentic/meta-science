#!/usr/bin/env python3
"""Build the evidence base.

Recording one run at a time is a capability; a paper needs a population. This sweeps
worlds and strategy settings and records every encounter, so a claim can be tested
against N rather than against an anecdote.

Offline by default — the heuristic reasoner needs no API key, so anyone can regenerate
the dataset from the code alone. That matters more here than using the better reasoner:
a result nobody else can reproduce is not a result.

    python3 scripts/collect.py --worlds 48
    python3 scripts/collect.py --worlds 48 --out runs/study
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from metascience.discovery import run_discovery, score_on_held_out  # noqa: E402
from metascience.experiment import record_discovery, summarise  # noqa: E402
from metascience.ledger import FileLedger  # noqa: E402
from metascience.reasoner import HeuristicReasoner  # noqa: E402
from metascience.strategy import Strategy  # noqa: E402
from metascience.templates import TEMPLATE_IDS, generate  # noqa: E402

# Each arm varies ONE thing against the champion, so a difference in the results has one
# candidate explanation rather than several.
ARMS = [
    ("champion", {}),
    ("frugal-100", {"samples_per_arm": 100}),
    ("lean-25", {"samples_per_arm": 25}),
    ("paired-champion", {"paired_arms": True}),
    ("paired-lean-25", {"paired_arms": True, "samples_per_arm": 25}),
    ("blunt", {"effect_threshold": 2.5}),
    ("sensitive", {"effect_threshold": 0.05}),
    ("no-screening", {"screen_observationally": False}),
]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--worlds", type=int, default=48, help="worlds per arm")
    ap.add_argument("--out", default="runs/study")
    ap.add_argument("--offset", type=int, default=50_000,
                    help="seed offset; kept clear of the held-out benchmark range")
    args = ap.parse_args()

    ledger = FileLedger(args.out)
    reasoner = HeuristicReasoner()
    seeds = [args.offset + i for i in range(args.worlds)]
    started = time.time()
    n = 0

    for arm_name, kwargs in ARMS:
        strategy = Strategy(name=arm_name, **kwargs)
        for seed in seeds:
            world = generate(seed)
            run = run_discovery(world, reasoner, strategy, seed=seed)
            variables = list(world.observable)
            probes = [(variables[0], 0.5), (variables[0], -0.5)]
            if len(variables) > 1:
                probes.append((variables[1], 0.5))
            held_out = score_on_held_out(world, run, probes, seed=seed + 5000)
            record_discovery(ledger, world, run, held_out, strategy,
                             models={"reasoner": "heuristic"},
                             notes=f"study arm {arm_name}")
            n += 1
        print(f"  {arm_name:18s} {len(seeds)} worlds recorded")

    records = ledger.experiments(limit=10_000)
    s = summarise(records)
    print(f"\n{n} records in {time.time() - started:.0f}s -> {args.out}/experiments/")
    print(f"  templates covered      {len(TEMPLATE_IDS)}")
    print(f"  hypotheses tested      {s['hypotheses_tested']}")
    print(f"  refuted by experiment  {s['hypotheses_refuted']}  ({s['refutation_rate']})")
    print("  direction accuracy by template:")
    for tid, v in s["direction_accuracy_by_template"].items():
        print(f"    {tid}  mean {v['mean']:.4f}  n {v['n']}")


if __name__ == "__main__":
    main()
