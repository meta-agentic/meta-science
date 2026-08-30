"""The whole argument, in one command, in the order the video needs it.

Five beats:
  1  what the agent is allowed to see          (nothing retrievable)
  2  observation alone gets it backwards       (the trap)
  3  intervention gets it right                (the refutation)
  4  the agent improves its own method         (promotion)
  5  and is refused when it overreaches        (the point)
"""
from __future__ import annotations

import argparse
import statistics as st
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from metascience.config import load_env, model_name  # noqa: E402
from metascience.discovery import run_discovery  # noqa: E402
from metascience.evolution import (ScriptedProposer, evaluate_strategy,  # noqa: E402
                                   held_out_seeds, run_generation)
from metascience.ledger import FileLedger, PromotionGate  # noqa: E402
from metascience.reasoner import HeuristicReasoner  # noqa: E402
from metascience.strategy import Strategy  # noqa: E402
from metascience.templates import generate  # noqa: E402

BOLD, DIM, GREEN, RED, CYAN, OFF = (
    "\033[1m", "\033[2m", "\033[32m", "\033[31m", "\033[36m", "\033[0m")


def rule(n: int, title: str) -> None:
    print(f"\n{BOLD}{CYAN}[{n}] {title}{OFF}\n{DIM}{'─' * 68}{OFF}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--live", action="store_true", help="use Gemini for the proposals")
    args = ap.parse_args()
    load_env()

    world = generate(args.seed, "T6")
    cause, effect = world.observable

    rule(1, "What the agent is allowed to know")
    print(f"  {world.describe()}")
    print(f"{DIM}  No names, no units, no documentation. Two affordances: look, or act.{OFF}")

    rule(2, "What passive observation says")
    obs = world.observe(3000, seed=1)
    corr = st.correlation([r[cause] for r in obs], [r[effect] for r in obs])
    print(f"  corr({cause}, {effect}) = {RED}{corr:+.3f}{OFF}")
    print(f"{DIM}  Strong, clean, and completely wrong. A hidden common cause is doing it.{OFF}")

    rule(3, "What the agent finds when it acts")
    run = run_discovery(world, HeuristicReasoner(), Strategy(), seed=args.seed)
    for e in run.experiments:
        h = e.hypothesis
        colour = RED if e.refuted else GREEN
        print(f"  predicted {h.cause}->{h.effect} sign {h.predicted_sign:+d}  "
              f"measured {e.observed_effect:+.3f}  {colour}{e.verdict}{OFF}")
    print(f"{DIM}  The prediction was written down before the experiment ran. "
          f"The verdict is a comparison,{OFF}")
    print(f"{DIM}  not a question put to the model.{OFF}")

    rule(4, "The agent proposes a change to its own method")
    seeds = held_out_seeds(24)
    ledger = FileLedger("runs/demo")
    gate = PromotionGate(ledger, evaluate_strategy, margin=0.02)
    champion = Strategy()
    print(f"  champion {champion.name}: {evaluate_strategy(champion, seeds):+.4f}"
          f"   {DIM}({len(seeds)} held-out worlds, never shown to the proposer){OFF}")

    if args.live:
        from metascience.gemini import GeminiProposer
        proposer, note = GeminiProposer(), f"Gemini {model_name()}"
    else:
        proposer = ScriptedProposer([("frugal-v2", {"samples_per_arm": 100}),
                                     ("greedy-v3", {"effect_threshold": 2.5})])
        note = "scripted (offline)"
    print(f"{DIM}  proposer: {note}{OFF}\n")

    for i in range(2):
        champion, r = run_generation(ledger, gate, champion, proposer, seeds)
        if i == 1:
            rule(5, "And is refused when the evidence does not support it")
        colour = GREEN if r.verdict == "PROMOTED" else RED
        print(f"  {colour}{r.verdict:9s}{OFF} {r.candidate}   {r.diff}")
        print(f"            champion {r.champion_score:+.4f}   "
              f"challenger {r.challenger_score:+.4f}")
        print(f"{DIM}            {r.reason}{OFF}")
        print(f"{DIM}            receipt {r.digest()}{OFF}\n")

    canon = ledger.canon().get("strategy", {}).get("name", champion.name)
    print(f"{BOLD}  canon holds: {canon}{OFF}")
    print(f"{DIM}  A refused proposal changed nothing. That is the whole claim.{OFF}\n")


if __name__ == "__main__":
    main()
