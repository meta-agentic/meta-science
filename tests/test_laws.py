"""The law language: parsing is safe, fitting is deterministic, physics comes out.

The core claim of laws.py is that a law proposed as free text can be judged with
the same held-out discipline as everything else. These tests pin the machinery on
the recorded unmemorisable-planet arc, so the whole chain — parse, fit, score —
runs offline and lands on the injected physics.
"""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from metascience import ephemeris, kepler, laws  # noqa: E402

POINTS = [(round(t / 360.0, 5), round(r * kepler.BLIND_SCALE, 5))
          for t, r in ephemeris.unmemorisable(7)]
CONIC = "c1/(1 + c2*cos(2*pi*x1 - c3))"


def test_the_grammar_rejects_everything_that_is_not_mathematics():
    for bad in ("__import__('os')", "x1.__class__", "lambda: 1", "x1;x1",
                "open('x')", "c5 + 1", "x1 ** 2", "unknown(x1)", "1 = 2"):
        with pytest.raises(laws.LawSyntaxError):
            laws.score(bad, POINTS)


def test_the_parser_reads_the_grammar_it_promises():
    tree = laws.parse("pow(c1, 2) + c2*cos(2*pi*x1 - c3) - sqrt(abs(x1))/c4")
    assert laws.variables(tree) == {"c1", "c2", "c3", "c4", "x1"}
    assert laws.complexity(tree) > 10


def test_fitting_is_deterministic():
    assert laws.score(CONIC, POINTS) == laws.score(CONIC, POINTS)


def test_the_true_shape_recovers_the_injected_physics():
    """The planet was built with e=0.06 and perihelion 67 deg. A free-text conic,
    fitted blind, must hand both back as its constants."""
    s = laws.score(CONIC, POINTS)
    assert s["holdout_mean_abs_err"] < 1e-4
    assert abs(s["constants"]["c2"] - 0.06) < 0.002
    assert abs(s["constants"]["c3"] - 1.1694) < 0.02  # 67 deg in radians


def test_wrong_shapes_lose_in_the_right_order():
    errs = [laws.score(e, POINTS)["holdout_mean_abs_err"]
            for e in (CONIC, "c1 + c2*cos(2*pi*x1 - c3)", "c1 + c2*x1", "c1")]
    assert errs == sorted(errs), "conic < cosine < linear < constant"
    assert errs[1] < errs[2] / 10, "the periodic shapes must clearly beat the line"


def test_a_domain_faulting_law_scores_as_infinitely_bad():
    s = laws.score("log(x1 - 1)", POINTS)  # log of a negative number on most rows
    assert s["holdout_mean_abs_err"] is None


def test_the_freeform_prompt_offers_no_menu():
    """Closing the leak the family menu opened: no shape is named, so recognising
    'Keplerian' must now come from the data or not at all."""
    prompt = laws.freeform_prompt([(0.1, 1.2), (0.4, 1.1)], 0.7)
    lowered = prompt.lower()
    for word in ("conic", "circle", "ellipse", "kepler", "orbit", "family",
                 "periodic", "focus"):
        assert word not in lowered, f"the prompt names {word!r}"


# ------------------------------------------------------- the time-split judge

def _drag_rows():
    series = ephemeris.drag_series()
    area = ephemeris.swept_area(series)
    a_scale = 10.0 / area[-1][1]
    # every 4th row: same physics, affordable fitting
    return [(round(t * 0.41, 5), round(a * a_scale, 5)) for t, a in area][::4]


def test_the_judge_reproduces_the_second_law_verdict():
    """The finding that created this scorer, now enforced by it: the saturating
    shape that flattered on the interleaved split does not extrapolate; the true
    shape (linear minus a small quadratic) does."""
    rows = _drag_rows()
    tanh = laws.judge("c1 * (1 - exp(-c2 * x1)) / (1 + exp(-c2 * x1))", rows)
    naive = laws.judge("c1 * x1", rows)
    true = laws.judge("c1 * x1 - c2 * x1 * x1", rows)
    assert not tanh["extrapolates"]
    assert tanh["extrapolation_penalty"] > laws.EXTRAPOLATION_TOLERANCE
    assert not naive["extrapolates"], "pure linear misses the decay's future"
    assert true["extrapolates"]
    assert true["extrapolation"]["future_mean_abs_err"] < \
        tanh["extrapolation"]["future_mean_abs_err"] / 5


def test_a_machine_precision_law_is_not_punished_for_perfection():
    """The conic interpolates the exact arc to a rounded 0.0; the ratio floor and
    the absolute escape must keep such a law judged as extrapolating."""
    verdict = laws.judge(CONIC, POINTS)
    assert verdict["interpolation"]["holdout_mean_abs_err"] < 1e-4
    assert verdict["extrapolates"]


def test_the_judge_is_deterministic():
    rows = _drag_rows()
    assert laws.judge("c1 * x1", rows) == laws.judge("c1 * x1", rows)
