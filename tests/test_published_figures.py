"""The figures quoted in the README must be the ones the code produces.

A number transcribed by hand into a document drifts silently the moment the code moves,
and this project already published one that did. These pin the claims: if a change moves
a headline figure, the suite says so instead of a reader discovering it.

Tolerances are tight but non-zero — a benchmark mean is not a hash.
"""
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from metascience.evolution import evaluate_detailed, held_out_seeds  # noqa: E402
from metascience.strategy import Strategy  # noqa: E402

SEEDS = held_out_seeds(24)
TOL = 0.005


@pytest.fixture(scope="module")
def readme() -> str:
    return (ROOT / "README.md").read_text()


def _published(readme: str, label: str, column: int) -> float:
    """Pull a figure out of the regime table by row label and column index."""
    row = next(line for line in readme.splitlines() if line.startswith(f"| {label}"))
    numbers = re.findall(r"[+-]?\d\.\d{4}", row)
    return float(numbers[column])


@pytest.mark.parametrize("label,kwargs", [
    ("champion, 400 samples", {}),
    ("frugal, 100 samples", {"samples_per_arm": 100}),
    ("very lean, 25 samples", {"samples_per_arm": 25}),
])
def test_the_published_regime_table_matches_the_code(readme, label, kwargs):
    for paired, (acc_col, score_col) in ((True, (0, 1)), (False, (2, 3))):
        got = evaluate_detailed(Strategy(paired_arms=paired, **kwargs), SEEDS)
        assert got["accuracy"] == pytest.approx(_published(readme, label, acc_col), abs=TOL)
        assert got["score"] == pytest.approx(_published(readme, label, score_col), abs=TOL)


def test_paired_arms_hide_the_cost_of_cutting_samples(readme):
    """The claim the table is making: paired accuracy does not move at all."""
    accs = {evaluate_detailed(Strategy(paired_arms=True, samples_per_arm=n), SEEDS)["accuracy"]
            for n in (400, 100, 25)}
    assert max(accs) - min(accs) < 1e-9, "paired accuracy must be flat, or the point is lost"


def test_independent_arms_expose_it(readme):
    accs = [evaluate_detailed(Strategy(samples_per_arm=n), SEEDS)["accuracy"]
            for n in (400, 100, 25)]
    assert accs[0] > accs[1] > accs[2], "accuracy must degrade as measurement is cut"
