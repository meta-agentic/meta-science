"""The third-law fleet, pinned to its fixtures.

Eight planets, periods measured by wrap time, axes by geometry. The law must be in
the measurements — and one known service defect must stay visible, not patched over.
"""
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from metascience import ephemeris, laws  # noqa: E402

TABLE = ephemeris.third_law_table()


def test_the_fleet_is_recorded():
    assert len(TABLE) == len(ephemeris.THIRD_LAW_SEEDS) == 8
    for seed in ephemeris.THIRD_LAW_SEEDS:
        assert (ephemeris.FIXTURES / f"ephemeris-thirdlaw-{seed}.json").exists()
    spread = [r["a_au"] for r in TABLE]
    assert max(spread) / min(spread) > 4, "the fleet must span a wide range of axes"


def test_keplers_third_law_is_in_the_measurements():
    """T = k * a^1.5, measured — the exponent from a log-log regression across the
    fleet. Slightly above 1.5 because sampling granularity biases both wrap time
    and the min/max axis estimate; the tolerance says how much."""
    xs = [math.log(r["a_au"]) for r in TABLE]
    ys = [math.log(r["period_days"]) for r in TABLE]
    n, sx, sy = len(xs), sum(xs), sum(ys)
    slope = ((n * sum(x * y for x, y in zip(xs, ys)) - sx * sy)
             / (n * sum(x * x for x in xs) - sx * sx))
    assert 1.48 < slope < 1.53


def test_the_power_law_fit_recovers_the_exponent_through_the_disguise():
    """The anonymising rescale changes only the constant — the exponent is
    scale-invariant, which is why this experiment cannot be broken by labels."""
    rows = [(r["a_au"] * 0.73, r["period_days"] * 0.41) for r in TABLE]
    s = laws.score("c1*pow(x1, c2)", rows, stride=4)
    assert abs(s["constants"]["c2"] - 1.5) < 0.03
    assert s["holdout_mean_abs_err"] < 0.2


def test_the_service_clock_defect_is_named_not_hidden():
    """The service's heliocentric periods run ~13.06x fast (effective mu ~170x
    solar) — consistently, so the law's exponent is untouched while the constant
    is miscalibrated. Pinned so a service fix breaks this test loudly instead of
    silently changing recorded science."""
    ratios = [(r["a_au"] ** 1.5 * 365.25) / r["period_days"] for r in TABLE]
    mean = sum(ratios) / len(ratios)
    assert 12.6 < mean < 13.5, f"clock ratio drifted: {mean:.3f}"
    assert max(ratios) - min(ratios) < 0.5, "the defect must stay consistent"
