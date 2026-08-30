"""Compound worlds from the existing AST.

A world is already a DAG of Nodes whose Mechanisms take any number of parents, so
composition needs no new representation: relabel one world's nodes past the other's,
take the union, and add bridge edges from the first part into the second. Bridges run
in one direction only, which makes acyclicity free — each part was a DAG and no edge
returns — though the constructor's cycle guard still checks.

What compounds buy the benchmark: harder problems from audited parts. Every template's
properties (anonymisation, known ground truth, the confounding traps) survive
composition, and difficulty now scales without writing new templates — an agent that
solves T2 and T6 separately faces genuinely new work when a T2 quantity feeds the
confounded pair's system.
"""
from __future__ import annotations

import random
import re

from .templates import TEMPLATE_IDS, _stable_hash, generate
from .worlds import Mechanism, Node, World


def _relabel(world: World, offset: int) -> dict[str, str]:
    """X-labels shifted past `offset`, preserving each label's index order."""
    mapping = {}
    for name in world.nodes:
        idx = int(re.fullmatch(r"X(\d+)", name).group(1))
        mapping[name] = f"X{idx + offset}"
    return mapping


def _rename(world: World, mapping: dict[str, str]) -> dict[str, Node]:
    out = {}
    for name, node in world.nodes.items():
        mech = node.mechanism
        if mech is not None:
            mech = Mechanism(mech.form,
                             {mapping[p]: c for p, c in mech.coeffs.items()},
                             mech.const, mech.noise)
        out[mapping[name]] = Node(mapping[name],
                                  tuple(mapping[p] for p in node.parents),
                                  mech, node.exo_mean, node.exo_sd)
    return out


def compose(a: World, b: World, seed: int, n_bridges: int = 1) -> World:
    """Join two worlds with directed bridges from a's observables into b's mechanisms.

    The bridge coefficient is drawn from the same range templates use, so a bridged
    edge is not statistically recognisable as a seam.
    """
    rng = random.Random(seed * 7919 + 17)
    max_idx = max(int(re.fullmatch(r"X(\d+)", n).group(1)) for n in a.nodes)
    mapping_b = _relabel(b, max_idx)
    nodes = dict(a.nodes) | _rename(b, mapping_b)

    sources = list(a.observable)
    targets = [mapping_b[n] for n, node in b.nodes.items() if node.mechanism]
    bridges = []
    for _ in range(min(n_bridges, len(targets))):
        src = rng.choice(sources)
        tgt = rng.choice(targets)
        targets.remove(tgt)
        node = nodes[tgt]
        mech = node.mechanism
        coeffs = dict(mech.coeffs) | {src: round(rng.uniform(0.5, 1.5) *
                                                 rng.choice((-1, 1)), 4)}
        nodes[tgt] = Node(tgt, tuple(sorted(set(node.parents) | {src})),
                          Mechanism(mech.form, coeffs, mech.const, mech.noise),
                          node.exo_mean, node.exo_sd)
        bridges.append((src, tgt))

    observable = tuple(a.observable) + tuple(mapping_b[v] for v in b.observable)
    hidden = tuple(a.hidden) + tuple(mapping_b[v] for v in b.hidden)
    world = World(f"W-{seed}c", f"{a.template_id}+{b.template_id}",
                  nodes, observable, hidden, seed)
    world._topo_order()          # cycle guard runs now, not on first sample
    return world


def generate_compound(seed: int) -> World:
    """Deterministic compound: two templates and the bridge, all derived from the seed."""
    pick = _stable_hash(f"compound-{seed}")
    t1 = TEMPLATE_IDS[pick % len(TEMPLATE_IDS)]
    t2 = TEMPLATE_IDS[(pick // 7) % len(TEMPLATE_IDS)]
    a = generate(seed * 2 + 1, t1)
    b = generate(seed * 2 + 2, t2)
    return compose(a, b, seed, n_bridges=1 + pick % 2)
