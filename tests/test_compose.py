"""Compound worlds must inherit every property the benchmark rests on.

Composition is only useful if what made single worlds trustworthy — anonymised
surfaces, cross-process determinism, an intervenable DAG with known ground truth —
survives it. Each of those is asserted here rather than inherited on faith.
"""
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from metascience.compose import compose, generate_compound  # noqa: E402
from metascience.discovery import run_discovery, score_on_held_out  # noqa: E402
from metascience.reasoner import HeuristicReasoner  # noqa: E402
from metascience.strategy import Strategy  # noqa: E402
from metascience.templates import generate  # noqa: E402
from metascience.worlds import BANNED_LEXICON  # noqa: E402


def test_a_bridge_actually_crosses_the_seam():
    a, b = generate(1, "T2"), generate(2, "T4")
    w = compose(a, b, seed=9)
    a_vars = set(a.observable)
    crossing = [(p, n.name) for n in w.nodes.values() for p in n.parents
                if p in a_vars and n.name not in a_vars and n.name not in a.hidden]
    assert crossing, "composition without a crossing edge is just two worlds side by side"


def test_labels_do_not_collide_and_stay_anonymous():
    w = generate_compound(3)
    assert len(set(w.nodes)) == len(w.nodes)
    for name in w.nodes:
        assert re.fullmatch(r"X\d+", name), name
    blob = json.dumps(w.describe()).lower() + json.dumps(w.observe(5, seed=1)).lower()
    assert not [t for t in BANNED_LEXICON if t in blob]


def test_compounds_are_deterministic_across_processes():
    script = (
        "import sys, json; sys.path.insert(0, %r);"
        "from metascience.compose import generate_compound;"
        "print(json.dumps(generate_compound(7).ground_truth(), sort_keys=True))"
        % str(ROOT / "src"))
    outs = {subprocess.run([sys.executable, "-c", script], capture_output=True,
                           text=True, check=True).stdout for _ in range(2)}
    assert len(outs) == 1


def test_the_discovery_loop_runs_on_a_compound_unchanged():
    """The point of composing: harder problems with zero changes to the agent."""
    w = generate_compound(5)
    run = run_discovery(w, HeuristicReasoner(), Strategy(), seed=5)
    assert run.experiments
    v = list(w.observable)
    scored = score_on_held_out(w, run, [(v[0], 0.5), (v[0], -0.5)], seed=99)
    assert scored["probes"] > 0


def test_composition_preserves_acyclicity_even_when_forced():
    """Bridges run one way; the guard still backs it up if a future edit breaks that."""
    w = generate_compound(11)
    w._topo_order()  # raises on a cycle


def test_hidden_stays_hidden_through_composition():
    # T5/T6 carry hidden confounders; compose one and check the union.
    a, b = generate(1, "T6"), generate(2, "T2")
    w = compose(a, b, seed=4)
    for h in w.hidden:
        assert h not in w.observable
        assert h not in json.dumps(w.describe())


def test_depth_zero_is_the_atomic_world_itself():
    """/world/7 at depth 0 must be the same W-7 it has always been."""
    atom, via_compound = generate(7), generate_compound(7, depth=0)
    assert atom.ground_truth() == via_compound.ground_truth()
    assert atom.world_id == via_compound.world_id


def test_a_depth_seven_chain_holds_every_invariant():
    w = generate_compound(7, depth=7)
    assert len(w.nodes) == len(set(w.nodes)), "label collision in a deep chain"
    for name in w.nodes:
        assert re.fullmatch(r"X\d+", name)
    w._topo_order()                                    # acyclic
    blob = json.dumps(w.describe()).lower()
    assert not [t for t in BANNED_LEXICON if t in blob]
    run = run_discovery(w, HeuristicReasoner(), Strategy(max_experiments=6), seed=7)
    assert run.experiments, "the loop must run on the deepest chain unchanged"


def test_depth_chains_are_deterministic_across_processes():
    script = (
        "import sys, json; sys.path.insert(0, %r);"
        "from metascience.compose import generate_compound;"
        "print(json.dumps(generate_compound(7, depth=5).ground_truth(), sort_keys=True))"
        % str(ROOT / "src"))
    outs = {subprocess.run([sys.executable, "-c", script], capture_output=True,
                           text=True, check=True).stdout for _ in range(2)}
    assert len(outs) == 1


