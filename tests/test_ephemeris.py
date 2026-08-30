"""The propagated worlds, pinned to their fixtures.

These tests never touch the network: the arcs were recorded once from the live
flight-dynamics service with the full request stored beside the response, and
arc() refuses a fixture whose stored request no longer matches the code's.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from metascience import ephemeris, kepler  # noqa: E402


def test_the_fixtures_exist_and_replay_deterministically():
    for name in ("planet-7", "oblate-7", "control-7"):
        assert (ephemeris.FIXTURES / f"ephemeris-{name}.json").exists()
    assert ephemeris.unmemorisable(7) == ephemeris.unmemorisable(7)


def test_the_injected_law_is_rediscovered_exactly():
    """Closure: elements in, propagation through Orekit, law back out.

    Seed 7 injects e=0.06 and argument of perigee 67 deg; the conic fitted to the
    resulting arc must return them. This validates the whole pipeline — service,
    units, plane reduction, fitting — in one assertion.
    """
    params = kepler.fit_focus_conic(ephemeris.unmemorisable(7))[0]
    assert abs(params["e"] - 0.06) < 0.002
    assert abs(params["theta0_deg"] - 67.0) < 2.0


def test_two_body_arcs_are_conics_to_machine_precision():
    for pts in (ephemeris.unmemorisable(7), ephemeris.control_orbit(7)):
        score = kepler.holdout_score(pts)
        assert score["focus_conic"]["mean_abs_err"] < 1e-4
        best = min(score, key=lambda k: score[k]["mean_abs_err"])
        assert best == "focus_conic"


def test_the_oblate_world_breaks_the_textbook():
    """Identical orbit, one change: the primary is oblate. The ellipse precesses,
    no closed r(theta) exists, and the conic stops being the right answer.

    This is the anti-recall instrument: an agent that answers 'Kepler's first law'
    from memory inherits this error floor; only an agent that looks at the residuals
    can notice the law itself has moved.
    """
    control = kepler.holdout_score(ephemeris.control_orbit(7))
    broken = kepler.holdout_score(ephemeris.law_breaking(7))

    assert broken["focus_conic"]["mean_abs_err"] > 0.01
    assert broken["focus_conic"]["mean_abs_err"] > \
        100 * max(control["focus_conic"]["mean_abs_err"], 1e-9)
    # and the conic's advantage over the other families collapses into the noise
    others = min(broken[f]["mean_abs_err"] for f in ("cosine", "offset_circle"))
    assert broken["focus_conic"]["mean_abs_err"] > 0.9 * others


def test_the_apsides_visibly_rotated():
    """The fitted perihelion direction should drift tens of degrees between the
    control arc and the oblate arc — the precession is the point, so it must be
    large enough to see, not a numerical whisper."""
    control_t0 = kepler.fit_focus_conic(ephemeris.control_orbit(7))[0]["theta0_deg"]
    broken_t0 = kepler.fit_focus_conic(ephemeris.law_breaking(7))[0]["theta0_deg"]
    drift = abs((broken_t0 - control_t0 + 180) % 360 - 180)
    assert 10.0 < drift < 120.0
