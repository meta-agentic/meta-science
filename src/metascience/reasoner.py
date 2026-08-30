"""The reasoning boundary.

The discovery loop talks to a `Reasoner`, never to a model. That keeps the loop
testable without credentials, makes the Gemini adapter a thin swap-in, and means the
benchmark can run deterministically — which a benchmark has to, to be replayable.
"""
from __future__ import annotations

import statistics as st
from typing import Protocol

from .strategy import Strategy, candidate_pairs


class Reasoner(Protocol):
    def rank_candidates(self, variables: list[str], observations: list[dict],
                        strategy: Strategy) -> list[tuple[str, str]]:
        """Order (cause, effect) pairs worth testing. Ordering only — never a verdict."""
        ...


class HeuristicReasoner:
    """Deterministic baseline. Orders candidates by observational association.

    It is deliberately *wrong* in the same way a naive analyst is wrong: strong
    association looks like strong evidence. It ranks — it never concludes. The loop
    concludes, and only from interventions.
    """

    def rank_candidates(self, variables, observations, strategy):
        pairs = candidate_pairs(variables)
        if not strategy.screen_observationally or len(observations) < 3:
            return pairs[: strategy.max_experiments]
        scored = []
        for cause, effect in pairs:
            xs = [r[cause] for r in observations]
            ys = [r[effect] for r in observations]
            try:
                assoc = abs(st.correlation(xs, ys))
            except st.StatisticsError:
                assoc = 0.0
            scored.append((assoc, cause, effect))
        scored.sort(key=lambda t: (-t[0], t[1], t[2]))
        return [(c, e) for _, c, e in scored[: strategy.max_experiments]]
