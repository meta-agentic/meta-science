"""Worded descriptions of a world — two views, one boundary.

`agent_brief` says what `describe()` says, in sentences: labels and affordances,
nothing else. It exists so an LLM agent (or a page) can be handed a natural-language
task statement without receiving one bit more than the JSON surface carries.

`observer_narrative` states the hidden ground truth in words — topology, mechanism
families, coefficients, confounders. It is the prose twin of `ground_truth()` and
inherits its rule: **analysis and human display only, never on the agent's path.**
A test asserts the agent-side modules do not import it.

The reason two functions exist instead of one with a flag: a flag can be passed
wrongly at a call site, and the cost of that mistake here is the whole benchmark —
prose that names a mechanism family tells the model what law to retrieve.
"""
from __future__ import annotations

from .worlds import World

# Mechanism families rendered for the observer. Deliberately human words — this text
# never reaches the agent, so it does not need to be oblique.
_FORM_PROSE = {
    "linear": "a weighted sum of",
    "multiplicative": "a product of powers of",
    "exponential": "an exponential response to",
    "saturating": "a saturating response to",
    "modulus": "the modulus (Euclidean magnitude) of",
    "real": "a scaled tap of the real component of",
    "imag": "a scaled tap of the imaginary component of",
}


def agent_brief(world: World) -> str:
    """The task statement the agent may see. Adds zero information to describe()."""
    d = world.describe()
    names = ", ".join(d["variables"])
    return (
        f"You face an unknown system called {d['world_id']}. It exposes "
        f"{len(d['variables'])} measurable quantities, labelled {names}. The labels "
        "carry no meaning. You may do exactly two things: observe(n) draws passive "
        "samples of all quantities; intervene(var, value, n) fixes one quantity to a "
        "value and draws samples of the rest. Nothing else about the system is "
        "documented. Your task is to determine which quantities causally affect which, "
        "and by how much."
    )


def observer_narrative(world: World) -> str:
    """Ground truth in words. OBSERVER VIEW — never show this to the agent."""
    gt = world.ground_truth()
    hidden = set(gt["hidden"])
    lines = [
        f"World {world.world_id} was drawn from template {gt['template_id']} "
        f"(seed {world.seed}).",
    ]
    for z, (re_, im_) in world.complex_vars.items():
        im_node = world.nodes[im_]
        const_note = (f" — a constant ({im_node.exo_mean:g})"
                      if im_node.mechanism is None and im_node.exo_sd == 0 else "")
        lines.append(
            f"{z} is a complex quantity {re_} + j·{im_}: its real component is {re_} "
            f"and its imaginary component is {im_}{const_note}. Both components are "
            "independently tappable downstream.")
    for name in world._topo_order():
        node = world.nodes[name]
        tag = " (hidden — the agent cannot see or set it)" if name in hidden else ""
        if node.mechanism is None:
            if node.exo_sd == 0:
                lines.append(f"{name}{tag} is a constant: {node.exo_mean:g}.")
            else:
                lines.append(
                    f"{name}{tag} is exogenous noise: gaussian with mean "
                    f"{node.exo_mean} and sd {node.exo_sd}.")
        else:
            m = node.mechanism
            parents = ", ".join(
                f"{p} (weight {m.coeffs[p]:+g})" for p in sorted(m.coeffs))
            lines.append(
                f"{name}{tag} is {_FORM_PROSE[m.form]} its parents — {parents} — "
                f"with constant {m.const:g} and observation noise sd {m.noise:g}.")
    # A hidden CONSTANT (sd 0) is not a confounder — it does not vary, so it cannot
    # induce correlation. Only varying hidden nodes earn the warning below.
    varying_hidden = {h for h in hidden if world.nodes[h].exo_sd > 0}
    if varying_hidden:
        hidden = varying_hidden
        children = sorted(
            n for n, node in world.nodes.items()
            if node.mechanism and any(p in hidden for p in node.parents))
        if len(children) >= 2:
            a, b = children[0], children[1]
            linked = (a in world.nodes[b].parents) or (b in world.nodes[a].parents)
            if linked:
                lines.append(
                    f"The hidden quantity drives both {a} and {b}, on top of a real "
                    f"causal edge between them — so their passive correlation is "
                    "dominated by the confounder and can even carry the opposite sign "
                    "to the true effect. Observation alone concludes backwards here.")
            else:
                lines.append(
                    f"Because the hidden quantity drives {a} and {b}, they correlate "
                    "in passive data without either causing the other — an agent that "
                    "only observes will be misled here.")
    return "\n".join(lines)
