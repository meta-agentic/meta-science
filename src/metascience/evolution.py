"""Level 2 — the system proposing changes to its own method.

The score rewards two things at once: getting the causal directions right, and not
burning experiments to do it. That matters, because a metric that only rewards accuracy
can be maxed by brute force, and a strategy that wins by running more experiments has
not learned anything — it has just paid more. Efficiency is what makes the improvement
axis real.

The proposer never sees the held-out seeds and never computes the score. It proposes;
the gate decides.
"""
from __future__ import annotations

from typing import Protocol

from .discovery import run_discovery, score_on_held_out
from .reasoner import HeuristicReasoner, Reasoner
from .strategy import Strategy
from .templates import generate

# Cost is charged on TOTAL MEASUREMENT — experiments x arms x samples — not on the
# experiment count alone. Charging only experiments would leave sample size free, so a
# challenger could buy accuracy by drawing more data and look like it had learned
# something. Under this metric an improvement has to come from designing better
# experiments, not from paying for more of them.
MEASUREMENT_COST = 0.20
BUDGET_UNIT = 12 * 2 * 400   # the champion's full spend = 1.0 units


def evaluate_strategy(strategy: Strategy, world_seeds: list[int],
                      reasoner: Reasoner | None = None) -> float:
    """Mean score across held-out worlds. Deterministic given the seeds."""
    return evaluate_detailed(strategy, world_seeds, reasoner)["score"]


def evaluate_detailed(strategy: Strategy, world_seeds: list[int],
                      reasoner: Reasoner | None = None) -> dict:
    """The score with its parts kept separate.

    The composite alone cannot distinguish "spent less and kept the answers" from
    "spent less, lost accuracy, and the cost saving outran the loss". Those are exactly
    the two cases an audit exists to tell apart, so the parts travel with the verdict.
    """
    reasoner = reasoner or HeuristicReasoner()
    totals, accs, costs = [], [], []
    for seed in world_seeds:
        world = generate(seed)
        run = run_discovery(world, reasoner, strategy, seed=seed)
        variables = list(world.observable)
        probes = [(variables[0], 0.5), (variables[0], -0.5)]
        if len(variables) > 1:
            probes.append((variables[1], 0.5))
        scored = score_on_held_out(world, run, probes, seed=seed + 5000)
        samples_used = len(run.experiments) * 2 * strategy.samples_per_arm
        spend = samples_used / BUDGET_UNIT
        accs.append(scored["direction_accuracy"])
        costs.append(MEASUREMENT_COST * spend)
        totals.append(accs[-1] - costs[-1])
    n = len(totals)
    return {"score": sum(totals) / n,
            "accuracy": sum(accs) / n,
            "cost": sum(costs) / n,
            "worlds": n}


class Proposer(Protocol):
    def propose(self, champion: Strategy, notes: str) -> Strategy: ...


class ScriptedProposer:
    """Deterministic proposer used to prove the gate works in both directions.

    It emits a queue of candidates, some of which are deliberately bad. A gate that has
    only ever refused nothing is not a gate, so the bad ones are not an oversight —
    they are the test.
    """

    def __init__(self, queue: list[tuple[str, dict]]):
        self._queue = list(queue)

    def propose(self, champion: Strategy, notes: str = "") -> Strategy:
        if not self._queue:
            raise StopIteration("no candidates left")
        name, changes = self._queue.pop(0)
        return champion.child(name, **changes)


def held_out_seeds(n: int = 24, offset: int = 10_000) -> list[int]:
    """Worlds the proposer has never seen and cannot enumerate.

    n=24 covers each of the six templates four times. Smaller sets make a win
    indistinguishable from noise: at n=10 a single world flipping moves the mean by
    0.10, which is five times the promotion margin.
    """
    return [offset + i for i in range(n)]


def run_generation(ledger, gate, champion: Strategy, proposer: Proposer,
                   world_seeds: list[int], notes: str = "") -> tuple[Strategy, object]:
    """One turn of the wheel: propose, evaluate behind the gate, promote or refuse.

    Returns the strategy that holds canon afterwards — which is the champion unchanged
    when the challenger is refused. That is the whole point: a proposal that loses
    changes nothing.
    """
    challenger = proposer.propose(champion, notes)
    ledger.put_raw(f"proposal-{challenger.name}",
                   {"name": challenger.name, "parent": challenger.parent,
                    "diff": challenger.diff(champion), "status": "proposed, not canon"})
    receipt = gate.consider(champion, challenger, world_seeds)
    from .ledger import PROMOTED
    return (challenger if receipt.verdict == PROMOTED else champion), receipt
