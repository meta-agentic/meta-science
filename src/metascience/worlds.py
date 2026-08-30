"""Hidden causal worlds with anonymised surfaces.

A world is a structural causal model the agent cannot see. It exposes exactly two
affordances — passive `observe` and active `intervene` — and hides everything else.

The surfaces are anonymised on purpose. Templates are seeded from real scientific
structures because real science supplies non-trivial topology, genuine confounding
and known ground truth for free; but every retrievable label, constant and exponent
is stripped or randomised. Without that, a model recognises the system, emits the
memorised law, and designs experiments that confirm what it already said — measuring
recall rather than discovery, and voiding every number computed downstream.

Anonymisation is therefore a correctness property with tests, not a nicety.
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass, field

# Vocabulary that must never reach the agent. Any leak here lets the model identify
# the source system and retrieve its law instead of discovering it.
BANNED_LEXICON = frozenset({
    "pressure", "volume", "temperature", "mole", "gas", "ideal", "boyle", "charles",
    "arrhenius", "activation", "energy", "rate", "catalyst", "concentration", "reaction",
    "ohm", "voltage", "current", "resistance", "circuit", "amp", "volt",
    "infect", "susceptible", "recover", "epidemic", "sir", "transmission",
    "gene", "genotype", "phenotype", "allele", "mendel", "dominant", "recessive",
    "treatment", "placebo", "recovery", "severity", "patient", "dose",
})


@dataclass(frozen=True)
class Mechanism:
    """How one variable is produced from its parents.

    `form` names the functional family, not the textbook law — two worlds drawn from
    the same template may use different families, so the family is not a fingerprint.
    """
    form: str
    coeffs: dict[str, float]
    const: float
    noise: float

    def __call__(self, parents: dict[str, float], rng: random.Random) -> float:
        xs = [self.coeffs[k] * parents[k] for k in sorted(self.coeffs)]
        if self.form == "linear":
            v = self.const + sum(xs)
        elif self.form == "multiplicative":
            v = self.const
            for k in sorted(self.coeffs):
                v *= max(parents[k], 1e-6) ** self.coeffs[k]
        elif self.form == "exponential":
            v = self.const * math.exp(max(min(sum(xs), 40.0), -40.0))
        elif self.form == "saturating":
            s = sum(xs)
            v = self.const * s / (1.0 + abs(s))
        else:
            raise ValueError(f"unknown mechanism form: {self.form}")
        return v + rng.gauss(0.0, self.noise)


@dataclass(frozen=True)
class Node:
    name: str
    parents: tuple[str, ...]
    mechanism: Mechanism | None      # None => exogenous
    exo_mean: float = 0.0
    exo_sd: float = 1.0


@dataclass
class World:
    """A structural causal model with an anonymised surface.

    `template_id` and `nodes` are ground truth: they are what the agent is trying to
    recover and must never be serialised into anything the agent reads. `describe()`
    is the only agent-facing view.
    """
    world_id: str
    template_id: str
    nodes: dict[str, Node]
    observable: tuple[str, ...]
    hidden: tuple[str, ...]
    seed: int
    _draws: int = field(default=0, repr=False)

    # -- agent-facing surface -------------------------------------------------

    def describe(self) -> dict:
        """Everything the agent is allowed to know: names and arity. No structure."""
        return {
            "world_id": self.world_id,
            "variables": list(self.observable),
            "affordances": ["observe(n)", "intervene(var, value, n)"],
        }

    def observe(self, n: int = 200, seed: int | None = None) -> list[dict[str, float]]:
        """Passive samples. Confounded by construction — this is the trap."""
        return [self._sample({}, self._rng(seed, i)) for i in range(n)]

    def intervene(self, var: str, value: float, n: int = 200,
                  seed: int | None = None, arm: int = 0) -> list[dict[str, float]]:
        """do(var := value). Severs incoming edges — the only route to causal truth.

        With an explicit `seed`, two arms of the same contrast draw the SAME noise:
        `intervene(x, lo, seed=s)` and `intervene(x, hi, seed=s)` differ only by the
        intervention. This is common random numbers, a deliberate variance reduction —
        the paired difference isolates the causal effect instead of measuring it through
        two independent noise draws.

        It has a consequence worth stating plainly: because the noise cancels, effect
        estimates are precise at small n, so **sample size matters far less here than it
        would against independent draws**. Anything scored on measurement efficiency
        should be read with that in mind (see README, "Limits").
        """
        if var not in self.observable:
            raise KeyError(f"not an observable variable: {var}")
        # `arm` breaks the pairing on purpose: passing a distinct arm id per contrast
        # level gives each arm independent noise, which is the harder regime and the
        # one an efficiency claim should be checked against.
        return [self._sample({var: value}, self._rng(seed, i, arm)) for i in range(n)]

    # -- ground truth (never shown to the agent) ------------------------------

    def ground_truth(self) -> dict:
        return {
            "template_id": self.template_id,
            "edges": {k: list(v.parents) for k, v in self.nodes.items()},
            "hidden": list(self.hidden),
            "mechanisms": {
                k: {"form": v.mechanism.form, "coeffs": v.mechanism.coeffs,
                    "const": v.mechanism.const}
                for k, v in self.nodes.items() if v.mechanism
            },
        }

    def causal_effect(self, cause: str, effect: str,
                      lo: float = -1.0, hi: float = 1.0, n: int = 4000) -> float:
        """True average causal effect: (E[effect | do(lo→hi)]) / (hi-lo)."""
        a = _mean(self.intervene(cause, lo, n, seed=90210), effect)
        b = _mean(self.intervene(cause, hi, n, seed=90210), effect)
        return (b - a) / (hi - lo)

    # -- internals ------------------------------------------------------------

    def _rng(self, seed: int | None, i: int, arm: int = 0) -> random.Random:
        base = self.seed if seed is None else seed
        self._draws += 1
        drift = self._draws if seed is None else 0
        return random.Random((base * 1_000_003) ^ (i * 7919) ^ (arm * 104_729) ^ drift)

    def _sample(self, do: dict[str, float], rng: random.Random) -> dict[str, float]:
        vals: dict[str, float] = {}
        for name in self._topo_order():
            if name in do:
                vals[name] = do[name]
                continue
            node = self.nodes[name]
            if node.mechanism is None:
                vals[name] = rng.gauss(node.exo_mean, node.exo_sd)
            else:
                vals[name] = node.mechanism({p: vals[p] for p in node.parents}, rng)
        return {k: round(v, 6) for k, v in vals.items() if k in self.observable}

    def _topo_order(self) -> list[str]:
        """Parents before children. Raises on a cycle rather than recursing forever."""
        seen: list[str] = []
        in_progress: set[str] = set()

        def visit(n: str) -> None:
            if n in seen:
                return
            if n in in_progress:
                raise ValueError(f"causal graph contains a cycle through {n!r}")
            in_progress.add(n)
            for p in self.nodes[n].parents:
                visit(p)
            in_progress.discard(n)
            seen.append(n)

        for n in self.nodes:
            visit(n)
        return seen


def _mean(rows: list[dict[str, float]], key: str) -> float:
    return sum(r[key] for r in rows) / len(rows)
