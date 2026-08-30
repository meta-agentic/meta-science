"""The prose views obey the same boundary as the JSON ones.

agent_brief is agent-facing: it must leak nothing beyond describe(). observer_narrative
is ground truth in words: it must never be importable from the agent's path. Prose is
the easiest place to leak structure — "responds exponentially" names the law's family —
so the boundary is asserted, not trusted.
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from metascience.narrate import agent_brief, observer_narrative  # noqa: E402
from metascience.templates import TEMPLATE_IDS, generate  # noqa: E402
from metascience.worlds import BANNED_LEXICON  # noqa: E402

# Structure words that would tell the model which law family to retrieve. The domain
# lexicon guards against "temperature"; this guards against "exponential".
STRUCTURE_LEXICON = {
    "linear", "multiplicative", "exponential", "saturating", "sum", "product",
    "power", "weight", "coefficient", "constant", "hidden", "confound", "parent",
    "edge", "cause", "causes", "drives", "chain", "gaussian", "exogenous",
}


def test_the_agent_brief_adds_nothing_to_the_surface():
    for tid in TEMPLATE_IDS:
        for seed in range(6):
            world = generate(seed, tid)
            words = set(re.findall(r"[a-z]+", agent_brief(world).lower()))
            assert not words & BANNED_LEXICON, f"{tid}/{seed} leaked domain terms"
            # "causally"/"affect" state the TASK; naming actual structure is the leak.
            leaked = words & (STRUCTURE_LEXICON - {"cause", "causes"})
            assert not leaked, f"{tid}/{seed} leaked structure terms: {leaked}"


def test_the_agent_brief_is_identical_for_structurally_different_worlds():
    """Same label count => same brief. If the brief varied with hidden structure, its
    variation would itself be a signal."""
    briefs = {agent_brief(generate(s, t))
              for s, t in ((1, "T2"), (3, "T4"), (5, "T5"))}
    # Variable COUNT is part of the legitimate surface (describe() exposes it), so it
    # is normalized away here along with ids and labels; everything else must match.
    normalized = {re.sub(r"W-\d+|X\d(, X\d)*|\d+ measurable", "*", b) for b in briefs}
    assert len(normalized) == 1, "briefs must differ only in id, labels and count"


def test_the_observer_narrative_tells_the_truth():
    world = generate(7, "T6")
    text = observer_narrative(world)
    gt = world.ground_truth()
    for name, parents in gt["edges"].items():
        for parent in parents:
            assert parent in text, f"parent {parent} of {name} missing from narrative"
    assert "hidden" in text
    assert "opposite sign" in text, "T6's inversion is the point and must be stated"


def test_the_agent_path_cannot_reach_the_observer_narrative():
    """Static check: no agent-side module references the ground-truth prose."""
    for mod in ("discovery", "gemini", "reasoner", "strategy", "evolution"):
        src = (ROOT / "src" / "metascience" / f"{mod}.py").read_text()
        assert "observer_narrative" not in src, f"{mod}.py touches observer prose"
        assert "ground_truth" not in src.replace("held-out", ""), \
            f"{mod}.py touches ground truth"
