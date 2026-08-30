"""The experiment-design strategy — the thing Level 2 evolves.

Kept as plain data plus a small amount of code so a proposed improvement is a
*diff a human can read*, not an opaque prompt mutation. That is what makes the
self-evolution claim auditable rather than asserted.
"""
from __future__ import annotations

import itertools
import json
from dataclasses import asdict, dataclass, replace


@dataclass(frozen=True)
class Strategy:
    """How the agent decides what to test next, and when to believe it.

    Every field is a knob a challenger may move. `name` and `parent` give each
    generation a lineage, so a promotion has a diff and an ancestor.
    """
    name: str = "champion-v1"
    parent: str | None = None
    samples_per_arm: int = 400
    contrast: tuple[float, float] = (-1.0, 1.0)
    effect_threshold: float = 0.15
    screen_observationally: bool = True   # use correlation to order candidates
    trust_observation: bool = False       # ...but never to conclude from it
    max_experiments: int = 12
    # Independent by default. With paired arms the two contrast levels share noise, so
    # effect estimates stay precise however few samples are drawn — and cutting samples
    # becomes free score. Measured: at 25 samples per arm, accuracy holds at 0.981 paired
    # and collapses to 0.847 independent. A benchmark where the cheap answer is always
    # right is not measuring anything, so the harder regime is the default.
    paired_arms: bool = False

    def digest(self) -> str:
        return json.dumps(asdict(self), sort_keys=True)

    def child(self, name: str, **changes) -> "Strategy":
        return replace(self, name=name, parent=self.name, **changes)

    def diff(self, other: "Strategy") -> dict:
        a, b = asdict(self), asdict(other)
        return {k: (a[k], b[k]) for k in a if a[k] != b[k] and k not in ("name", "parent")}


def candidate_pairs(variables: list[str]) -> list[tuple[str, str]]:
    return [(a, b) for a, b in itertools.permutations(variables, 2)]
