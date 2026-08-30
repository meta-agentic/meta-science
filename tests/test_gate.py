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
