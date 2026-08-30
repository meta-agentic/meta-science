"""Ephemeris worlds: orbits propagated by the isohub flight-dynamics service.

The historical dataset (kepler.py) has two hard limits: Mars is the most memorised
data in science, and nobody can act on it. A numerical propagator lifts both. It can
fly a planet that has never existed — real Keplerian physics, no textbook entry, so
recall is impossible — and it can fly one under a force model where the textbook law
is *wrong* (an oblate primary precesses the ellipse), so recall is punished.

The service is isohub's `space-flight-dynamics` (Orekit behind a REST contract,
`contracts/sfd/openapi.yaml`). One recipe works for heliocentric arcs: backend OREKIT
with every force-model term explicitly zeroed — the service's default force model is
tuned for Earth orbits and its integrator underflows its minimum step around the Sun.
Perturbed worlds turn individual terms back on.

Nothing here calls the network during tests. Arcs are recorded once into
tests/fixtures/ with the full request beside the response — provenance, and replay.
"""
from __future__ import annotations

import json
import math
import os
import urllib.request
from pathlib import Path

SFD_URL = os.environ.get("SFD_URL", "http://localhost:8080")
FIXTURES = Path(__file__).resolve().parents[2] / "tests" / "fixtures"

AU_M = 1.495978707e11

TWO_BODY = {"atmosphericDrag": False, "moonGravity": False, "sunGravity": False,
            "solarRadiationPressure": False, "gravityDegree": 0, "gravityOrder": 0}

# An oblate primary: degree-8 gravity field. Around Earth this precesses the line of
# apsides by degrees per day — the world where a closed conic is the wrong answer.
OBLATE = {**TWO_BODY, "gravityDegree": 8, "gravityOrder": 8}


def _quantity(value: float, unit: str) -> dict:
    return {"value": value, "unit": unit}


def fictional_planet(seed: int) -> dict:
    """Deterministic Keplerian elements for a planet that has never existed.

    Plain arithmetic on the seed, no RNG: the same seed is the same planet in every
    process, which is the same determinism bargain the generated worlds make.
    Inclination is zero by construction — the first-law loop lives in the plane.
    """
    a_au = 0.45 + (seed * 137) % 211 / 100.0          # 0.45 .. 2.55 AU
    ecc = 0.04 + (seed * 89) % 23 / 100.0             # 0.04 .. 0.26
    argp = (seed * 61) % 360
    anomaly = (seed * 29) % 360
    return {
        "centralBody": "SUN",
        "frame": "ICRF",
        "epoch": "2026-01-01T00:00:00Z",
        "semiMajorAxis": _quantity(round(a_au * AU_M / 1000.0, 1), "km"),
        "eccentricity": round(ecc, 4),
        "inclination": _quantity(0.0, "°"),
        "raan": _quantity(0.0, "°"),
        "argumentOfPerigee": _quantity(float(argp), "°"),
        "trueAnomaly": _quantity(float(anomaly), "°"),
    }


def low_orbit(seed: int) -> dict:
    """An equatorial orbit close to an oblate Earth: the law-breaking regime."""
    return {
        "centralBody": "EARTH",
        "frame": "EME2000",
        "epoch": "2026-01-01T00:00:00Z",
        "semiMajorAxis": _quantity(6900.0 + (seed * 37) % 400, "km"),
        "eccentricity": 0.05 + (seed * 13) % 5 / 100.0,
        "inclination": _quantity(0.0, "°"),
        "raan": _quantity(0.0, "°"),
        "argumentOfPerigee": _quantity(float((seed * 61) % 360), "°"),
        "trueAnomaly": _quantity(0.0, "°"),
    }


def _request(orbit: dict, duration: str, step: str, forces: dict) -> dict:
    return {
        "spacecraftId": "metascience",
        "startEpoch": orbit["epoch"],
        "duration": duration,
        "stepSize": step,
        "backend": "OREKIT",
        "orbit": orbit,
        "forceModel": forces,
    }


