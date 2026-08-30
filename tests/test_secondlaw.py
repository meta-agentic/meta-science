"""The second law and its breaking, pinned to the recorded arcs.

Equal areas is a claim about time, so these are the first fixtures whose sampling
had to respect the clock: chord-triangle areas are honest only well inside a
revolution, and an early probe of this experiment produced plausible-looking
nonsense by stepping 2 hours across a 93-minute orbit. The step sizes below are
part of the result.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from metascience import ephemeris  # noqa: E402


def _drift(series) -> float:
    """Relative change of the areal rate, first decile to last."""
    rates = ephemeris.areal_rates(series)
    k = max(1, len(rates) // 10)
    first = sum(rates[:k]) / k
    last = sum(rates[len(rates) - k:]) / k
    return (last - first) / first


def test_the_fixtures_exist_and_replay():
    for name in ("secondlaw-planet-5", "secondlaw-drag-7", "secondlaw-nodrag-7"):
        assert (ephemeris.FIXTURES / f"ephemeris-{name}.json").exists()
    assert ephemeris.drag_series() == ephemeris.drag_series()


def test_equal_areas_holds_where_it_should():
    """Two-body worlds: the areal rate is flat to a few parts in a hundred
    thousand over the whole arc — Kepler's second law, measured."""
    assert abs(_drift(ephemeris.equal_areas_series())) < 5e-4
    assert abs(_drift(ephemeris.no_drag_series())) < 5e-4


def test_drag_breaks_it_and_only_drag_is_different():
    """The drag arc and its control share every request field except the force
    model, and the drag world's areal rate decays two orders of magnitude
    faster. A dissipative, non-central force is what the second law cannot
    survive — our oblate world, being axially symmetric, never touched it."""
    drag = _drift(ephemeris.drag_series())
    control = _drift(ephemeris.no_drag_series())
    assert drag < -0.008, f"drag decay too small to demonstrate anything: {drag}"
    assert abs(drag) > 100 * abs(control)

    import json
    a = json.loads((ephemeris.FIXTURES / "ephemeris-secondlaw-drag-7.json"
                    ).read_text())["request"]
    b = json.loads((ephemeris.FIXTURES / "ephemeris-secondlaw-nodrag-7.json"
                    ).read_text())["request"]
    assert {k: v for k, v in a.items() if k != "forceModel"} == \
           {k: v for k, v in b.items() if k != "forceModel"}


def test_swept_area_is_monotone_and_consistent_with_the_rates():
    series = ephemeris.equal_areas_series()
    area = ephemeris.swept_area(series)
    assert all(b[1] >= a[1] for a, b in zip(area, area[1:]))
    total_from_rates = sum(
        r * (t2 - t1) for r, (t1, _, _), (t2, _, _)
        in zip(ephemeris.areal_rates(series), series, series[1:]))
    assert abs(area[-1][1] - total_from_rates) < 1e-9 * area[-1][1]


def test_the_sampling_respects_the_clock():
    """The aliasing guard: every step must be a small fraction of a revolution.
    Chord areas across a large angle are systematically wrong, and across more
    than half a turn they are meaningless."""
    for series in (ephemeris.equal_areas_series(), ephemeris.drag_series(),
                   ephemeris.no_drag_series()):
        for (_, th1, _), (_, th2, _) in zip(series, series[1:]):
            dtheta = abs(((th2 - th1 + 180.0) % 360.0) - 180.0)
            assert dtheta < 25.0, f"step sweeps {dtheta:.1f} deg — too coarse"