def test_depth_out_of_range_is_refused():
    import pytest
    with pytest.raises(ValueError, match="depth"):
        generate_compound(7, depth=8)


def test_complex_domain_is_off_by_default(monkeypatch):
    """The master switch: every experiment path stays real-domain unless a process
    opts in, so history cannot silently mix domains."""
    import pytest as _pytest

    monkeypatch.delenv("METASCIENCE_COMPLEX", raising=False)
    with _pytest.raises(ValueError, match="disabled by default"):
        generate(2, "T7")
    generate(2, "T1")          # the rotation set is untouched by the switch


def test_compounds_never_contain_complex_variables():
    """Compound generation draws from the rotation set only; if that ever changes,
    the recorded history stops being comparable and this fails first."""
    for seed in range(4):
        for depth in (0, 2, 5):
            assert not generate_compound(seed, depth).complex_vars


def test_t7_complex_template_holds_the_invariants(monkeypatch):
    """T7 is EXTRA — reachable by name, never by rotation — and must pass the same
    gates as the rotation set: anonymous surface, determinism, a runnable loop."""
    monkeypatch.setenv("METASCIENCE_COMPLEX", "1")
    from metascience.templates import TEMPLATE_IDS

    assert "T7" not in TEMPLATE_IDS, \
        "adding T7 to the rotation remaps every held-out seed"
    for seed in range(6):
        w = generate(seed, "T7")
        blob = json.dumps(w.describe()).lower() + json.dumps(w.observe(4, seed=1)).lower()
        assert not [t for t in BANNED_LEXICON if t in blob]
        for word in ("complex", "modulus", "real", "imag", "j·"):
            assert word not in blob, f"complex semantics leaked to the surface: {word}"
        gt = w.ground_truth()
        assert gt["complex_vars"], "T7 must register its complex grouping"
        z, (re_, im_) = next(iter(w.complex_vars.items()))
        assert z not in w.observable and z not in w.nodes, \
            "the complex variable is a grouping, not a node"
        forms = {m["form"] for m in gt["mechanisms"].values()}
        assert "modulus" in forms and forms & {"real", "imag"}


def test_modulus_is_discoverable_by_intervention(monkeypatch):
    """The new family must be a real mechanism the loop can probe, not decoration."""
    monkeypatch.setenv("METASCIENCE_COMPLEX", "1")
    w = generate(3, "T7")
    run = run_discovery(w, HeuristicReasoner(), Strategy(), seed=3)
    assert run.experiments
    mod_node = next(n for n, m in w.ground_truth()["mechanisms"].items()
                    if m["form"] == "modulus")
    touched = [e for e in run.experiments if e.hypothesis.effect == mod_node]
    assert touched, "the modulus node must be reachable by the agent's experiments"


def test_t7_is_deterministic_across_processes():
    script = (
        "import os, sys, json; os.environ['METASCIENCE_COMPLEX'] = '1'; sys.path.insert(0, %r);"
        "from metascience.templates import generate;"
        "print(json.dumps(generate(2, 'T7').ground_truth(), sort_keys=True))"
        % str(ROOT / "src"))
    outs = {subprocess.run([sys.executable, "-c", script], capture_output=True,
                           text=True, check=True).stdout for _ in range(2)}
    assert len(outs) == 1


def test_the_complex_toggle_carries_through_a_chain(monkeypatch):
    """complex=true at depth n starts the chain from the complex world; the grouping
    must survive every composition, not just exist at depth 0."""
    monkeypatch.setenv("METASCIENCE_COMPLEX", "1")
    for depth in (0, 1, 3):
        w = generate_compound(5, depth, include_complex=True)
        assert w.complex_vars, f"complex grouping lost at depth {depth}"
        z, (re_, im_) = next(iter(w.complex_vars.items()))
        assert re_ in w.nodes and im_ in w.nodes, "components must map to real nodes"
        forms = {m["form"] for m in w.ground_truth()["mechanisms"].values()}
        assert "modulus" in forms
    run = run_discovery(generate_compound(5, 2, include_complex=True),
                        HeuristicReasoner(), Strategy(max_experiments=6), seed=5)
    assert run.experiments


def test_the_complex_toggle_respects_the_master_switch(monkeypatch):
    import pytest as _pytest
    monkeypatch.delenv("METASCIENCE_COMPLEX", raising=False)
    with _pytest.raises(ValueError, match="disabled by default"):
        generate_compound(5, 2, include_complex=True)