def _propagate_live(request: dict) -> dict:
    req = urllib.request.Request(
        f"{SFD_URL}/api/v1/trajectories/propagate",
        data=json.dumps(request).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        body = json.loads(resp.read())
    if not body.get("states"):
        raise RuntimeError(f"flight-dynamics returned no states: {body}")
    return body


def arc(name: str, orbit: dict, duration: str, step: str,
        forces: dict) -> list[tuple[str, float, float]]:
    """(epoch, theta_deg, r) samples of one propagated arc, fixture-first.

    r is in AU for heliocentric arcs and in Earth radii for Earth-centred ones —
    both dimensionless enough to keep the law machinery unit-blind.
    """
    path = FIXTURES / f"ephemeris-{name}.json"
    if path.exists():
        record = json.loads(path.read_text())
        if record["request"] != _request(orbit, duration, step, forces):
            raise RuntimeError(f"fixture {name} was recorded for a different request")
    else:
        request = _request(orbit, duration, step, forces)
        record = {"request": request, "response": _propagate_live(request)}
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(record, indent=1))

    scale = AU_M if orbit["centralBody"] == "SUN" else 6.378137e6
    out = []
    for s in record["response"]["states"]:
        x, y = s["x"]["value"], s["y"]["value"]
        r = math.hypot(x, y) / scale
        out.append((s["epoch"], math.degrees(math.atan2(y, x)) % 360.0, r))
    return out


# ------------------------------------------------------------------- the three worlds

def unmemorisable(seed: int = 7) -> list[tuple[float, float]]:
    """A planet with no textbook: pure two-body, one and a half years, in the plane."""
    pts = arc(f"planet-{seed}", fictional_planet(seed), "P548D", "P4D", TWO_BODY)
    return [(t, r) for _, t, r in pts]


def law_breaking(seed: int = 7) -> list[tuple[float, float]]:
    """The same question where the textbook answer is wrong: an oblate primary
    rotates the ellipse under the data. A closed r(theta) does not exist here."""
    pts = arc(f"oblate-{seed}", low_orbit(seed), "P10D", "PT2H", OBLATE)
    return [(t, r) for _, t, r in pts]


def control_orbit(seed: int = 7) -> list[tuple[float, float]]:
    """The identical Earth orbit under two-body forces: the paired control arm,
    so the law-breaking comparison changes exactly one thing."""
    pts = arc(f"control-{seed}", low_orbit(seed), "P10D", "PT2H", TWO_BODY)
    return [(t, r) for _, t, r in pts]


# ------------------------------------------------------------------ the third law

THIRD_LAW_SEEDS = (57, 31, 5, 56, 30, 4, 55, 29)   # a from 0.47 to 2.20 AU


def _epoch_seconds(iso: str) -> float:
    from datetime import datetime
    return datetime.fromisoformat(iso.replace("Z", "+00:00")).timestamp()


