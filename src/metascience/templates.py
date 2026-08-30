"""World generators seeded from real scientific structures, anonymised at birth.

Each template contributes a causal *topology* — the thing real science is good for.
Everything identifying is randomised per instance: constants, exponents, signs, the
functional family, and the assignment of X-labels to roles, so neither the name nor
the position of a variable is a fingerprint.
"""
from __future__ import annotations

import hashlib
import random

from .worlds import Mechanism, Node, World

# The seed-rotation set. FROZEN at T1-T6: adding to this tuple remaps every seed's
# template (seed % len), which would silently rebuild the held-out benchmark, the
# frozen study and every receipt. New templates join EXTRA_TEMPLATES instead and are
# reachable only by asking for them by name.
TEMPLATE_IDS = ("T1", "T2", "T3", "T4", "T5", "T6")
EXTRA_TEMPLATES = ("T7",)


def _labels(rng: random.Random, k: int) -> list[str]:
    """X-labels shuffled, so role cannot be inferred from index."""
    names = [f"X{i}" for i in range(1, k + 1)]
    rng.shuffle(names)
    return names


def _c(rng: random.Random, lo: float, hi: float) -> float:
    return round(rng.uniform(lo, hi), 4)


def _stable_hash(s: str) -> int:
    """A hash that survives leaving the process.

    Python randomises str.__hash__ per interpreter (PYTHONHASHSEED), so seeding world
    generation with the builtin made the *same seed* produce a *different world* in every
    run — which quietly broke the one property the receipts promise, replayability.
    """
    return int.from_bytes(hashlib.sha256(s.encode()).digest()[:4], "big")


def build(template_id: str, seed: int) -> World:
    if template_id not in _BUILDERS:
        raise ValueError(f"unknown template: {template_id}")
    rng = random.Random(seed * 31 + _stable_hash(template_id) % 9973)
    fn = _BUILDERS[template_id]
    return fn(rng, seed)


# -- T1: multiplicative state relation (gas-law shaped) -----------------------
def _t1(rng: random.Random, seed: int) -> World:
    a, b, c, d = _labels(rng, 4)
    nodes = {
        a: Node(a, (), None, _c(rng, 1, 4), _c(rng, .2, .6)),
        b: Node(b, (), None, _c(rng, 1, 4), _c(rng, .2, .6)),
        c: Node(c, (), None, _c(rng, 1, 3), _c(rng, .1, .4)),
        d: Node(d, (a, b, c), Mechanism(
            "multiplicative",
            {a: _c(rng, .6, 1.4), b: _c(rng, .6, 1.4), c: _c(rng, -1.4, -.6)},
            _c(rng, .5, 3.0), _c(rng, .02, .1))),
    }
    return World(f"W-{seed}", "T1", nodes, (a, b, c, d), (), seed)


# -- T2: exponential response (kinetics shaped) -------------------------------
def _t2(rng: random.Random, seed: int) -> World:
    a, b, c = _labels(rng, 3)
    nodes = {
        a: Node(a, (), None, _c(rng, .5, 2), _c(rng, .2, .5)),
        b: Node(b, (), None, _c(rng, .5, 2), _c(rng, .2, .5)),
        c: Node(c, (a, b), Mechanism(
            "exponential", {a: _c(rng, .4, 1.2), b: _c(rng, -1.2, -.4)},
            _c(rng, .5, 2.0), _c(rng, .05, .15))),
    }
    return World(f"W-{seed}", "T2", nodes, (a, b, c), (), seed)


# -- T3: linear transport chain (circuit shaped) ------------------------------
def _t3(rng: random.Random, seed: int) -> World:
    a, b, c, d = _labels(rng, 4)
    nodes = {
        a: Node(a, (), None, _c(rng, 0, 2), _c(rng, .5, 1.0)),
        b: Node(b, (), None, _c(rng, 0, 2), _c(rng, .5, 1.0)),
        c: Node(c, (a, b), Mechanism(
            "linear", {a: _c(rng, .5, 2.0), b: _c(rng, -2.0, -.5)},
            _c(rng, -1, 1), _c(rng, .1, .3))),
        d: Node(d, (c,), Mechanism(
            "linear", {c: _c(rng, .5, 1.5)}, _c(rng, -1, 1), _c(rng, .1, .3))),
    }
    return World(f"W-{seed}", "T3", nodes, (a, b, c, d), (), seed)


