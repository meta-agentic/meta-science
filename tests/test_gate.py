"""Tests for the promotion gate.

The gate is where the claim lives. Everything else could work perfectly and the project
would still be worthless if a proposal could reach canon without earning it.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from metascience.ledger import PROMOTED, REFUSED, FileLedger, PromotionGate  # noqa: E402
from metascience.strategy import Strategy  # noqa: E402


def _gate(tmp_path, scores, margin=0.02):
    """A gate whose evidence is a lookup, so the test controls the outcome exactly."""
    ledger = FileLedger(tmp_path)
    return ledger, PromotionGate(ledger, lambda s, seeds: scores[s.name], margin=margin)


def test_promotes_only_when_the_margin_is_cleared(tmp_path):
    champ = Strategy()
    chal = champ.child("challenger", samples_per_arm=100)
    ledger, gate = _gate(tmp_path, {champ.name: 0.80, "challenger": 0.85})
    assert gate.consider(champ, chal, [1, 2, 3]).verdict == PROMOTED
    assert ledger.canon()["strategy"]["name"] == "challenger"


def test_refuses_a_gain_below_the_margin(tmp_path):
    """A real but marginal improvement must lose. This is what stops drift on noise."""
    champ = Strategy()
    chal = champ.child("marginal", samples_per_arm=100)
    ledger, gate = _gate(tmp_path, {champ.name: 0.80, "marginal": 0.81})
    r = gate.consider(champ, chal, [1, 2, 3])
    assert r.verdict == REFUSED
    assert r.challenger_score > r.champion_score, "the challenger did improve"
    assert "needed" in r.reason


def test_a_refusal_leaves_canon_untouched(tmp_path):
    champ = Strategy()
    chal = champ.child("worse", effect_threshold=9.0)
    ledger, gate = _gate(tmp_path, {champ.name: 0.90, "worse": 0.10})
    assert gate.consider(champ, chal, [1]).verdict == REFUSED
    assert ledger.canon() == {}, "a refused proposal must change nothing"


def test_refusals_are_recorded_as_fully_as_promotions(tmp_path):
    """A gate that only logs its successes proves nothing."""
    champ = Strategy()
    ledger, gate = _gate(tmp_path, {champ.name: 0.90, "a": 0.10, "b": 0.99})
    gate.consider(champ, champ.child("a", samples_per_arm=50), [1])
    gate.consider(champ, champ.child("b", samples_per_arm=60), [1])
    verdicts = sorted(r["verdict"] for r in ledger.receipts())
    assert verdicts == [PROMOTED, REFUSED]
    for r in ledger.receipts():
        assert r["world_seeds"] and r["diff"] and r["digest"]


def test_the_proposer_cannot_supply_its_own_score(tmp_path):
    """A candidate claiming to be excellent is scored by the gate regardless."""
    champ = Strategy()
    liar = champ.child("liar", samples_per_arm=100)
    object.__setattr__(liar, "score", 999.0)          # ignored: the gate measures
    ledger, gate = _gate(tmp_path, {champ.name: 0.90, "liar": 0.10})
    r = gate.consider(champ, liar, [1])
    assert r.verdict == REFUSED
    assert r.challenger_score == 0.10


def test_the_receipt_replays_to_the_same_verdict(tmp_path):
    champ = Strategy()
    chal = champ.child("c", samples_per_arm=100)
    _, gate = _gate(tmp_path, {champ.name: 0.80, "c": 0.85})
    first = gate.consider(champ, chal, [1, 2, 3])
    _, gate2 = _gate(tmp_path / "again", {champ.name: 0.80, "c": 0.85})
    second = gate2.consider(champ, chal, first.world_seeds)
    assert first.verdict == second.verdict
    assert (first.champion_score, first.challenger_score) == \
           (second.champion_score, second.challenger_score)


def test_the_diff_names_exactly_what_changed(tmp_path):
    champ = Strategy()
    chal = champ.child("c", samples_per_arm=100, effect_threshold=0.3)
    _, gate = _gate(tmp_path, {champ.name: 0.9, "c": 0.1})
    assert gate.consider(champ, chal, [1]).diff == {
        "samples_per_arm": (100, 400), "effect_threshold": (0.3, 0.15)}


def test_the_metric_has_teeth_under_independent_noise():
    """An over-frugal strategy must lose, or measurement efficiency is free score.

    With paired arms the two contrast levels share noise, so effect estimates stay
    precise however few samples are drawn and cutting samples always wins. That is a
    benchmark with no trade-off in it. Under the independent default, accuracy at 25
    samples per arm falls far enough that the cost saving no longer covers it.
    """
    from metascience.evolution import evaluate_detailed, held_out_seeds

    seeds = held_out_seeds(12)
    champion = evaluate_detailed(Strategy(), seeds)
    over_frugal = evaluate_detailed(Strategy(samples_per_arm=25), seeds)

    assert over_frugal["accuracy"] < champion["accuracy"] - 0.05, \
        "cutting to 25 samples must cost real accuracy"
    assert over_frugal["score"] < champion["score"] + 0.02, \
        "and that cost must not be outrun by the cost saving"


def test_a_moderate_efficiency_gain_still_wins():
    """The promotion the demo shows must survive the harder regime too."""
    from metascience.evolution import evaluate_detailed, held_out_seeds

    seeds = held_out_seeds(12)
    assert (evaluate_detailed(Strategy(samples_per_arm=100), seeds)["score"]
            > evaluate_detailed(Strategy(), seeds)["score"] + 0.02)


def test_a_refused_candidate_is_fed_back_to_the_proposer(tmp_path):
    """Observed live: the same refused diff proposed twice in a row.

    Each proposal call is independent, so a prose note saying "it was refused" is easy
    to ignore. The verdict has to come back as structured history.
    """
    from metascience.evolution import run_generation

    class Recording:
        def __init__(self):
            self.seen, self._n = [], 0

        def propose(self, champion, notes=""):
            self._n += 1
            return champion.child(f"c{self._n}", samples_per_arm=100 * self._n)

        def remember_verdict(self, diff, gain, promoted):
            self.seen.append((diff, promoted))

    champ = Strategy()
    ledger, gate = _gate(tmp_path, {champ.name: 0.90, "c1": 0.10, "c2": 0.99})
    proposer = Recording()
    champ, _ = run_generation(ledger, gate, champ, proposer, [1, 2, 3])
    run_generation(ledger, gate, champ, proposer, [1, 2, 3])

    assert len(proposer.seen) == 2, "every verdict must reach the proposer"
    assert proposer.seen[0][1] is False and proposer.seen[1][1] is True
    assert proposer.seen[0][0], "the refused diff must be included, not just the outcome"
