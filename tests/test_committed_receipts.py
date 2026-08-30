"""The committed receipts must replay, and the README must match them.

This project once published a transcript whose receipts no longer existed anywhere, so
a reader could re-run the loop but never check the run we described. The receipts under
docs/receipts/ close that gap, and these tests keep it closed: the numbers in the README
are the numbers in the receipt files, and every receipt's verdict can be recomputed from
its own diff and seeds without trusting anything written down.

No API key is needed. Only the proposing was live; the scoring is offline and
deterministic.
"""
import json
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from metascience.evolution import evaluate_strategy  # noqa: E402
from metascience.strategy import Strategy  # noqa: E402

RECEIPTS = ROOT / "docs" / "receipts"
RUNS = sorted(p for p in RECEIPTS.glob("run-*") if p.is_dir())
README_RUN = "run-2"  # the run the README transcribes; see docs/receipts/README.md


def _run(name: str) -> list[dict]:
    """A run's receipts, in the order the generations happened."""
    files = sorted((RECEIPTS / name).glob("*.json"))
    return sorted((json.loads(f.read_text()) for f in files), key=lambda r: r["created_at"])


_scores: dict[tuple, float] = {}


def _score(params: dict, seeds: list[int]) -> float:
    key = (tuple(sorted(params.items())), tuple(seeds))
    if key not in _scores:
        _scores[key] = evaluate_strategy(Strategy(**params), seeds)
    return _scores[key]


def test_three_runs_are_committed():
    assert [p.name for p in RUNS] == ["run-1", "run-2", "run-3"]
    for run in RUNS:
        assert len(_run(run.name)) == 3, f"{run.name} must carry all three verdicts"
        assert (run / "transcript.txt").exists()


@pytest.mark.parametrize("run", [p.name for p in RUNS])
def test_every_receipt_replays(run):
    """Recompute each verdict from the receipt's own diff, seeds and margin.

    The champion is rebuilt by walking the run forward: a promotion moves canon, a
    refusal leaves it. If any recorded score were transcribed rather than measured,
    or a verdict did not follow from the margin, this fails.
    """
    canon: dict = {}
    for r in _run(run):
        seeds = r["world_seeds"]
        challenger = {**canon, **{k: new for k, (new, _old) in r["diff"].items()}}

        assert _score(canon, seeds) == pytest.approx(r["champion_score"], abs=5e-5)
        assert _score(challenger, seeds) == pytest.approx(r["challenger_score"], abs=5e-5)

        earned = r["challenger_score"] >= r["champion_score"] + r["margin_required"]
        assert earned == (r["verdict"] == "PROMOTED"), (
            f"{run}/{r['candidate']}: verdict does not follow from the margin")

        if r["verdict"] == "PROMOTED":
            canon = challenger


def test_the_readme_transcript_matches_the_committed_receipts():
    """Every digest and score in the README's transcript comes from a receipt file."""
    readme = (ROOT / "README.md").read_text()
    block = readme.split("held-out worlds: 24")[1].split("```")[0]

    for r in _run(README_RUN):
        assert r["digest"] in block, f"receipt {r['digest']} is not in the README"
        assert r["candidate"] in block
        assert f"{r['champion_score']:+.4f}" in block
        assert f"{r['challenger_score']:+.4f}" in block

    for digest in re.findall(r"receipt ([0-9a-f]{16})", block):
        assert digest in {r["digest"] for r in _run(README_RUN)}, (
            f"README quotes receipt {digest}, which is not committed")


def test_the_headline_claims_about_the_three_runs_hold():
    """The README says: one promotion and two refusals every time, four real gains refused."""
    refused_gains = 0
    for run in RUNS:
        receipts = _run(run.name)
        verdicts = [r["verdict"] for r in receipts]
        assert verdicts.count("PROMOTED") == 1, f"{run.name}: expected one promotion"
        assert verdicts.count("REFUSED") == 2, f"{run.name}: expected two refusals"
        assert "max_experiments" in receipts[-1]["diff"], (
            f"{run.name}: the proposer should have changed the subject by generation three")
        refused_gains += sum(
            1 for r in receipts
            if r["verdict"] == "REFUSED" and r["challenger_score"] > r["champion_score"])

    assert refused_gains == 4, "four of the six refusals were of candidates that scored higher"


def test_the_auditor_disagreed_with_itself_and_we_kept_both():
    """Runs 1 and 3 hold the same promotion with opposite audit verdicts.

    Named rather than polished: the auditor is advisory and not deterministic. The gate
    is unaffected — the margin decides — but the disagreement stays on the record.
    """
    first = [r for r in _run("run-1") if r["verdict"] == "PROMOTED"][0]
    third = [r for r in _run("run-3") if r["verdict"] == "PROMOTED"][0]

    assert first["diff"] == third["diff"]
    assert first["challenger_score"] == pytest.approx(third["challenger_score"], abs=5e-5)
    assert first["audit"]["legitimate"] is False
    assert third["audit"]["legitimate"] is True