# -- T4: saturating compartment flow (epidemiological shaped) -----------------
def _t4(rng: random.Random, seed: int) -> World:
    a, b, c = _labels(rng, 3)
    nodes = {
        a: Node(a, (), None, _c(rng, 0, 1), _c(rng, .5, 1.2)),
        b: Node(b, (a,), Mechanism(
            "saturating", {a: _c(rng, 1.0, 3.0)}, _c(rng, 1, 4), _c(rng, .05, .2))),
        c: Node(c, (b,), Mechanism(
            "linear", {b: _c(rng, -2.0, -.5)}, _c(rng, 0, 2), _c(rng, .1, .3))),
    }
    return World(f"W-{seed}", "T4", nodes, (a, b, c), (), seed)


# -- T5: hidden common cause of two children (inheritance shaped) -------------
def _t5(rng: random.Random, seed: int) -> World:
    a, b, h = _labels(rng, 3)
    nodes = {
        h: Node(h, (), None, 0.0, _c(rng, .8, 1.5)),
        a: Node(a, (h,), Mechanism("linear", {h: _c(rng, .8, 1.8)}, 0, _c(rng, .2, .5))),
        b: Node(b, (h,), Mechanism("linear", {h: _c(rng, .8, 1.8)}, 0, _c(rng, .2, .5))),
    }
    # a and b correlate strongly and neither causes the other — a pure-confounding trap.
    return World(f"W-{seed}", "T5", nodes, (a, b), (h,), seed)


# -- T6: sign inversion under confounding — REQUIRED --------------------------
def _t6(rng: random.Random, seed: int) -> World:
    """The observational correlation carries the WRONG SIGN.

    H → A, H → B, A → B, with the true A→B effect positive and H's contribution to B
    strongly negative. Observation-only concludes A harms B; intervention shows it helps.
    This world is the entire "autonomy removes real friction" argument on one screen,
    and it cannot be faked, so its inversion is asserted by test.
    """
    a, b, h = _labels(rng, 3)
    a_to_b = _c(rng, .8, 1.5)          # true causal effect: POSITIVE
    h_to_a = _c(rng, 1.2, 2.0)
    h_to_b = _c(rng, -4.5, -3.0)       # confounder swamps it: NEGATIVE
    nodes = {
        h: Node(h, (), None, 0.0, 1.0),
        a: Node(a, (h,), Mechanism("linear", {h: h_to_a}, 0, 0.25)),
        b: Node(b, (h, a), Mechanism("linear", {h: h_to_b, a: a_to_b}, 0, 0.25)),
    }
    return World(f"W-{seed}", "T6", nodes, (a, b), (h,), seed)


# -- T7: complex quantity z = a + j·b — EXTRA, never in the seed rotation ------
def _t7(rng: random.Random, seed: int) -> World:
    """A complex variable with both outputs used downstream.

    Component a (real) is always a gaussian node. Component b (imaginary) is a
    gaussian node on even worlds and a CONSTANT on odd ones — materialised as an
    sd=0 hidden node, exercising the 'component can be a constant' case. One child
    takes the modulus of the pair; another taps a single component, so the two
    outputs of z are both load-bearing, not decorative.
    """
    a, b, m_, t_, z = _labels(rng, 5)
    const_im = rng.random() < 0.5
    nodes = {
        a: Node(a, (), None, _c(rng, -1, 2), _c(rng, .3, .9)),
        b: Node(b, (), None, _c(rng, -1, 2), 0.0 if const_im else _c(rng, .3, .9)),
        m_: Node(m_, (a, b), Mechanism(
            "modulus", {a: _c(rng, .6, 1.4), b: _c(rng, .6, 1.4)},
            _c(rng, -.5, .5), _c(rng, .05, .15))),
        t_: Node(t_, (b,) if rng.random() < 0.5 else (a,), None),
    }
    tap_parent = nodes[t_].parents[0]
    tap_form = "imag" if tap_parent == b else "real"
    nodes[t_] = Node(t_, (tap_parent,), Mechanism(
        tap_form, {tap_parent: _c(rng, .5, 1.5)}, _c(rng, -.5, .5), _c(rng, .05, .2)))
    hidden = (b,) if const_im else ()
    observable = tuple(n for n in (a, b, m_, t_) if n not in hidden)
    world = World(f"W-{seed}", "T7", nodes, observable, hidden, seed,
                  complex_vars={z: (a, b)})
    return world


_BUILDERS = {"T1": _t1, "T2": _t2, "T3": _t3, "T4": _t4, "T5": _t5, "T6": _t6,
             "T7": _t7}


def generate(seed: int, template_id: str | None = None) -> World:
    """Deterministic from seed: any run is replayable from its receipt."""
    tid = template_id or TEMPLATE_IDS[seed % len(TEMPLATE_IDS)]
    return build(tid, seed)


def world_set(seeds: range | list[int]) -> list[World]:
    return [generate(s) for s in seeds]
