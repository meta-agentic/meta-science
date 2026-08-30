"""Anonymisation is a correctness property. These tests are what make it one.

If the retrieval surface leaks, the agent recognises the source system, emits the
memorised law, and every number downstream measures recall instead of discovery.
"""
import json
import statistics as st
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from metascience.templates import TEMPLATE_IDS, generate  # noqa: E402
from metascience.worlds import BANNED_LEXICON  # noqa: E402


def _agent_visible_text(world) -> str:
    """Everything the agent can see, as one lowercase blob."""
    rows = world.observe(5, seed=3) + world.intervene(world.observable[0], 1.0, 5, seed=3)
    return (json.dumps(world.describe()) + json.dumps(rows)).lower()


def test_no_domain_term_reaches_the_agent():
    for tid in TEMPLATE_IDS:
        for seed in range(12):
            blob = _agent_visible_text(generate(seed, tid))
            leaked = [t for t in BANNED_LEXICON if t in blob]
            assert not leaked, f"{tid}/{seed} leaked {leaked}"


def test_variables_are_anonymous_labels_only():
    for tid in TEMPLATE_IDS:
        for v in generate(3, tid).describe()["variables"]:
            assert v.startswith("X") and v[1:].isdigit(), v


def test_constants_differ_across_seeds():
    """A fixed constant would be a fingerprint the model could learn."""
    for tid in TEMPLATE_IDS:
        consts = set()
        for seed in range(8):
            gt = generate(seed, tid).ground_truth()
            consts.add(json.dumps(gt["mechanisms"], sort_keys=True))
        assert len(consts) >= 6, f"{tid} constants too repetitive: {len(consts)}/8"


def test_role_is_not_inferable_from_label():
    """X1 must not always be the outcome, or position becomes the fingerprint."""
    sinks = set()
    for seed in range(24):
        gt = generate(seed, "T3").ground_truth()
        sinks |= {n for n, p in gt["edges"].items() if p and n in generate(seed, "T3").observable}
    assert len(sinks) > 1, "sink role is pinned to one label"


def test_determinism_from_seed():
    a = generate(11, "T1").observe(50, seed=5)
    b = generate(11, "T1").observe(50, seed=5)
    assert a == b, "same seed must replay identically"


def test_t6_observational_correlation_has_the_wrong_sign():
    """The required world: observation concludes the opposite of the truth."""
    for seed in range(10):
        w = generate(seed, "T6")
        a, b = w.observable
        obs = w.observe(3000, seed=1)
        corr = st.correlation([r[a] for r in obs], [r[b] for r in obs])
        effect = w.causal_effect(a, b)
        assert corr < 0 < effect, f"seed {seed}: corr={corr:+.3f} effect={effect:+.3f}"


def test_intervention_severs_incoming_edges():
    """In T5 neither observable causes the other; only a hidden common cause links them."""
    w = generate(4, "T5")
    a, b = w.observable
    obs = w.observe(3000, seed=2)
    corr = st.correlation([r[a] for r in obs], [r[b] for r in obs])
    assert abs(corr) > 0.5, "T5 should look strongly associated"
    assert abs(w.causal_effect(a, b)) < 0.15, "but intervening on a must not move b"
