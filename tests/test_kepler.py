"""The Kepler dataset and the law fits, pinned.

The transcription is checked against physics, not against the source: five points
triangulated from the verbatim table must land on an orbit with Mars's shape. If a
digit were wrong, the eccentricity or the radii would say so.
"""
import math
import sys
from datetime import date
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from metascience import kepler  # noqa: E402
from metascience.worlds import BANNED_LEXICON  # noqa: E402

POINTS = kepler.mars_points()


def test_the_triangulation_lands_on_mars():
    radii = [r for _, r in POINTS]
    assert 1.35 < min(radii) < 1.42, "perihelion distance should be near 1.38 AU"
    assert 1.63 < max(radii) < 1.72, "aphelion distance should be near 1.67 AU"


def test_the_lab_sheet_labels_match_the_geometry():
    radii = [r for _, r in POINTS]
    assert radii.index(min(radii)) == kepler.PERIHELION_PAIR
    assert radii.index(max(radii)) in kepler.APHELION_PAIRS


def test_the_day_gaps_are_what_the_data_says_not_what_the_folklore_says():
    """Three pairs are exactly one Martian year apart; two are longer baselines."""
    gaps = sorted(
        abs((date.fromisoformat(a[0]) - date.fromisoformat(b[0])).days)
        for a, b in kepler.TYCHO_PAIRS)
    assert gaps[:3] == [687, 687, 687]
    assert gaps[3:] == [1759, 2966]


def test_the_conic_recovers_mars_eccentricity():
    params = kepler.full_fits()["focus_conic"]
    assert 0.06 < params["e"] < 0.14, "Mars's true eccentricity is 0.0934"
    # perihelion direction: truth is ~336 deg; five old points get within a wedge
    assert abs((params["theta0_deg"] - 336) + 180) % 360 - 180 < 30


def test_the_sun_centred_circle_loses_and_the_conic_wins():
    loo = kepler.leave_one_out()
    assert loo["constant"]["mean_abs_err"] > 10 * loo["focus_conic"]["mean_abs_err"]
    best = min(loo, key=lambda k: loo[k]["mean_abs_err"])
    assert best == "focus_conic"


def test_keplers_own_difficulty_is_reproduced():
    """The offset circle — the hypothesis Kepler spent years on — comes close.

    If this margin were wide the historical problem would have been easy, and the
    dataset would be failing to represent it.
    """
    loo = kepler.leave_one_out()
    ratio = loo["offset_circle"]["mean_abs_err"] / loo["focus_conic"]["mean_abs_err"]
    assert 1.0 < ratio < 3.0


def test_everything_is_deterministic():
    assert kepler.mars_points() == POINTS
    assert kepler.full_fits() == kepler.full_fits()
    assert kepler.leave_one_out() == kepler.leave_one_out()


def test_nobody_intervenes_on_a_planet():
    with pytest.raises(kepler.ObservationalOnly):
        kepler.HistoricalWorld().intervene("x1", 0.5)


def test_the_blind_brief_is_actually_blind():
    text, _ = kepler.brief(blind=True)
    lowered = text.lower()
    for word in BANNED_LEXICON | {"mars", "planet", "orbit", "kepler", "tycho",
                                  "brahe", "astronom", "heliocentric", "longitude",
                                  "ellipse", "degrees", " au", "sun"}:
        assert word not in lowered, f"blind brief leaks {word!r}"


def test_the_labelled_brief_is_maximally_labelled():
    text, _ = kepler.brief(blind=False)
    for word in ("Mars", "Tycho Brahe", "Kepler", "Astronomia Nova"):
        assert word in text


def test_the_two_briefs_show_the_same_rows_in_different_clothes():
    blind_rows, blind_held = kepler._rows(blind=True)
    lab_rows, lab_held = kepler._rows(blind=False)
    assert len(blind_rows) == len(lab_rows) == 4
    assert blind_held[1] == pytest.approx(lab_held[1] * kepler.BLIND_SCALE, abs=1e-4)