def measure_planet(seed: int) -> dict:
    """One planet's period and semi-major axis, measured — never injected.

    The arc covers ~1.3 orbits. T is the interpolated time for the unwrapped
    longitude to advance one full turn; a is (r_min + r_max)/2 over a full orbit.
    The generator knows the physics (it must, to size the arc); the numbers
    reported here come from the trajectory alone.
    """
    a_nominal = 0.45 + (seed * 137) % 211 / 100.0
    days = int(1.3 * (a_nominal ** 1.5) * 365.25)
    step_days = max(1, days // 130)
    pts = arc(f"thirdlaw-{seed}", fictional_planet(seed),
              f"P{days}D", f"P{step_days}D", TWO_BODY)

    t0 = _epoch_seconds(pts[0][0])
    times = [( _epoch_seconds(e) - t0) / 86400.0 for e, _, _ in pts]
    unwrapped, prev, offset = [], pts[0][1], 0.0
    for _, theta, _ in pts:
        if theta < prev - 180.0:
            offset += 360.0
        unwrapped.append(theta + offset)
        prev = theta
    target = unwrapped[0] + 360.0
    for i in range(1, len(unwrapped)):
        if unwrapped[i] >= target:
            frac = (target - unwrapped[i - 1]) / (unwrapped[i] - unwrapped[i - 1])
            period_days = times[i - 1] + frac * (times[i] - times[i - 1])
            radii = [r for _, _, r in pts[:i + 1]]
            return {"seed": seed,
                    "a_au": round((min(radii) + max(radii)) / 2.0, 5),
                    "period_days": round(period_days, 3),
                    "samples": len(pts)}
    raise RuntimeError(f"arc for seed {seed} never completed an orbit")


def third_law_table() -> list[dict]:
    return [measure_planet(s) for s in THIRD_LAW_SEEDS]


# ----------------------------------------------------------------- the second law
#
# Equal areas is a statement about time, so these arcs carry their timestamps and
# their sampling must respect the clock: the swept area between samples is the
# chord triangle 1/2*|r_i x r_i+1|, which is honest only while the step stays a
# small fraction of a revolution. The heliocentric arm samples ~3 deg per step;
# the drag arm samples ~19 steps per revolution of a ~93-minute orbit.
#
# Physics note that shaped the design: our oblate world does NOT break the second
# law — J2 is axially symmetric, so equatorial angular momentum is conserved and
# equal areas survives. Breaking it takes a non-central force. Drag is one, and
# it is dissipative: the areal rate does not wobble, it decays.

def drag_orbit(seed: int) -> dict:
    """Low perigee (~230 km), equatorial: deep enough for drag to bite in days."""
    return {
        "centralBody": "EARTH",
        "frame": "EME2000",
        "epoch": "2026-01-01T00:00:00Z",
        "semiMajorAxis": _quantity(6800.0, "km"),
        "eccentricity": 0.028,
        "inclination": _quantity(0.0, "°"),
        "raan": _quantity(0.0, "°"),
        "argumentOfPerigee": _quantity(float((seed * 61) % 360), "°"),
        "trueAnomaly": _quantity(0.0, "°"),
    }


# 100 m2 for five days decays the areal rate ~1.1% and the orbit survives;
# 150 m2 for six days does not — the shrinking orbit drives the integrator into
# its minimum step. The knob is calibrated to the strongest surviving signal.
DRAG = {**TWO_BODY, "atmosphericDrag": True, "dragCoefficient": 2.2,
        "dragCrossSection": {"value": 100.0, "unit": "m²"}}


def _with_days(pts) -> list[tuple[float, float, float]]:
    t0 = _epoch_seconds(pts[0][0])
    return [((_epoch_seconds(e) - t0) / 86400.0, th, r) for e, th, r in pts]


def equal_areas_series(seed: int = 5) -> list[tuple[float, float, float]]:
    """(t_days, theta_deg, r_au) for one finely-sampled orbit of a fictional
    planet — the world where the second law holds."""
    return _with_days(arc(f"secondlaw-planet-{seed}", fictional_planet(seed),
                          "P28D", "PT6H", TWO_BODY))


def drag_series(seed: int = 7) -> list[tuple[float, float, float]]:
    """(t_days, theta_deg, r_re) under drag — the world where it fails."""
    return _with_days(arc(f"secondlaw-drag-{seed}", drag_orbit(seed),
                          "P5D", "PT5M", DRAG))


def no_drag_series(seed: int = 7) -> list[tuple[float, float, float]]:
    """The identical orbit without drag: the paired control."""
    return _with_days(arc(f"secondlaw-nodrag-{seed}", drag_orbit(seed),
                          "P5D", "PT5M", TWO_BODY))


def swept_area(series) -> list[tuple[float, float]]:
    """(t_days, cumulative area) — the radius vector's sweep, chord triangles."""
    out, total = [(series[0][0], 0.0)], 0.0
    for (t1, th1, r1), (t2, th2, r2) in zip(series, series[1:]):
        dtheta = math.radians(((th2 - th1 + 180.0) % 360.0) - 180.0)
        total += abs(0.5 * r1 * r2 * math.sin(dtheta))
        out.append((t2, total))
    return out


def areal_rates(series) -> list[float]:
    """The per-interval sweep rate — the second law says these are all equal."""
    rates = []
    for (t1, th1, r1), (t2, th2, r2) in zip(series, series[1:]):
        dtheta = math.radians(((th2 - th1 + 180.0) % 360.0) - 180.0)
        rates.append(abs(0.5 * r1 * r2 * math.sin(dtheta)) / (t2 - t1))
    return rates
